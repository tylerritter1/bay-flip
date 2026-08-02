"""
Bay Flip Deal Scanner
Main orchestrator for scanning, scoring, and analyzing real estate deals.
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

def ingest_redfin(csv_path: str) -> List[Dict]:
    logger.info(f"Ingesting Redfin CSV: {csv_path}")
    raw_props = parse_redfin_csv(csv_path)
    enriched = []
    
    for prop in raw_props:
        # Standardize keys to match DB schema
        p = {
            'address': prop.get('address'),
            'city': prop.get('city'),
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
            'listing_url': prop.get('url_(link)'),
            'source': 'redfin',
            'latitude': prop.get('latitude'),
            'longitude': prop.get('longitude'),
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
                source, address, city, zip, list_price, beds, baths, sqft, lot_sqft, 
                year_built, days_on_market, price_per_sqft, property_type, listing_url,
                latitude, longitude, distress_signals, deal_score, deal_tier, ai_analysis,
                first_seen, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                list_price=excluded.list_price,
                days_on_market=excluded.days_on_market,
                deal_score=excluded.deal_score,
                deal_tier=excluded.deal_tier,
                ai_analysis=excluded.ai_analysis,
                last_updated=excluded.last_updated
            ''', (
                p.get('source'), p.get('address'), p.get('city'), p.get('zip'),
                p.get('list_price'), p.get('beds'), p.get('baths'), p.get('sqft'),
                p.get('lot_sqft'), p.get('year_built'), p.get('days_on_market'),
                p.get('price_per_sqft'), p.get('property_type'), p.get('listing_url'),
                p.get('latitude'), p.get('longitude'), p.get('distress_signals'),
                p.get('deal_score'), p.get('deal_tier'), p.get('ai_analysis'),
                now, now
            ))
            count += 1
        except Exception as e:
            logger.error(f"Error saving {p.get('address')}: {e}")
            
    conn.commit()
    conn.close()
    logger.info(f"Saved/Updated {count} properties to DB.")

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
        save_to_db(properties)
        
    if email_to:
        logger.info(f"Sending email alert to {email_to}...")
        top_deals = [p for p in properties if p.get('deal_tier') in ['strong_buy', 'worth_a_look']][:10]
        send_deal_alert(top_deals, email_to)
        
    if not dry_run:
        dump_db()

    logger.info("Scan complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bay Flip Deal Scanner")
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
