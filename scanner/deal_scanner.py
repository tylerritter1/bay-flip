"""
Bay Opps Deal Scanner
Main orchestrator for scanning, scoring, and analyzing real estate buy opportunities.
"""

import os
import sqlite3
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any

from scanner.data_sources.redfin_csv import parse_redfin_csv, detect_distress_signals
from scanner.data_sources.county_assessor import enrich_property
from scanner.scoring import score_property
from scanner.gemini_analyst import analyze_top_deals
from scanner.email_alert import send_deal_alert

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "data", "deals.db"))
SQL_PATH = os.path.join(BASE_DIR, "data", "deals.sql")

def restore_db_if_needed():
    """Restore DB from SQL dump if the .db file doesn't exist."""
    if not os.path.exists(DB_PATH) and os.path.exists(SQL_PATH):
        logger.info(f"Restoring database from {SQL_PATH}...")
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        with open(SQL_PATH, 'r') as f:
            conn.executescript(f.read())
        conn.close()
        logger.info("Database restored.")

def dump_db():
    """Dump DB to SQL file for version control."""
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        os.makedirs(os.path.dirname(SQL_PATH), exist_ok=True)
        with open(SQL_PATH, 'w') as f:
            for line in conn.iterdump():
                f.write(f"{line}\n")
        conn.close()
        logger.info(f"Database dumped to {SQL_PATH}")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    restore_db_if_needed()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        address TEXT UNIQUE,
        city TEXT,
        county TEXT,
        zip TEXT,
        latitude REAL,
        longitude REAL,
        list_price INTEGER,
        price_per_sqft REAL,
        beds INTEGER,
        baths REAL,
        sqft INTEGER,
        lot_sqft INTEGER,
        year_built INTEGER,
        property_type TEXT,
        days_on_market INTEGER,
        hoa_monthly INTEGER,
        listing_remarks TEXT,
        assessed_value INTEGER,
        last_sale_price INTEGER,
        last_sale_date TEXT,
        zoning TEXT,
        deal_score REAL,
        deal_tier TEXT,
        distress_signals TEXT,
        ai_analysis TEXT,
        listing_url TEXT,
        school_rating INTEGER,
        original_price INTEGER,
        price_drop_pct REAL DEFAULT 0.0,
        adu_potential INTEGER DEFAULT 0,
        probate_flag INTEGER DEFAULT 0,
        long_term_owner_flag INTEGER DEFAULT 0,
        primary_distress_badge TEXT,
        first_seen TEXT,
        last_updated TEXT,
        is_active INTEGER DEFAULT 1
    );
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_date TEXT,
        source TEXT,
        properties_scanned INTEGER,
        new_deals_found INTEGER,
        top_deal_address TEXT,
        top_deal_score REAL
    );
    ''')
    
    conn.commit()
    conn.close()

CITY_TO_COUNTY = {
    "san francisco": "San Francisco",
    "oakland": "Alameda", "berkeley": "Alameda", "hayward": "Alameda", "fremont": "Alameda",
    "alameda": "Alameda", "pleasanton": "Alameda", "livermore": "Alameda", "san leandro": "Alameda",
    "union city": "Alameda", "dublin": "Alameda", "newark": "Alameda", "albany": "Alameda",
    "emeryville": "Alameda", "piedmont": "Alameda", "castro valley": "Alameda",
    "walnut creek": "Contra Costa", "concord": "Contra Costa", "richmond": "Contra Costa",
    "san ramon": "Contra Costa", "antioch": "Contra Costa", "pittsburg": "Contra Costa",
    "brentwood": "Contra Costa", "martinez": "Contra Costa", "danville": "Contra Costa",
    "orinda": "Contra Costa", "lafayette": "Contra Costa", "moraga": "Contra Costa",
    "el cerrito": "Contra Costa", "hercules": "Contra Costa", "pinole": "Contra Costa",
    "pacheco": "Contra Costa", "clayton": "Contra Costa", "oakley": "Contra Costa",
    "san rafael": "Marin", "mill valley": "Marin", "novato": "Marin", "tiburon": "Marin",
    "sausalito": "Marin", "san anselmo": "Marin", "larkspur": "Marin", "corte madera": "Marin",
    "ross": "Marin", "fairfax": "Marin", "belvedere": "Marin",
    "napa": "Napa", "st. helena": "Napa", "calistoga": "Napa", "yountville": "Napa",
    "american canyon": "Napa", "angwin": "Napa", "pope valley": "Napa",
    "san mateo": "San Mateo", "redwood city": "San Mateo", "south san francisco": "San Mateo",
    "daly city": "San Mateo", "san bruno": "San Mateo", "pacifica": "San Mateo",
    "menlo park": "San Mateo", "foster city": "San Mateo", "burlingame": "San Mateo",
    "san carlos": "San Mateo", "east palo alto": "San Mateo", "belmont": "San Mateo",
    "millbrae": "San Mateo", "hillsborough": "San Mateo", "woodside": "San Mateo",
    "portola valley": "San Mateo", "brisbane": "San Mateo", "colma": "San Mateo",
    "half moon bay": "San Mateo", "el granada": "San Mateo",
    "san jose": "Santa Clara", "palo alto": "Santa Clara", "mountain view": "Santa Clara",
    "sunnyvale": "Santa Clara", "santa clara": "Santa Clara", "cupertino": "Santa Clara",
    "milpitas": "Santa Clara", "gilroy": "Santa Clara", "campbell": "Santa Clara",
    "morgan hill": "Santa Clara", "los gatos": "Santa Clara", "los altos": "Santa Clara",
    "saratoga": "Santa Clara", "los altos hills": "Santa Clara", "alviso": "Santa Clara",
    "santa rosa": "Sonoma", "petaluma": "Sonoma", "sonoma": "Sonoma", "rohnert park": "Sonoma",
    "windsor": "Sonoma", "healdsburg": "Sonoma", "cloverdale": "Sonoma", "sebastopol": "Sonoma",
    "guerneville": "Sonoma", "bodega bay": "Sonoma", "cotati": "Sonoma"
}

def get_county_from_city_or_zip(city: str, zip_code: str) -> str:
    if not city and not zip_code:
        return None
    city_clean = str(city).strip().lower() if city else ""
    if city_clean in CITY_TO_COUNTY:
        return CITY_TO_COUNTY[city_clean]
    if zip_code:
        zip_str = str(zip_code).strip()[:5]
        if zip_str.isdigit():
            z = int(zip_str)
            if 94101 <= z <= 94188:
                return "San Francisco"
            elif (94002 <= z <= 94080) or (94401 <= z <= 94404):
                return "San Mateo"
            elif (94301 <= z <= 94306) or (95008 <= z <= 95070 and z != 95060) or (95101 <= z <= 95196):
                return "Santa Clara"
            elif 94901 <= z <= 94998:
                if z in [94952, 94954]:
                    return "Sonoma"
                return "Marin"
            elif 95401 <= z <= 95492:
                return "Sonoma"
            elif 94558 <= z <= 94576:
                return "Napa"
            elif z in [94501, 94502] or (94536 <= z <= 94545) or (94550 <= z <= 94552) or z == 94568 or (94577 <= z <= 94580) or (94586 <= z <= 94588) or (94601 <= z <= 94662):
                return "Alameda"
            elif (94509 <= z <= 94531) or (94547 <= z <= 94565) or z in [94572, 94582, 94583] or (94595 <= z <= 94598) or (94801 <= z <= 94850):
                return "Contra Costa"
    return None

def get_mock_school_rating(city: str) -> int:
    city_lower = str(city).strip().lower() if city else ""
    # Map cities to realistic average school ratings (1-10 scale)
    ratings = {
        "palo alto": 9, "cupertino": 9, "los altos": 9, "saratoga": 9, "st. helena": 9, "st helena": 9, "saint helena": 9, "danville": 9, "moraga": 9, "piedmont": 9,
        "mill valley": 8, "tiburon": 8, "orinda": 8, "lafayette": 8, "san ramon": 8, "pleasanton": 8, "berkeley": 8,
        "san francisco": 7, "san mateo": 7, "redwood city": 7, "sunnyvale": 7, "santa clara": 7, "novato": 7,
        "walnut creek": 7, "sonoma": 7, "petaluma": 7, "alameda": 7,
        "oakland": 5, "richmond": 5, "concord": 6, "antioch": 5, "pittsburg": 5, "hayward": 5, "fremont": 7,
        "napa": 6, "santa rosa": 6
    }
    return ratings.get(city_lower, 6) # Default to 6 if unknown

def check_adu_potential(property_type: str, lot_sqft: Any, sqft: Any) -> int:
    try:
        p_type = str(property_type).strip().lower() if property_type else ""
        if p_type in ['sfr', 'single family residential', 'house', 'single family home']:
            lot = float(lot_sqft) if lot_sqft is not None else 0
            bldg = float(sqft) if sqft is not None else 0
            if lot >= 3000 and bldg > 0 and (lot / bldg) >= 3.0:
                return 1
    except: pass
    return 0

def detect_probate(distress_signals: List[str]) -> int:
    signals_lower = [str(s).lower().strip() for s in distress_signals] if distress_signals else []
    probate_keywords = ['probate', 'trust sale', 'conservatorship', 'subject to court approval', 'estate sale']
    if any(kw in signals_lower for kw in probate_keywords):
        return 1
    return 0

def detect_long_term_owner(distress_signals: List[str]) -> int:
    signals_lower = [str(s).lower().strip() for s in distress_signals] if distress_signals else []
    owner_keywords = ['original owner', 'first time on market', 'longtime family']
    if any(kw in signals_lower for kw in owner_keywords):
        return 1
    return 0

def get_primary_distress_badge(distress_signals: List[str], days_on_market: Any) -> str:
    signals_lower = [str(s).lower().strip() for s in distress_signals] if distress_signals else []
    
    if 'fire damage' in signals_lower:
        return 'Fire Damage'
    if any(kw in signals_lower for kw in ['probate', 'trust sale', 'conservatorship', 'subject to court approval', 'estate sale']):
        return 'Probate/Trust'
    if any(kw in signals_lower for kw in ['auction', 'foreclosure', 'bank owned', 'reo', 'short sale']):
        return 'Foreclosure'
    if any(kw in signals_lower for kw in ['contractor', 'gut renovation', 'tear-down', 'uninhabitable']):
        return 'Major Rehab'
    if any(kw in signals_lower for kw in ['fixer', 'needs work', 'handyman', 'tlc', 'as-is', 'deferred maintenance']):
        return 'Fixer-Upper'
    if 'price drop' in signals_lower or 'motivated seller' in signals_lower:
        return 'Motivated'
    
    try:
        dom = float(days_on_market) if days_on_market is not None else 0
        if dom > 60:
            return 'Stale Listing'
    except: pass
    
    return 'Value Opp'

def ingest_redfin(csv_path: str) -> List[Dict]:
    logger.info(f"Ingesting Redfin CSV: {csv_path}")
    raw_props = parse_redfin_csv(csv_path)
    enriched = []
    
    for prop in raw_props:
        address = prop.get('address')
        if not address or not str(address).strip() or str(address).lower().strip().startswith('in accordance'):
            continue
            
        # Standardize keys to match DB schema
        p = {
            'address': address,
            'city': prop.get('city'),
            'county': get_county_from_city_or_zip(prop.get('city'), prop.get('zip_or_postal_code')),
            'zip': prop.get('zip_or_postal_code'),
            'state': prop.get('state_or_province'),
            'list_price': prop.get('price'),
            'beds': prop.get('beds'),
            'baths': prop.get('baths'),
            'sqft': prop.get('square_feet'),
            'lot_sqft': prop.get('lot_size'),
            'year_built': prop.get('year_built'),
            'days_on_market': prop.get('days_on_market'),
            'price_per_sqft': prop.get('price_per_sqft') or prop.get('$/square_feet'),
            'property_type': prop.get('property_type'),
            'listing_url': prop.get('listing_url') or prop.get('url_(link)') or next((v for k, v in prop.items() if k.startswith('url')), None),
            'source': 'redfin',
            'latitude': prop.get('latitude'),
            'longitude': prop.get('longitude'),
            'school_rating': get_mock_school_rating(prop.get('city')),
        }
        
        # Clean numeric fields
        for num_field in ['list_price', 'beds', 'baths', 'sqft', 'lot_sqft', 'year_built', 'days_on_market']:
            try:
                if p[num_field]:
                    # Remove commas and $ for conversion
                    clean_val = str(p[num_field]).replace(',', '').replace('$', '')
                    p[num_field] = float(clean_val) if '.' in clean_val else int(clean_val)
            except:
                p[num_field] = None
        
        remarks = prop.get('listing_remarks', '')
        signals = detect_distress_signals(remarks)
        p['distress_signals'] = ','.join(signals) if signals else None
        p['probate_flag'] = detect_probate(signals)
        p['long_term_owner_flag'] = detect_long_term_owner(signals)
        p['primary_distress_badge'] = get_primary_distress_badge(signals, p.get('days_on_market'))
        p['adu_potential'] = check_adu_potential(p.get('property_type'), p.get('lot_sqft'), p.get('sqft'))
        
        # We would enrich here in a real scenario
        # p = enrich_property(p)
        
        enriched.append(p)
        
    return enriched

def score_all_properties(properties: List[Dict]) -> List[Dict]:
    # Placeholder for median calc, ideally queried from DB
    median_price_per_sqft = 800.0 
    
    scored = []
    for p in properties:
        score, tier = score_property(p, median_price_per_sqft)
        p['deal_score'] = score
        p['deal_tier'] = tier
        scored.append(p)
    return scored

def run_ai_analysis(deals: List[Dict], top_n: int = 10) -> List[Dict]:
    logger.info(f"Running AI analysis on top {top_n} deals...")
    return analyze_top_deals(deals, limit=top_n)

def save_to_db(properties: List[Dict]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    count = 0
    
    for p in properties:
        try:
            cursor.execute('''
            INSERT INTO properties (
                source, address, city, county, zip, list_price, beds, baths, sqft, lot_sqft, 
                year_built, days_on_market, price_per_sqft, property_type, listing_url,
                latitude, longitude, distress_signals, deal_score, deal_tier, ai_analysis,
                school_rating, original_price, price_drop_pct, adu_potential, probate_flag,
                long_term_owner_flag, primary_distress_badge, first_seen, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                price_drop_pct = CASE 
                    WHEN original_price > excluded.list_price THEN ROUND(((original_price - excluded.list_price) * 100.0) / original_price, 2)
                    ELSE 0.0
                END,
                list_price=excluded.list_price,
                beds=excluded.beds,
                baths=excluded.baths,
                sqft=excluded.sqft,
                lot_sqft=excluded.lot_sqft,
                year_built=excluded.year_built,
                days_on_market=excluded.days_on_market,
                price_per_sqft=excluded.price_per_sqft,
                listing_url=excluded.listing_url,
                latitude=excluded.latitude,
                longitude=excluded.longitude,
                distress_signals=excluded.distress_signals,
                deal_score=excluded.deal_score,
                deal_tier=excluded.deal_tier,
                ai_analysis=excluded.ai_analysis,
                county=excluded.county,
                school_rating=excluded.school_rating,
                adu_potential=excluded.adu_potential,
                probate_flag=excluded.probate_flag,
                long_term_owner_flag=excluded.long_term_owner_flag,
                primary_distress_badge=excluded.primary_distress_badge,
                last_updated=excluded.last_updated
            ''', (
                p.get('source'), p.get('address'), p.get('city'), p.get('county'), p.get('zip'),
                p.get('list_price'), p.get('beds'), p.get('baths'), p.get('sqft'),
                p.get('lot_sqft'), p.get('year_built'), p.get('days_on_market'),
                p.get('price_per_sqft'), p.get('property_type'), p.get('listing_url'),
                p.get('latitude'), p.get('longitude'), p.get('distress_signals'),
                p.get('deal_score'), p.get('deal_tier'), p.get('ai_analysis'),
                p.get('school_rating'), p.get('list_price'), 0.0,
                p.get('adu_potential'), p.get('probate_flag'), p.get('long_term_owner_flag'),
                p.get('primary_distress_badge'), now, now
            ))
            count += 1
        except Exception as e:
            logger.error(f"Error saving {p.get('address')}: {e}")
            
    conn.commit()
    conn.close()
    logger.info(f"Saved/Updated {count} properties to DB.")

def log_scan_history(source: str, total_scanned: int, new_deals: int, top_deal: Dict = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_date = datetime.now().strftime("%Y-%m-%d")
    top_address = top_deal.get('address') if top_deal else 'N/A'
    top_score = top_deal.get('deal_score') if top_deal else 0.0
    
    cursor.execute('''
    INSERT INTO scan_history (scan_date, source, properties_scanned, new_deals_found, top_deal_address, top_deal_score)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (now_date, source, total_scanned, new_deals, top_address, top_score))
    conn.commit()
    conn.close()
    logger.info(f"Scan history logged: Scanned {total_scanned}, Found {new_deals} deals.")

