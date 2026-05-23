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
