# 🏥 DocBook Islamabad — Real-Time Doctor Booking Platform

> Find & book verified doctors across Islamabad — live data, instant appointments, zero waiting.

**Live Site:** [raeesmalik89-oss.github.io/IslamabadDoctors](https://raeesmalik89-oss.github.io/IslamabadDoctors/)

---

## 📌 Overview

DocBook Islamabad is a full-stack healthcare discovery and appointment booking platform serving patients across Islamabad, Pakistan. The platform aggregates real-time doctor data from multiple healthcare sources, displays searchable doctor profiles, and allows patients to book appointments — all without a traditional backend server.

---

## ✨ Features

- 🔍 **Smart Search** — Filter doctors by specialty, area, gender, availability, and fee range
- 📅 **Appointment Booking** — Patients submit booking requests; clinic receives instant email notification
- 🏥 **Doctor Registration** — Clinics and doctors can list their practice via a self-service form
- 🔄 **Real-Time Data** — Doctor profiles auto-update every 6 hours via GitHub Actions
- 📊 **Live Stats** — Doctor count and last-updated timestamp shown on the homepage
- 📱 **Responsive Design** — Fully mobile-friendly across all screen sizes

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  GitHub Actions (Cron)               │
│           Runs scraper.py every 6 hours              │
└──────────────────────┬──────────────────────────────┘
                       │ commits doctors.json
                       ▼
┌─────────────────────────────────────────────────────┐
│              GitHub Repository                       │
│   index.html │ doctors.html │ app.js │ doctors.json  │
└──────────────────────┬──────────────────────────────┘
                       │ served via
                       ▼
┌─────────────────────────────────────────────────────┐
│              GitHub Pages (Static Hosting)           │
│        raeesmalik89-oss.github.io/IslamabadDoctors   │
└──────────────────────┬──────────────────────────────┘
                       │ fetches doctors.json at runtime
                       ▼
┌─────────────────────────────────────────────────────┐
│              Patient's Browser                       │
│   app.js loads live data → renders doctor cards      │
└─────────────────────────────────────────────────────┘
```

---

## 🕷️ Data Sources

The scraper (`scraper.py`) aggregates doctor data from:

| Source | Method | Status |
|--------|--------|--------|
| [Marham.pk](https://www.marham.pk) | Playwright + `__NEXT_DATA__` JSON extraction | ✅ Active |
| [Oladoc.com](https://oladoc.com) | Playwright + `__NEXT_DATA__` JSON extraction | ✅ Active |
| [InstaCare.pk](https://instacare.pk) | Playwright headless browser | ✅ Active |
| Shifa International Hospital | Playwright headless browser | ✅ Active |
| Kulsum International Hospital | HTTP requests + BeautifulSoup | ✅ Active |
| AIH (Advanced International Hospital) | Playwright headless browser | ✅ Active |
| Hardcoded Verified Doctors | 30 manually verified Islamabad doctors | ✅ Always present |

---

## ⚙️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML5, CSS3, JavaScript (ES6+) |
| Hosting | GitHub Pages |
| Data Pipeline | Python 3.11, Playwright, BeautifulSoup4, lxml |
| Automation | GitHub Actions (cron schedule — every 6 hours) |
| Form Handling | Formspree REST API |
| Version Control | Git / GitHub |

---

## 🚀 Local Setup

### Prerequisites
```bash
python3 --version   # 3.9+
```

### Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium --with-deps
```

### Run the scraper
```bash
python scraper.py
```
This generates `doctors.json` with live doctor data.

### View the site locally
Simply open `index.html` in your browser. The site will load `doctors.json` automatically.

---

## 🔄 GitHub Actions — Auto-Update

The workflow at `.github/workflows/scrape.yml` runs automatically:

- **Every 6 hours** (cron: `0 */6 * * *`)
- **On manual trigger** via GitHub Actions UI → "Run workflow"

On each run it:
1. Checks out the repository
2. Installs Python dependencies + Playwright Chromium
3. Runs `scraper.py` → generates fresh `doctors.json`
4. Commits and pushes the updated file back to the repo
5. GitHub Pages serves the new data within minutes

---

## 📁 Project Structure

```
IslamabadDoctors/
├── index.html              # Homepage
├── doctors.html            # Doctor search & listing page
├── register-doctor.html    # Doctor/clinic registration form
├── app.js                  # Main JavaScript (data loading, filters, booking)
├── data.js                 # Static fallback doctor data
├── style.css               # Global styles
├── doctors.json            # Live doctor data (auto-updated by scraper)
├── scraper.py              # Python web scraper
├── requirements.txt        # Python dependencies
└── .github/
    └── workflows/
        └── scrape.yml      # GitHub Actions automation workflow
```

---

## 💼 Business Model

| Plan | Price | Features |
|------|-------|----------|
| Free Basic | PKR 0 / month | Profile listed, searchable, booking requests |
| Featured | PKR 2,000 / month | Top of search results, featured badge, homepage placement |

Doctors and clinics register via the [List Your Practice](https://raeesmalik89-oss.github.io/IslamabadDoctors/register-doctor.html) page. Registration requests are reviewed manually before publishing.

---

## 📬 Contact

**Developer:** Muhammad Raees  
**Email:** raees.malik89@gmail.com  
**WhatsApp:** +92-316-881-8693  
**LinkedIn:** [linkedin.com/in/muhammad-raees081489](https://linkedin.com/in/muhammad-raees081489)  
**GitHub:** [github.com/raeesmalik89-oss](https://github.com/raeesmalik89-oss)

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

*Built with ❤️ for Islamabad — making quality healthcare accessible to everyone.*
