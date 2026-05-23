#!/usr/bin/env python3
"""
DocBook Islamabad — Real-Time Doctor Data Scraper
==================================================
Sources:
  1. Marham.pk        – JS-rendered, uses Playwright headless browser
  2. Oladoc.com       – JS-rendered, uses Playwright headless browser
  3. InstaCare.pk     – JS-rendered, uses Playwright headless browser
  4. Shifa International Hospital – /find-a-doctor  (static HTML)
  5. Kulsum International Hospital – /find-a-doctor (static HTML)
  6. Advanced International Hospital – /all-doctors (static HTML)

Usage:
  pip install requests beautifulsoup4 lxml playwright
  playwright install chromium
  python scraper.py

Outputs: doctors.json  (loaded by the website at runtime)
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
import hashlib
import sys
from datetime import datetime

# ── Playwright availability check ─────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠  Playwright not installed — JS-rendered sites (Marham/Oladoc/InstaCare) will be skipped")

# ── HTTP session with browser-like headers ─────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})
REQUEST_DELAY = 1.5   # seconds between requests (be polite)
OUTPUT_FILE   = "doctors.json"


# ── Helpers ─────────────────────────────────────────────────────────────────

def fetch(url, retries=2):
    """Fetch URL with retries; return BeautifulSoup or None."""
    for attempt in range(retries + 1):
        try:
            print(f"  ↳ GET {url}")
            r = SESSION.get(url, timeout=20)
            r.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            print(f"    ⚠ attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return None


def stable_id(name, clinic):
    """Generate a stable numeric-ish ID from name+clinic."""
    digest = hashlib.md5(f"{name}|{clinic}".encode()).hexdigest()
    return int(digest[:8], 16) % 900000 + 100000


def clean(text):
    return " ".join((text or "").split()).strip()


def parse_fee(text):
    """Extract integer fee from strings like 'Rs. 2,500' or '2500'."""
    if not text:
        return 0
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def parse_exp(text):
    """Extract years of experience from strings like '12 Years Experience'."""
    if not text:
        return 0
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else 0


def avatar(name, bg="0ea5e9"):
    encoded = "+".join(name.split())
    return f"https://ui-avatars.com/api/?name={encoded}&background={bg}&color=fff&size=128"


# Known specialty/role keywords — if a "name" matches these it's not a real person
SPECIALTY_WORDS = {
    "cardiologist","gynecologist","neurologist","surgeon","physician","specialist",
    "pediatrician","dentist","dermatologist","psychiatrist","urologist","nephrologist",
    "pulmonologist","gastroenterologist","rheumatologist","physiotherapy","psychologist",
    "obstetrician","radiologist","oncologist","pathologist","anesthesiologist",
    "ophthalmologist","orthopedic","neonatologist","counselor","medicine","consultant",
    "general","internal","cardiology","neurosurgery","gynaecology","gynecology",
}

def is_person_name(name):
    """Return True only if name looks like an actual person, not a job title."""
    if not name or len(name) < 5:
        return False
    # Must contain at least one word starting with uppercase (real name pattern)
    words = name.strip().split()
    # Reject if first word is a known specialty
    if words[0].lower().rstrip('s') in SPECIALTY_WORDS:
        return False
    # Reject if name contains no proper noun (all lowercase words)
    has_proper = any(w[0].isupper() for w in words if len(w) > 1)
    if not has_proper:
        return False
    # Must have at least 2 words (first + last name)
    if len(words) < 2:
        return False
    return True


# ── Playwright HTML parser ────────────────────────────────────────────────────

def pw_get_html(url, wait_selector=None, timeout=30000):
    """Use Playwright to fetch a JS-rendered page and return BeautifulSoup."""
    if not PLAYWRIGHT_AVAILABLE:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
            ctx = browser.new_context(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ))
            page = ctx.new_page()
            page.goto(url, timeout=timeout, wait_until="networkidle")
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=10000)
                except Exception:
                    pass
            html = page.content()
            browser.close()
            time.sleep(1)
            return BeautifulSoup(html, "lxml")
    except Exception as e:
        print(f"    ⚠ Playwright error for {url}: {e}")
        return None


def parse_doctor_cards(soup, source, base_url, clinic, phone, area, BG):
    """Generic card parser — works for Marham, Oladoc, InstaCare after JS renders."""
    results = []

    # Try every common card pattern
    cards = (
        soup.select("div[class*='doctor-card']") or
        soup.select("div[class*='DoctorCard']") or
        soup.select("div[class*='docCard']") or
        soup.select("div[class*='doctor-profile']") or
        soup.select("div[class*='doctorCard']") or
        soup.select("div[class*='doc-card']") or
        soup.select("article[class*='doctor']") or
        soup.select("[data-cy='doctor-card']") or
        soup.select("[data-testid*='doctor']") or
        soup.select("div[class*='physician']")
    )

    # JSON-LD fallback — many medical sites embed Schema.org data
    if not cards:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                items = data if isinstance(data, list) else data.get("@graph", [data])
                for item in items:
                    if item.get("@type") in ("Physician","MedicalBusiness","Person","Doctor"):
                        name = clean(item.get("name",""))
                        if not is_person_name(name):
                            continue
                        specialty = clean(item.get("medicalSpecialty") or
                                         item.get("jobTitle","General Physician"))
                        addr = item.get("address",{})
                        loc = clean(addr.get("addressLocality","") or area)
                        rating_obj = item.get("aggregateRating",{})
                        rating = float(rating_obj.get("ratingValue",0) or 0)
                        reviews = int(rating_obj.get("reviewCount",0) or 0)
                        results.append({
                            "id": stable_id(name, source),
                            "name": name,
                            "specialty": specialty,
                            "qualification": "",
                            "experience": 0,
                            "fee": 0,
                            "rating": round(min(rating, 5.0), 1),
                            "reviews": reviews,
                            "area": loc or area,
                            "clinic": clinic,
                            "address": f"{loc or area}, Islamabad",
                            "phone": phone,
                            "available": True,
                            "nextSlot": f"Book via {source}",
                            "timings": "",
                            "about": clean(item.get("description","")),
                            "tags": [specialty],
                            "gender": "",
                            "photo": avatar(name, BG[len(results) % len(BG)]),
                            "source": source,
                            "profileUrl": item.get("url", base_url),
                        })
            except Exception:
                pass
        return results

    for i, card in enumerate(cards):
        try:
            name_el = (
                card.select_one("h2") or card.select_one("h3") or
                card.select_one("[class*='doctor-name']") or
                card.select_one("[class*='DoctorName']") or
                card.select_one("[class*='name']") or
                card.select_one("strong")
            )
            name = clean(name_el.get_text()) if name_el else ""
            if not is_person_name(name):
                continue

            spec_el = (
                card.select_one("[class*='specialt']") or
                card.select_one("[class*='Specialt']") or
                card.select_one("[class*='category']") or
                card.select_one("[class*='designation']") or
                card.select_one("small")
            )
            specialty = clean(spec_el.get_text()) if spec_el else "General Physician"
            if not specialty or is_person_name(specialty):
                specialty = "General Physician"

            exp_el = card.select_one("[class*='exp']") or card.select_one("[class*='year']")
            experience = parse_exp(exp_el.get_text() if exp_el else "")

            fee_el = (card.select_one("[class*='fee']") or
                      card.select_one("[class*='Fee']") or
                      card.select_one("[class*='price']"))
            fee = parse_fee(fee_el.get_text() if fee_el else "")

            rating_el = (card.select_one("[class*='rating']") or
                         card.select_one("[class*='Rating']") or
                         card.select_one("[class*='star']"))
            rm = re.search(r"[\d.]+", clean(rating_el.get_text()) if rating_el else "")
            rating = min(float(rm.group()), 5.0) if rm else 0.0

            loc_el = (card.select_one("[class*='location']") or
                      card.select_one("[class*='city']") or
                      card.select_one("[class*='area']"))
            loc = clean(loc_el.get_text()) if loc_el else area

            link_el = card.select_one("a[href]")
            profile_url = base_url
            if link_el:
                href = link_el.get("href","")
                profile_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")

            results.append({
                "id": stable_id(name, specialty + source),
                "name": name,
                "specialty": specialty,
                "qualification": "",
                "experience": experience,
                "fee": fee,
                "rating": round(rating, 1),
                "reviews": 0,
                "area": loc,
                "clinic": clinic,
                "address": f"{loc}, Islamabad",
                "phone": phone,
                "available": True,
                "nextSlot": f"Book via {source}",
                "timings": "",
                "about": f"{specialty} based in {loc}, Islamabad.",
                "tags": [specialty],
                "gender": "",
                "photo": avatar(name, BG[(len(results) + i) % len(BG)]),
                "source": source,
                "profileUrl": profile_url,
            })
        except Exception as e:
            print(f"    ⚠ {source} card parse error: {e}")

    return results


# ── 1. Marham ────────────────────────────────────────────────────────────────

def scrape_marham(pages=5):
    """Marham — JS-rendered Next.js app, requires Playwright."""
    results = []
    BG = ["0ea5e9", "0f766e", "7c3aed", "db2777", "ea580c"]
    print(f"  ↳ Using {'Playwright' if PLAYWRIGHT_AVAILABLE else 'static fetch (limited)'}")

    for page in range(1, pages + 1):
        url = f"https://www.marham.pk/doctors/islamabad?page={page}"
        soup = (pw_get_html(url, wait_selector="[class*='doctor']")
                if PLAYWRIGHT_AVAILABLE else fetch(url))
        if not soup:
            break
        found = parse_doctor_cards(soup, "Marham",
                                   "https://www.marham.pk/doctors/islamabad",
                                   "See Marham Profile", "", "Islamabad", BG)
        results.extend(found)
        print(f"  ✓ Marham page {page}: +{len(found)} doctors (total: {len(results)})")
        if not found:
            break

    return results


# ── 2. Oladoc ────────────────────────────────────────────────────────────────

def scrape_oladoc(pages=5):
    """Oladoc — JS-rendered, requires Playwright."""
    results = []
    BG = ["7c3aed", "db2777", "0ea5e9", "0f766e", "b45309"]
    print(f"  ↳ Using {'Playwright' if PLAYWRIGHT_AVAILABLE else 'static fetch (limited)'}")

    for page in range(1, pages + 1):
        url = f"https://oladoc.com/pakistan/islamabad/doctors?page={page}"
        soup = (pw_get_html(url, wait_selector="[class*='doctor']")
                if PLAYWRIGHT_AVAILABLE else fetch(url))
        if not soup:
            break
        found = parse_doctor_cards(soup, "Oladoc",
                                   "https://oladoc.com/pakistan/islamabad/doctors",
                                   "See Oladoc Profile", "", "Islamabad", BG)
        results.extend(found)
        print(f"  ✓ Oladoc page {page}: +{len(found)} doctors (total: {len(results)})")
        if not found:
            break

    return results


# ── 3. InstaCare ─────────────────────────────────────────────────────────────

def scrape_instacare(pages=3):
    """InstaCare — JS-rendered, requires Playwright."""
    results = []
    BG = ["ea580c", "16a34a", "9333ea", "0284c7", "be185d"]
    print(f"  ↳ Using {'Playwright' if PLAYWRIGHT_AVAILABLE else 'static fetch (limited)'}")

    for page in range(1, pages + 1):
        url = f"https://instacare.pk/doctors/islamabad?page={page}"
        soup = (pw_get_html(url, wait_selector="[class*='doctor']")
                if PLAYWRIGHT_AVAILABLE else fetch(url))
        if not soup:
            break
        found = parse_doctor_cards(soup, "InstaCare",
                                   "https://instacare.pk/doctors/islamabad",
                                   "See InstaCare Profile", "", "Islamabad", BG)
        results.extend(found)
        print(f"  ✓ InstaCare page {page}: +{len(found)} doctors (total: {len(results)})")
        if not found:
            break

    return results


# ── 4. Shifa International Hospital ──────────────────────────────────────────

def scrape_shifa():
    """
    Shifa International Hospital Find-a-Doctor directory.
    URL: https://www.shifa.com.pk/find-a-doctor/
    """
    results = []
    url = "https://www.shifa.com.pk/find-a-doctor/"
    soup = fetch(url)
    if not soup:
        return results

    cards = (
        soup.select("div[class*='doctor']") or
        soup.select("div.team-member") or
        soup.select("div.staff-member") or
        soup.select("div[class*='physician']") or
        soup.select("article[class*='doctor']") or
        soup.select("li[class*='doctor']") or
        soup.select("div.col-md-4") or   # common Bootstrap grid for team
        soup.select("div.col-lg-3")
    )

    # JSON-LD fallback
    if not cards:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Physician", "Person", "MedicalBusiness"):
                        name = clean(item.get("name", ""))
                        if not name or len(name) < 4:
                            continue
                        specialty = clean(item.get("medicalSpecialty") or item.get("jobTitle", "Specialist"))
                        doc = {
                            "id": stable_id(name, "Shifa"),
                            "name": name,
                            "specialty": specialty,
                            "qualification": clean(item.get("description", "").split(".")[0]),
                            "experience": 0,
                            "fee": 0,
                            "rating": 0,
                            "reviews": 0,
                            "area": "H-8/4",
                            "clinic": "Shifa International Hospital",
                            "address": "Shifa International Hospital, H-8/4, Islamabad",
                            "phone": "051-8460911",
                            "available": True,
                            "nextSlot": "Call Shifa: 051-8460911",
                            "timings": "Mon–Fri: 9:00 AM – 5:00 PM",
                            "about": clean(item.get("description", "")),
                            "tags": [specialty],
                            "gender": "",
                            "photo": avatar(name, "1d4ed8"),
                            "source": "Shifa Hospital",
                            "profileUrl": item.get("url", "https://www.shifa.com.pk/find-a-doctor/"),
                        }
                        results.append(doc)
            except Exception:
                pass
        return results

    for card in cards:
        try:
            name_el = (
                card.select_one("h2") or card.select_one("h3") or card.select_one("h4") or
                card.select_one("[class*='name']") or card.select_one("strong")
            )
            name = clean(name_el.get_text()) if name_el else ""
            if not name or len(name) < 4 or not any(c.isupper() for c in name):
                continue

            spec_el = (
                card.select_one("[class*='special']") or card.select_one("[class*='dept']") or
                card.select_one("small") or card.select_one("p") or card.select_one("span.title")
            )
            specialty = clean(spec_el.get_text()) if spec_el else "Specialist"

            qual_el = card.select_one("[class*='qual']") or card.select_one("[class*='degree']")
            qualification = clean(qual_el.get_text()) if qual_el else ""

            doc = {
                "id": stable_id(name, "Shifa"),
                "name": name,
                "specialty": specialty,
                "qualification": qualification,
                "experience": 0,
                "fee": 0,
                "rating": 0,
                "reviews": 0,
                "area": "H-8/4",
                "clinic": "Shifa International Hospital",
                "address": "Shifa International Hospital, H-8/4, Islamabad",
                "phone": "051-8460911",
                "available": True,
                "nextSlot": "Call Shifa: 051-8460911",
                "timings": "Mon–Sat: 9:00 AM – 5:00 PM",
                "about": f"{specialty} at Shifa International Hospital, Islamabad.",
                "tags": [specialty],
                "gender": "",
                "photo": avatar(name, "1d4ed8"),
                "source": "Shifa Hospital",
                "profileUrl": "https://www.shifa.com.pk/find-a-doctor/",
            }
            results.append(doc)
        except Exception as e:
            print(f"    ⚠ Shifa card parse error: {e}")

    print(f"  ✓ Shifa: +{len(results)} doctors")
    return results


# ── 5. Kulsum International Hospital ─────────────────────────────────────────

def scrape_kulsum():
    """
    Kulsum International Hospital Find-a-Doctor.
    URL: https://kih.com.pk/find-a-doctor/
    Kulsum renders a table/grid: name in heading, specialty in sub-element or sibling.
    """
    results = []
    url = "https://kih.com.pk/find-a-doctor/"
    soup = fetch(url)
    if not soup:
        return results

    # Try every reasonable card pattern
    cards = (
        soup.select("div[class*='doctor']") or
        soup.select("div.team-member") or
        soup.select("div[class*='physician']") or
        soup.select("div[class*='staff']") or
        soup.select("article") or
        soup.select("div.col-md-3") or soup.select("div.col-lg-4") or
        soup.select("div.col-sm-6") or
        soup.select("li.doctor") or
        soup.select("tr")   # table fallback
    )

    if not cards:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Physician", "Person"):
                        name = clean(item.get("name", ""))
                        if not is_person_name(name):
                            continue
                        specialty = clean(item.get("medicalSpecialty") or item.get("jobTitle", "Specialist"))
                        doc = {
                            "id": stable_id(name, "Kulsum"),
                            "name": name,
                            "specialty": specialty,
                            "qualification": "",
                            "experience": 0,
                            "fee": 0,
                            "rating": 0,
                            "reviews": 0,
                            "area": "G-10/4",
                            "clinic": "Kulsum International Hospital",
                            "address": "Kulsum International Hospital, G-10/4, Islamabad",
                            "phone": "051-2109000",
                            "available": True,
                            "nextSlot": "Call KIH: 051-2109000",
                            "timings": "Mon–Sat: 9:00 AM – 5:00 PM",
                            "about": clean(item.get("description", "")),
                            "tags": [specialty],
                            "gender": "",
                            "photo": avatar(name, "15803d"),
                            "source": "Kulsum Hospital",
                            "profileUrl": "https://kih.com.pk/find-a-doctor/",
                        }
                        results.append(doc)
            except Exception:
                pass
        return results

    for card in cards:
        try:
            # Try all heading levels + name-classed elements
            name_el = (
                card.select_one("h2") or card.select_one("h3") or card.select_one("h4") or
                card.select_one("h5") or
                card.select_one("[class*='name']") or card.select_one("[class*='title']") or
                card.select_one("strong") or card.select_one("b")
            )
            name = clean(name_el.get_text()) if name_el else ""
            if not is_person_name(name):
                continue

            # Try multiple selectors for specialty — Kulsum often puts it in p or span.subtitle
            spec_el = (
                card.select_one("[class*='special']") or card.select_one("[class*='dept']") or
                card.select_one("[class*='designation']") or card.select_one("[class*='position']") or
                card.select_one("p") or card.select_one("small") or
                card.select_one("span:not([class*='name'])")
            )
            specialty_raw = clean(spec_el.get_text()) if spec_el else ""
            # Only use it if it doesn't look like another person's name
            specialty = specialty_raw if specialty_raw and not is_person_name(specialty_raw) else "Specialist"

            doc = {
                "id": stable_id(name, "Kulsum"),
                "name": name,
                "specialty": specialty,
                "qualification": "",
                "experience": 0,
                "fee": 0,
                "rating": 0,
                "reviews": 0,
                "area": "G-10/4",
                "clinic": "Kulsum International Hospital",
                "address": "Kulsum International Hospital, G-10/4, Islamabad",
                "phone": "051-2109000",
                "available": True,
                "nextSlot": "Call KIH: 051-2109000",
                "timings": "Mon–Sat: 9:00 AM – 5:00 PM",
                "about": f"{specialty} at Kulsum International Hospital, Islamabad.",
                "tags": [specialty],
                "gender": "",
                "photo": avatar(name, "15803d"),
                "source": "Kulsum Hospital",
                "profileUrl": "https://kih.com.pk/find-a-doctor/",
            }
            results.append(doc)
        except Exception as e:
            print(f"    ⚠ Kulsum card parse error: {e}")

    print(f"  ✓ Kulsum: +{len(results)} doctors")
    return results


# ── 6. Advanced International Hospital ───────────────────────────────────────

def scrape_aih():
    """
    Advanced International Hospital All Doctors.
    URL: https://aih.com.pk/advanced-internaional-hospital-all-doctors/
    """
    results = []
    url = "https://aih.com.pk/advanced-internaional-hospital-all-doctors/"
    soup = fetch(url)
    if not soup:
        return results

    cards = (
        soup.select("div[class*='doctor']") or
        soup.select("div.team-member") or
        soup.select("div[class*='staff']") or
        soup.select("article") or
        soup.select("table tr") or       # some hospital sites use tables
        soup.select("div.col-md-4") or soup.select("div.col-lg-3") or
        soup.select("li.team-member")
    )

    if not cards:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Physician", "Person"):
                        name = clean(item.get("name", ""))
                        if not name or len(name) < 4:
                            continue
                        specialty = clean(item.get("medicalSpecialty") or item.get("jobTitle", "Specialist"))
                        doc = {
                            "id": stable_id(name, "AIH"),
                            "name": name,
                            "specialty": specialty,
                            "qualification": "",
                            "experience": 0,
                            "fee": 0,
                            "rating": 0,
                            "reviews": 0,
                            "area": "F-11",
                            "clinic": "Advanced International Hospital",
                            "address": "Advanced International Hospital, F-11, Islamabad",
                            "phone": "051-2228800",
                            "available": True,
                            "nextSlot": "Call AIH: 051-2228800",
                            "timings": "Mon–Sat: 9:00 AM – 5:00 PM",
                            "about": clean(item.get("description", "")),
                            "tags": [specialty],
                            "gender": "",
                            "photo": avatar(name, "7e22ce"),
                            "source": "AIH",
                            "profileUrl": "https://aih.com.pk/advanced-internaional-hospital-all-doctors/",
                        }
                        results.append(doc)
            except Exception:
                pass
        return results

    for card in cards:
        try:
            # For table rows: AIH uses format where name is in one cell, specialty in another
            # Try multiple patterns — headings first, then table cells, then any strong/b tag
            candidates = []
            for sel in ["h2","h3","h4","h5","[class*='name']","[class*='doctor-name']",
                        "strong","b","td:first-child","td:nth-child(2)"]:
                el = card.select_one(sel)
                if el:
                    candidates.append(clean(el.get_text()))

            # Pick first candidate that looks like a real person name
            name = ""
            for c in candidates:
                if is_person_name(c):
                    name = c
                    break
            if not name:
                continue

            # Specialty: look for sibling element or second table cell
            spec_el = (
                card.select_one("[class*='special']") or card.select_one("[class*='dept']") or
                card.select_one("[class*='designation']") or
                card.select_one("small") or card.select_one("span.subtitle") or
                card.select_one("td:nth-child(2)") or card.select_one("td:nth-child(3)")
            )
            specialty = clean(spec_el.get_text()) if spec_el else "Specialist"
            # If specialty looks like a name, clear it
            if is_person_name(specialty):
                specialty = "Specialist"

            qual_el = card.select_one("[class*='qual']") or card.select_one("td:nth-child(4)")
            qualification = clean(qual_el.get_text()) if qual_el else ""

            doc = {
                "id": stable_id(name, "AIH"),
                "name": name,
                "specialty": specialty,
                "qualification": qualification,
                "experience": 0,
                "fee": 0,
                "rating": 0,
                "reviews": 0,
                "area": "F-11",
                "clinic": "Advanced International Hospital",
                "address": "Advanced International Hospital, F-11, Islamabad",
                "phone": "051-2228800",
                "available": True,
                "nextSlot": "Call AIH: 051-2228800",
                "timings": "Mon–Sat: 9:00 AM – 5:00 PM",
                "about": f"{specialty} at Advanced International Hospital, Islamabad.",
                "tags": [specialty],
                "gender": "",
                "photo": avatar(name, "7e22ce"),
                "source": "AIH",
                "profileUrl": "https://aih.com.pk/advanced-internaional-hospital-all-doctors/",
            }
            results.append(doc)
        except Exception as e:
            print(f"    ⚠ AIH card parse error: {e}")

    print(f"  ✓ AIH: +{len(results)} doctors")
    return results


# ── Deduplication ─────────────────────────────────────────────────────────────

def deduplicate(doctors):
    """Remove near-duplicates by normalised name."""
    seen = set()
    unique = []
    for d in doctors:
        key = re.sub(r"[^a-z]", "", d["name"].lower())
        if key and key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def assign_sequential_ids(doctors):
    for i, d in enumerate(doctors, start=1):
        d["id"] = i
    return doctors


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n🏥 DocBook Islamabad — Data Scraper")
    print("=" * 44)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_doctors = []

    print("📡 [1/6] Scraping Marham.pk ...")
    all_doctors += scrape_marham(pages=5)

    print(f"\n📡 [2/6] Scraping Oladoc.com ...")
    all_doctors += scrape_oladoc(pages=5)

    print(f"\n📡 [3/6] Scraping InstaCare.pk ...")
    all_doctors += scrape_instacare(pages=3)

    print(f"\n📡 [4/6] Scraping Shifa International Hospital ...")
    all_doctors += scrape_shifa()

    print(f"\n📡 [5/6] Scraping Kulsum International Hospital ...")
    all_doctors += scrape_kulsum()

    print(f"\n📡 [6/6] Scraping Advanced International Hospital ...")
    all_doctors += scrape_aih()

    print(f"\n🔄 Deduplicating {len(all_doctors)} records ...")
    all_doctors = deduplicate(all_doctors)
    all_doctors = assign_sequential_ids(all_doctors)
    print(f"   → {len(all_doctors)} unique doctors after deduplication")

    # Save output
    output = {
        "updated": datetime.utcnow().isoformat() + "Z",
        "count": len(all_doctors),
        "doctors": all_doctors,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved → {OUTPUT_FILE}")
    print(f"   Total doctors: {len(all_doctors)}")
    print(f"   Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Quick source breakdown
    from collections import Counter
    sources = Counter(d["source"] for d in all_doctors)
    for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"   {src:30s} {cnt:>4} doctors")

    return len(all_doctors)


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count > 0 else 1)
