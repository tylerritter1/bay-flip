# Bay Flip 🏠
> Surface value-add and fixer-upper opportunities in the Bay Area

## 📌 Overview

Finding actionable real estate deals in the competitive San Francisco Bay Area market is challenging. Traditional portals like Zillow and Redfin treat all listings equally and often hide value-add opportunities beneath standard marketing copy. Finding true fixer-uppers, high price-per-square-foot disparities, or long-days-on-market discounts requires tedious manual searching and analysis.

**Bay Flip** automates real estate deal sourcing by aggregating property exports, running multi-factor deal scoring algorithms, generating LLM-powered property investment briefs via Google Gemini, and presenting high-yield opportunities in an interactive dashboard.

---

## ✨ Features

- **Data Pipeline**: Ingests and standardizes raw MLS and Redfin CSV exports across major Bay Area counties.
- **Automated Deal Scoring**: Evaluates multi-dimensional signals (price/sqft vs neighborhood average, days on market, keywords like "TLC", "fixer", "estate sale", price drops) to score opportunities.
- **AI Investment Analysis**: Leverages Google Gemini API to scan listing descriptions and generate instant ROI hypotheses, repair estimates, and risk flags.
- **Interactive Dashboard**: Clean, responsive static/web UI for sorting, filtering, and deep-diving into surfaced properties.
- **Email Alerts**: Automated notifications for newly identified Tier 1 and Tier 2 opportunities.

---

## 🏗️ Architecture

```
[ Redfin / MLS CSV Exports ] ---> [ Data Pipeline & Normalizer ]
                                             |
                                             v
[ Google Gemini AI Analysis ] <-- [ Deal Scoring Engine ]
             |                               |
             v                               v
[ SQLite / JSON Storage ] -------> [ Interactive Dashboard ]
                                             |
                                             v
                                  [ Automated Email Alerts ]
```

---

## 📊 Scoring Methodology

Properties are scored on a scale from 0 to 100 based on weighted algorithmic signals:

| Signal | Weight | Description |
| :--- | :---: | :--- |
| **Price / SqFt Discount** | 30% | Listing $/sqft compared against zip code / city median |
| **Days on Market (DOM)** | 20% | High DOM increases negotiation leverage & discount potential |
| **Fixer / Value-Add Keywords** | 25% | Presence of key terms ("AS-IS", "handyman", "contractor", "investor", "tlc") |
| **Price Reduction History** | 15% | Recent or repeated price cuts signaling seller motivation |
| **Lot Size & Expansion Potential** | 10% | Excess lot coverage allowing ADU construction or expansions |

---

## 🎯 Deal Tiers

Surfaced opportunities are categorized into clear actionable tiers:

- **🥇 Tier 1: Strong Value-Add Opportunity (Score: 80-100)**  
  High discount potential, strong fixer keywords, heavily motivated sellers, or high margin potential for flip / BRRRR.
- **🥈 Tier 2: Moderate Value-Add Potential (Score: 60-79)**  
  Minor cosmetic updates needed or mild neighborhood price discrepancy. Good candidate for light updates or buy-and-hold.
- **🥉 Tier 3: Watchlist / Market Rate (Score: <60)**  
  Near market value or minor value-add potential. Kept on watch for potential future price reductions.

---

## 🚀 Quick Start Guide

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/your-username/bay-flip.git
cd bay-flip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API credentials:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key
RENTCAST_API_KEY=your_optional_rentcast_key
```

### 3. Download Redfin Data Export
1. Search your target Bay Area cities/zips on Redfin (e.g., San Jose, Oakland, Concord, Vallejo).
2. Scroll to the bottom of the search results page and click **"Download All"** (CSV format).
3. Save the exported CSV files into the `data/redfin_exports/` directory.

### 4. Run Deal Scanner & AI Engine
```bash
python scanner.py
```

### 5. Build & Open Dashboard
```bash
python build_dashboard.py
open docs/index.html
```

---

## 🌐 Data Sources

- **Redfin CSV Exports**: Primary listing data, price history, square footage, lot size, and listing descriptions.
- **RentCast API** *(Optional)*: Rent estimates, historical comps, and property valuation data.
- **Google Gemini API**: AI-assisted narrative parsing and investment thesis generation.

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Data Analysis**: Pandas, NumPy
- **Database**: SQLite
- **AI / LLM Integration**: `google-generativeai` (Gemini API)
- **Frontend / Dashboard**: HTML5, Vanilla CSS, JavaScript
- **HTTP / APIs**: Requests, python-dotenv

---

## 📄 License

This project is licensed under the **MIT License**.
