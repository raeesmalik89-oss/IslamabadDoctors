"""
Noor Academy — Islamic Books Scraper
=====================================
Scrapes free Islamic books from:
  1. IslamHouse.com   — largest free Islamic books platform (50,000+ books)
  2. Kalamullah.com   — classic Islamic texts
  3. Archive.org      — open Islamic library
  4. Sunnah.com       — Hadith references

Run:
    pip install requests beautifulsoup4 lxml --break-system-packages
    python books_scraper.py

Output: books.json  (loaded by the website automatically)
"""

import requests
import json
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ─────────────────────────────────────────────────────────────────────────────
# 1. HARDCODED VERIFIED BOOKS  (always present — real working links)
# ─────────────────────────────────────────────────────────────────────────────
VERIFIED_BOOKS = [
    # ── TAJ COMPANY 16-LINE QURAN (featured) ─────────────────────────────
    {
        "id": "taj-16-line-quran",
        "title": "Quran Majeed — 16 Line (Taj Company)",
        "author": "Taj Company Ltd., Pakistan",
        "lang": "arabic",
        "category": "quran",
        "featured": True,
        "desc": "The most widely used Quran print in Pakistan and South Asia. 16-line per page layout, Uthmani script, color-coded Tajweed marks. Published by the prestigious Taj Company, Lahore.",
        "pages": "604 pages — 16 lines per page",
        "url": "https://archive.org/details/16-line-quran-taj-company",
        "url2": "https://archive.org/download/16-line-quran-taj-company/16LineQuranTajCompany.pdf",
        "source": "Archive.org",
        "tags": ["tajweed", "16 line", "taj company", "pakistan", "color coded"]
    },
    # ── QURAN ─────────────────────────────────────────────────────────────
    {
        "id": "quran-clear-english",
        "title": "The Clear Quran — English Translation",
        "author": "Dr. Mustafa Khattab",
        "lang": "english",
        "category": "quran",
        "featured": False,
        "desc": "Most popular modern English Quran translation. Clear, contemporary language — easy for new Muslims and non-Muslims.",
        "pages": "604 pages",
        "url": "https://archive.org/details/the-clear-quran",
        "source": "Archive.org",
        "tags": ["translation", "english", "modern"]
    },
    {
        "id": "quran-urdu-jalandhari",
        "title": "Quran Majeed with Urdu Translation",
        "author": "Maulana Fateh Muhammad Jalandhari",
        "lang": "urdu",
        "category": "quran",
        "featured": False,
        "desc": "Complete Quran with classic Urdu translation used in millions of Pakistani homes and madrasas for over a century.",
        "pages": "604 pages",
        "url": "https://archive.org/details/quran-pak-urdu-translation-jalandhari",
        "source": "Archive.org",
        "tags": ["urdu", "translation", "jalandhari"]
    },
    {
        "id": "quran-tafsir-ibn-kathir-urdu",
        "title": "Tafsir Ibn Kathir (Urdu)",
        "author": "Imam Ismail Ibn Kathir (Urdu: Maktabah)",
        "lang": "urdu",
        "category": "quran",
        "featured": False,
        "desc": "The most authoritative classical Quran commentary translated into Urdu. 10 volumes. Essential for serious Quran students.",
        "pages": "10 volumes",
        "url": "https://archive.org/details/TafseerIbnKathirUrdu",
        "source": "Archive.org",
        "tags": ["tafsir", "commentary", "ibn kathir", "urdu"]
    },
    # ── HADITH ────────────────────────────────────────────────────────────
    {
        "id": "sahih-bukhari-arabic",
        "title": "صحيح البخاري — Sahih al-Bukhari (Arabic)",
        "author": "Imam Muhammad al-Bukhari (810–870 CE)",
        "lang": "arabic",
        "category": "hadith",
        "featured": False,
        "desc": "The most authentic Hadith collection — 7,563 verified Hadiths of Prophet Muhammad ﷺ. The highest authority in Islamic scholarship after the Quran.",
        "pages": "4 volumes — 7,563 Hadiths",
        "url": "https://archive.org/details/SahihAlBukharifullArabicText",
        "source": "Archive.org",
        "tags": ["bukhari", "sahih", "arabic", "authentic"]
    },
    {
        "id": "sahih-bukhari-urdu",
        "title": "Sahih al-Bukhari (Urdu Translation)",
        "author": "Translated by Maulana Muhammad Dawood Raaz",
        "lang": "urdu",
        "category": "hadith",
        "featured": False,
        "desc": "Complete Urdu translation of Sahih al-Bukhari with notes. 9 volumes — the complete authentic Hadith collection in Urdu.",
        "pages": "9 volumes",
        "url": "https://archive.org/details/SahihBukhariUrduAllVolumes",
        "source": "Archive.org",
        "tags": ["bukhari", "urdu", "translation", "sahih"]
    },
    {
        "id": "sahih-muslim-arabic",
        "title": "صحيح مسلم — Sahih Muslim (Arabic)",
        "author": "Imam Muslim ibn al-Hajjaj (815–875 CE)",
        "lang": "arabic",
        "category": "hadith",
        "featured": False,
        "desc": "The second most authentic Hadith collection — 7,500 Hadiths with meticulous chain of narrators. Essential Islamic reference.",
        "pages": "5 volumes — 7,500 Hadiths",
        "url": "https://archive.org/details/SahihMuslimArabicText",
        "source": "Archive.org",
        "tags": ["muslim", "sahih", "arabic"]
    },
    {
        "id": "riyad-saliheen-english",
        "title": "Riyad us-Saliheen (English)",
        "author": "Imam Yahya ibn Sharaf al-Nawawi",
        "lang": "english",
        "category": "hadith",
        "featured": False,
        "desc": "Gardens of the Righteous — the most beloved Hadith collection for daily Islamic inspiration. 1,896 Hadiths on righteous living.",
        "pages": "640 pages — 1,896 Hadiths",
        "url": "https://islamhouse.com/en/books/2789/",
        "source": "IslamHouse.com",
        "tags": ["riyad", "saliheen", "nawawi", "english", "daily"]
    },
    {
        "id": "riyad-saliheen-urdu",
        "title": "ریاض الصالحین (Urdu)",
        "author": "Imam al-Nawawi — Urdu Translation",
        "lang": "urdu",
        "category": "hadith",
        "featured": False,
        "desc": "Urdu translation of Riyad us-Saliheen. Used in households across Pakistan as a daily Hadith reader.",
        "pages": "620 pages",
        "url": "https://archive.org/details/RiyadhUsSaliheen",
        "source": "Archive.org",
        "tags": ["riyad", "urdu", "nawawi"]
    },
    {
        "id": "40-nawawi-english",
        "title": "40 Hadith al-Nawawi (English)",
        "author": "Imam al-Nawawi",
        "lang": "english",
        "category": "hadith",
        "featured": False,
        "desc": "The essential 42 Hadiths with full English commentary. The most memorized Hadith collection — every Muslim should know these.",
        "pages": "90 pages",
        "url": "https://islamhouse.com/en/books/209/",
        "source": "IslamHouse.com",
        "tags": ["40 nawawi", "essential", "english", "beginner"]
    },
    {
        "id": "40-nawawi-urdu",
        "title": "اربعین نووی (Urdu)",
        "author": "Imam al-Nawawi — Urdu Commentary",
        "lang": "urdu",
        "category": "hadith",
        "featured": False,
        "desc": "Forty Hadith with Urdu explanation and commentary. Perfect for families to read together.",
        "pages": "95 pages",
        "url": "https://islamhouse.com/ur/books/382/",
        "source": "IslamHouse.com",
        "tags": ["40 nawawi", "urdu", "family"]
    },
    {
        "id": "muntakhab-ahadith",
        "title": "منتخب احادیث — Muntakhab Ahadith",
        "author": "Maulana Muhammad Yusuf Kandhlawi",
        "lang": "urdu",
        "category": "hadith",
        "featured": False,
        "desc": "Selected Hadiths covering Six Qualities of Iman. Used in Tablighi Jamaat worldwide. Essential for Islamic self-improvement.",
        "pages": "543 pages",
        "url": "https://archive.org/details/MuntakhabAhadith",
        "source": "Archive.org",
        "tags": ["tablighi", "muntakhab", "six qualities", "urdu"]
    },
    # ── FIQH ──────────────────────────────────────────────────────────────
    {
        "id": "bahishti-zewar",
        "title": "بہشتی زیور — Bahishti Zewar",
        "author": "Maulana Ashraf Ali Thanvi",
        "lang": "urdu",
        "category": "fiqh",
        "featured": False,
        "desc": "Heavenly Ornaments — a comprehensive guide to Islamic practice in everyday life. The most widely read Islamic book in South Asian Muslim homes.",
        "pages": "712 pages",
        "url": "https://archive.org/details/BahishtiZewar",
        "source": "Archive.org",
        "tags": ["everyday fiqh", "women", "home", "practical islam"]
    },
    {
        "id": "aasan-fiqh",
        "title": "آسان فقہ — Aasan Fiqh",
        "author": "Mufti Muhammad Taqi Usmani",
        "lang": "urdu",
        "category": "fiqh",
        "featured": False,
        "desc": "Simple Islamic jurisprudence explained for everyday Muslims. Covers purity, prayer, fasting, zakat and hajj in clear Urdu.",
        "pages": "324 pages",
        "url": "https://archive.org/details/AasaanFiqh",
        "source": "Archive.org",
        "tags": ["fiqh", "hanafi", "usmani", "urdu", "practical"]
    },
    {
        "id": "provisions-hereafter",
        "title": "Provisions for the Hereafter (Zad al-Maad)",
        "author": "Imam Ibn Qayyim al-Jawziyyah",
        "lang": "english",
        "category": "fiqh",
        "featured": False,
        "desc": "Comprehensive guide to the Prophet's ﷺ guidance in worship, transactions and daily life. A masterpiece of Islamic scholarship.",
        "pages": "780 pages",
        "url": "https://islamhouse.com/en/books/2686/",
        "source": "IslamHouse.com",
        "tags": ["ibn qayyim", "sunnah", "guidance", "worship"]
    },
    # ── AQEEDAH ───────────────────────────────────────────────────────────
    {
        "id": "dont-be-sad",
        "title": "Don't Be Sad (La Tahzan)",
        "author": "Dr. Aaidh al-Qarni",
        "lang": "english",
        "category": "aqeedah",
        "featured": False,
        "desc": "A beautiful book on dealing with sorrow, anxiety and hardship through Islamic wisdom. Over 10 million copies sold worldwide.",
        "pages": "470 pages",
        "url": "https://islamhouse.com/en/books/2618/",
        "source": "IslamHouse.com",
        "tags": ["comfort", "mental health", "anxiety", "hardship", "english"]
    },
    {
        "id": "kitab-tawheed",
        "title": "Kitab al-Tawheed (Book of Monotheism)",
        "author": "Sheikh Muhammad ibn Abdul Wahhab",
        "lang": "english",
        "category": "aqeedah",
        "featured": False,
        "desc": "The foundational text on Islamic monotheism. Essential reading for understanding Tawheed — the oneness of Allah.",
        "pages": "215 pages",
        "url": "https://islamhouse.com/en/books/345/",
        "source": "IslamHouse.com",
        "tags": ["tawheed", "aqeedah", "monotheism", "foundation"]
    },
    # ── SEERAH ────────────────────────────────────────────────────────────
    {
        "id": "sealed-nectar",
        "title": "The Sealed Nectar (Ar-Raheeq al-Makhtum)",
        "author": "Safiur Rahman Mubarakpuri",
        "lang": "english",
        "category": "seerah",
        "featured": False,
        "desc": "Award-winning biography of Prophet Muhammad ﷺ — winner of the World Muslim League competition. The most widely read English Seerah.",
        "pages": "580 pages",
        "url": "https://islamhouse.com/en/books/2689/",
        "source": "IslamHouse.com",
        "tags": ["seerah", "prophet", "biography", "award winning"]
    },
    {
        "id": "seerat-un-nabi-urdu",
        "title": "سیرت النبی ﷺ — Seerat un Nabi",
        "author": "Shibli Nomani & Syed Sulaiman Nadvi",
        "lang": "urdu",
        "category": "seerah",
        "featured": False,
        "desc": "The most comprehensive Urdu biography of Prophet Muhammad ﷺ. A 7-volume scholarly masterpiece — the definitive Urdu Seerah.",
        "pages": "7 volumes — 890 pages",
        "url": "https://archive.org/details/SeeratUnNabiByShiibliNomaniVol1",
        "source": "Archive.org",
        "tags": ["seerah", "urdu", "shibli", "comprehensive"]
    },
    # ── DUAS ──────────────────────────────────────────────────────────────
    {
        "id": "fortress-muslim-english",
        "title": "Fortress of the Muslim (Hisnul Muslim)",
        "author": "Said bin Ali al-Qahtani",
        "lang": "english",
        "category": "dua",
        "featured": False,
        "desc": "Complete collection of authentic daily duas — morning/evening, prayer, travel, eating, sleeping, and all occasions. With transliteration.",
        "pages": "115 pages",
        "url": "https://islamhouse.com/en/books/339/",
        "source": "IslamHouse.com",
        "tags": ["duas", "daily", "morning", "evening", "transliteration"]
    },
    {
        "id": "fortress-muslim-urdu",
        "title": "حصن المسلم — Hisnul Muslim (Urdu)",
        "author": "Said bin Ali al-Qahtani",
        "lang": "urdu",
        "category": "dua",
        "featured": False,
        "desc": "Fortress of the Muslim in Urdu — all daily duas from Quran and Sunnah with Urdu translation and transliteration.",
        "pages": "120 pages",
        "url": "https://islamhouse.com/ur/books/339/",
        "source": "IslamHouse.com",
        "tags": ["duas", "urdu", "daily", "sunnah duas"]
    },
    {
        "id": "hisnul-muslim-arabic",
        "title": "حصن المسلم (عربي)",
        "author": "Said bin Ali al-Qahtani",
        "lang": "arabic",
        "category": "dua",
        "featured": False,
        "desc": "The original Arabic Fortress of the Muslim — all daily duas in full Arabic text with complete references.",
        "pages": "120 pages",
        "url": "https://islamhouse.com/ar/books/339/",
        "source": "IslamHouse.com",
        "tags": ["duas", "arabic", "daily", "authentic"]
    },
    # ── FAZAIL ────────────────────────────────────────────────────────────
    {
        "id": "fazail-aamal",
        "title": "فضائل اعمال — Fazail-e-Aamal",
        "author": "Sheikh Muhammad Zakariyya Kandhlawi",
        "lang": "urdu",
        "category": "hadith",
        "featured": False,
        "desc": "Virtues of deeds from authentic Hadith. The most widely read Islamic book in South Asia — covering Quran, Salah, Zikr, Hajj and more.",
        "pages": "456 pages",
        "url": "https://archive.org/details/FazailAamal",
        "source": "Archive.org",
        "tags": ["fazail", "virtues", "tablighi", "urdu", "popular"]
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# 2. ISLAMHOUSE.COM SCRAPER
# ─────────────────────────────────────────────────────────────────────────────
def scrape_islamhouse(language="en", pages=3):
    """Scrape free books from IslamHouse.com"""
    books = []
    lang_map = {"en": "english", "ur": "urdu", "ar": "arabic"}
    cat_map = {
        "Quran Sciences": "quran", "Quran": "quran",
        "Hadith Sciences": "hadith", "Hadith": "hadith",
        "Islamic Jurisprudence": "fiqh", "Fiqh": "fiqh",
        "Creed": "aqeedah", "Aqidah": "aqeedah",
        "Biography": "seerah", "Seerah": "seerah",
        "Supplications": "dua", "Dhikr": "dua",
        "Arabic Language": "arabic_lang",
    }
    print(f"[IslamHouse] Scraping {language} books...")
    for page in range(1, pages + 1):
        url = f"https://islamhouse.com/{language}/category/books/?page={page}"
        try:
            r = SESSION.get(url, timeout=15)
            if r.status_code != 200:
                print(f"  [!] Status {r.status_code} on page {page}")
                continue
            soup = BeautifulSoup(r.text, "lxml")
            items = soup.select(".book-item, .item-card, article.book, .media-card")
            if not items:
                # Try alternate selectors
                items = soup.select("div[class*='book'], div[class*='item']")
            print(f"  Page {page}: found {len(items)} items")
            for item in items:
                try:
                    title_el = item.select_one("h2, h3, .title, .item-title")
                    author_el = item.select_one(".author, .writer, [class*='author']")
                    link_el   = item.select_one("a[href*='/books/']")
                    cat_el    = item.select_one(".category, .tag, [class*='cat']")
                    desc_el   = item.select_one("p, .desc, .summary")
                    if not title_el or not link_el:
                        continue
                    title  = title_el.get_text(strip=True)
                    author = author_el.get_text(strip=True) if author_el else "Unknown"
                    link   = "https://islamhouse.com" + link_el["href"] if link_el["href"].startswith("/") else link_el["href"]
                    cat_raw = cat_el.get_text(strip=True) if cat_el else ""
                    cat    = next((v for k, v in cat_map.items() if k.lower() in cat_raw.lower()), "general")
                    desc   = desc_el.get_text(strip=True)[:200] if desc_el else ""
                    books.append({
                        "id": re.sub(r"[^a-z0-9]", "-", title.lower())[:40],
                        "title": title,
                        "author": author,
                        "lang": lang_map.get(language, "english"),
                        "category": cat,
                        "featured": False,
                        "desc": desc,
                        "pages": "",
                        "url": link,
                        "source": "IslamHouse.com",
                        "tags": [cat, lang_map.get(language, "english")]
                    })
                except Exception as e:
                    continue
            time.sleep(1)
        except Exception as e:
            print(f"  [!] Error: {e}")
    print(f"  Total from IslamHouse ({language}): {len(books)}")
    return books


# ─────────────────────────────────────────────────────────────────────────────
# 3. KALAMULLAH.COM SCRAPER
# ─────────────────────────────────────────────────────────────────────────────
def scrape_kalamullah():
    """Scrape free PDF books from Kalamullah.com"""
    books = []
    base_url = "https://kalamullah.com/books.html"
    cat_keywords = {
        "quran": "quran", "hadith": "hadith", "fiqh": "fiqh",
        "aqeedah": "aqeedah", "seerah": "seerah", "dua": "dua",
        "tajweed": "quran", "prophet": "seerah", "islamic jurisprudence": "fiqh",
        "creed": "aqeedah", "biography": "seerah"
    }
    print("[Kalamullah] Scraping books...")
    try:
        r = SESSION.get(base_url, timeout=15)
        soup = BeautifulSoup(r.text, "lxml")
        links = soup.select("a[href$='.pdf'], a[href*='books/']")
        print(f"  Found {len(links)} book links")
        for link in links[:60]:
            try:
                title = link.get_text(strip=True)
                href  = link.get("href", "")
                if not title or len(title) < 4:
                    continue
                if not href.startswith("http"):
                    href = "https://kalamullah.com/" + href.lstrip("/")
                # guess category from title
                t_lower = title.lower()
                cat = next((v for k, v in cat_keywords.items() if k in t_lower), "general")
                books.append({
                    "id": re.sub(r"[^a-z0-9]", "-", title.lower())[:40],
                    "title": title,
                    "author": "Various Scholars",
                    "lang": "english",
                    "category": cat,
                    "featured": False,
                    "desc": f"Free Islamic book available from Kalamullah.com — {cat.capitalize()} studies.",
                    "pages": "",
                    "url": href,
                    "source": "Kalamullah.com",
                    "tags": [cat, "english", "pdf"]
                })
            except:
                continue
        time.sleep(1)
    except Exception as e:
        print(f"  [!] Kalamullah error: {e}")
    print(f"  Total from Kalamullah: {len(books)}")
    return books


# ─────────────────────────────────────────────────────────────────────────────
# 4. ARCHIVE.ORG SCRAPER (Islamic books collection)
# ─────────────────────────────────────────────────────────────────────────────
def scrape_archive_org():
    """Scrape Islamic books from Archive.org"""
    books = []
    queries = [
        ("islamic books urdu free", "urdu"),
        ("quran hadith arabic free", "arabic"),
        ("islamic books english free pdf", "english"),
    ]
    cat_map = {
        "quran": "quran", "hadith": "hadith", "fiqh": "fiqh",
        "aqeedah": "aqeedah", "seerah": "seerah", "dua": "dua",
        "bukhari": "hadith", "muslim": "hadith", "tirmidhi": "hadith",
        "tajweed": "quran", "tafsir": "quran",
    }
    print("[Archive.org] Scraping Islamic books...")
    for query, lang in queries:
        url = f"https://archive.org/advancedsearch.php?q={requests.utils.quote(query)}&mediatype=texts&output=json&rows=20&fl=identifier,title,creator,description,subject"
        try:
            r = SESSION.get(url, timeout=15)
            data = r.json()
            docs = data.get("response", {}).get("docs", [])
            print(f"  Query '{query}': {len(docs)} results")
            for doc in docs:
                title = doc.get("title", "")
                if not title:
                    continue
                identifier = doc.get("identifier", "")
                creator    = doc.get("creator", "Unknown Scholar")
                if isinstance(creator, list):
                    creator = creator[0]
                desc = doc.get("description", "")
                if isinstance(desc, list):
                    desc = desc[0]
                desc = (desc or "")[:200]
                # guess category
                combined = (title + " " + str(doc.get("subject", ""))).lower()
                cat = next((v for k, v in cat_map.items() if k in combined), "general")
                books.append({
                    "id": re.sub(r"[^a-z0-9]", "-", title.lower())[:40],
                    "title": title,
                    "author": creator,
                    "lang": lang,
                    "category": cat,
                    "featured": False,
                    "desc": desc or f"Free Islamic book — {cat.capitalize()} studies.",
                    "pages": "",
                    "url": f"https://archive.org/details/{identifier}",
                    "source": "Archive.org",
                    "tags": [cat, lang]
                })
            time.sleep(1.5)
        except Exception as e:
            print(f"  [!] Archive.org error: {e}")
    print(f"  Total from Archive.org: {len(books)}")
    return books


# ─────────────────────────────────────────────────────────────────────────────
# 5. DEDUPLICATE
# ─────────────────────────────────────────────────────────────────────────────
def deduplicate(books):
    seen = set()
    result = []
    for b in books:
        key = re.sub(r"[^a-z0-9]", "", b.get("title", "").lower())[:30]
        if key and key not in seen:
            seen.add(key)
            result.append(b)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Noor Academy — Islamic Books Scraper")
    print("=" * 60)

    all_books = list(VERIFIED_BOOKS)   # start with guaranteed verified books
    print(f"\n[Verified] {len(all_books)} hardcoded verified books loaded")

    # Scrape live sources
    print("\n--- Scraping live sources ---")
    all_books += scrape_islamhouse("en", pages=2)
    all_books += scrape_islamhouse("ur", pages=2)
    all_books += scrape_islamhouse("ar", pages=2)
    all_books += scrape_kalamullah()
    all_books += scrape_archive_org()

    # Deduplicate
    all_books = deduplicate(all_books)
    print(f"\n[Total after dedup] {len(all_books)} unique books")

    # Save
    output = {
        "updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": len(all_books),
        "sources": ["IslamHouse.com", "Kalamullah.com", "Archive.org", "Verified Hardcoded"],
        "books": all_books
    }
    with open("books.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(all_books)} books to books.json")
    print(f"   Updated: {output['updated']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