def run_scan(csv_path: str = None, use_rentcast: bool = False, counties: List[str] = None, 
             analyze: bool = False, email_to: str = None, dry_run: bool = False):
    
    if not dry_run:
        init_db()
        
    properties = []
    
    if csv_path:
        properties.extend(ingest_redfin(csv_path))
        
    if use_rentcast:
        logger.info("RentCast integration not yet implemented for bulk scan.")
        
    if not properties:
        logger.warning("No properties to process.")
        return
        
    logger.info(f"Scoring {len(properties)} properties...")
    properties = score_all_properties(properties)
    
    # Sort by score
    properties.sort(key=lambda x: x.get('deal_score', 0), reverse=True)
    
    if analyze:
        properties = run_ai_analysis(properties, top_n=5)
        
    if not dry_run:
        new_deals_count = len([p for p in properties if p.get('deal_tier') != 'pass'])
        top_deal = properties[0] if properties else None
        log_scan_history('Redfin CSV' if csv_path else 'RentCast', len(properties), new_deals_count, top_deal)
        save_to_db(properties)
        
    if email_to:
        logger.info(f"Sending email alert to {email_to}...")
        top_deals = [p for p in properties if p.get('deal_tier') in ['strong_buy', 'worth_a_look']][:10]
        send_deal_alert(top_deals, email_to)
        
    if not dry_run:
        dump_db()

    logger.info("Scan complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bay Opps Deal Scanner")
    parser.add_argument("--csv", help="Path to Redfin CSV")
    parser.add_argument("--rentcast", action="store_true", help="Fetch from RentCast")
    parser.add_argument("--counties", help="Comma-separated county list")
    parser.add_argument("--analyze", action="store_true", help="Run Gemini analysis on top deals")
    parser.add_argument("--email", help="Send alert email to this address")
    parser.add_argument("--dry-run", action="store_true", help="Parse and score but don't save")
    
    args = parser.parse_args()
    
    counties_list = args.counties.split(',') if args.counties else []
    
    run_scan(
        csv_path=args.csv,
        use_rentcast=args.rentcast,
        counties=counties_list,
        analyze=args.analyze,
        email_to=args.email,
        dry_run=args.dry_run
    )
