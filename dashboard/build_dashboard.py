import os
import json
import sqlite3
import argparse
from datetime import datetime
import random

def get_sample_data():
    properties = []
    cities = [
        "San Francisco", "Oakland", "San Jose", "Berkeley", "Palo Alto", 
        "San Mateo", "Walnut Creek", "Concord", "Hayward", "Fremont",
        "San Rafael", "Mill Valley", "Novato",  # Marin
        "Napa", "St. Helena",                    # Napa
        "Santa Rosa", "Petaluma", "Sonoma"        # Sonoma
    ]
    counties = {
        "San Francisco": "San Francisco", "Oakland": "Alameda", "San Jose": "Santa Clara", 
        "Berkeley": "Alameda", "Palo Alto": "Santa Clara", "San Mateo": "San Mateo", 
        "Walnut Creek": "Contra Costa", "Concord": "Contra Costa", "Hayward": "Alameda", 
        "Fremont": "Alameda",
        "San Rafael": "Marin", "Mill Valley": "Marin", "Novato": "Marin",
        "Napa": "Napa", "St. Helena": "Napa",
        "Santa Rosa": "Sonoma", "Petaluma": "Sonoma", "Sonoma": "Sonoma"
    }
    
    street_names = [
        "Oak St", "Main St", "Elm Ave", "Cedar Blvd", "Pine Ln", "Maple Dr",
        "Redwood Way", "Hillside Rd", "Valley View Dr", "Mission Blvd",
        "Vineyard Ln", "Ranch Rd", "Harbor Dr", "Ridge Rd", "Laurel Ave"
    ]
    
    for i in range(30):
        city = random.choice(cities)
        county = counties[city]
        score = random.randint(20, 95)
        
        if score >= 80: tier = "Strong Buy"
        elif score >= 60: tier = "Worth a Look"
        elif score >= 40: tier = "Monitor"
        else: tier = "Pass"
        
        price = random.randint(450000, 2800000)
        sqft = random.randint(900, 3500)
        
        # Lat/lng ranges covering wider Bay Area including North Bay
        lat_base = {"San Francisco": 37.77, "Alameda": 37.65, "Santa Clara": 37.35,
                    "San Mateo": 37.50, "Contra Costa": 37.90, "Marin": 37.97,
                    "Napa": 38.30, "Sonoma": 38.25}
        lng_base = {"San Francisco": -122.42, "Alameda": -122.10, "Santa Clara": -121.90,
                    "San Mateo": -122.30, "Contra Costa": -122.05, "Marin": -122.53,
                    "Napa": -122.30, "Sonoma": -122.70}
        has_drop = random.random() < 0.25
        orig_price = price if not has_drop else int(price * 1.12)
        drop_pct = 0.0 if not has_drop else 10.7
        
        prop_type = random.choice(["SFR", "Multi-Family", "Condo", "Land"])
        lot_size = sqft * random.uniform(1.5, 5)
        adu = 1 if prop_type == "SFR" and lot_size >= 3000 and (lot_size / sqft) >= 3.0 else 0
        
        probate = 1 if random.random() < 0.1 else 0
        long_owner = 1 if random.random() < 0.15 else 0
        
        badge = "Value Opp"
        if probate: badge = "Probate/Trust"
        elif has_drop: badge = "Motivated"
        elif random.random() < 0.4: badge = "Fixer-Upper"
        
        properties.append({
            "id": f"prop_{i}",
            "address": f"{random.randint(100, 9999)} {random.choice(street_names)}",
            "city": city,
            "county": county,
            "zip": f"94{random.randint(0, 999):03d}",
            "price": price,
            "beds": random.randint(2, 5),
            "baths": random.choice([1, 1.5, 2, 2.5, 3]),
            "sqft": sqft,
            "lot_sqft": lot_size,
            "year_built": random.randint(1920, 2010),
            "dom": random.randint(1, 120),
            "score": score,
            "tier": tier,
            "property_type": prop_type,
            "price_per_sqft": round(price / sqft),
            "distress_signals": random.sample(["Price Drop", "Estate Sale", "As-Is", "Needs TLC", "Motivated Seller", "Fixer", "Probate"], random.randint(0, 3)),
            "ai_analysis": "This property shows potential for forced appreciation through cosmetic updates. The lot size is generous, providing potential for an ADU. Comps in the area suggest a strong ARV.",
            "lat": lat_base.get(county, 37.7) + random.uniform(-0.1, 0.1),
            "lng": lng_base.get(county, -122.2) + random.uniform(-0.1, 0.1),
            "url": "#",
            "school_rating": random.randint(4, 10),
            "original_price": orig_price,
            "price_drop_pct": drop_pct,
            "adu_potential": adu,
            "probate_flag": probate,
            "long_term_owner_flag": long_owner,
            "primary_distress_badge": badge
        })
    
    scan_history = [
        {"date": datetime.now().strftime("%Y-%m-%d"), "source": "MLS", "scanned": 1500, "new_deals": 12, "top_deal": properties[0]['address'], "top_score": properties[0]['score']},
        {"date": "2023-10-26", "source": "Zillow", "scanned": 1200, "new_deals": 5, "top_deal": "456 Oak Ave", "top_score": 92}
    ]
    # Filter out Pass tier properties to match actual DB query behavior
    filtered_properties = [p for p in properties if p['tier'] != "Pass"]
    return filtered_properties, scan_history

def get_db_data(db_path):
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Check if table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='properties'")
        if not cur.fetchone():
            return [], []
            
        cur.execute("SELECT * FROM properties WHERE is_active = 1 AND deal_tier != 'pass'")
        raw_props = [dict(row) for row in cur.fetchall()]
        
        # Map DB column names to template-expected keys
        properties = []
        for r in raw_props:
            import json as _json
            distress = r.get('distress_signals', '')
            if distress:
                try:
                    distress_list = _json.loads(distress)
                except (ValueError, TypeError):
                    distress_list = [s.strip() for s in distress.split(',') if s.strip()]
            else:
                distress_list = []
            
            properties.append({
                "id": r.get("id"),
                "address": r.get("address", ""),
                "city": r.get("city", ""),
                "county": r.get("county", ""),
                "zip": r.get("zip", ""),
                "price": r.get("list_price") or 0,
                "beds": r.get("beds") or 0,
                "baths": r.get("baths") or 0,
                "sqft": r.get("sqft") or 0,
                "lot_sqft": r.get("lot_sqft") or 0,
                "year_built": r.get("year_built") or 0,
                "dom": r.get("days_on_market") or 0,
                "score": r.get("deal_score") or 0,
                "tier": {"strong_buy": "Strong Buy", "worth_a_look": "Worth a Look", 
                         "monitor": "Monitor", "pass": "Pass"}.get(r.get("deal_tier", "pass"), "Pass"),
                "property_type": r.get("property_type", ""),
                "price_per_sqft": r.get("price_per_sqft") or 0,
                "distress_signals": distress_list,
                "ai_analysis": r.get("ai_analysis", ""),
                "lat": r.get("latitude"),
                "lng": r.get("longitude"),
                "url": r.get("listing_url", "#"),
                "school_rating": r.get("school_rating") or 6,
                "original_price": r.get("original_price") or r.get("list_price") or 0,
                "price_drop_pct": r.get("price_drop_pct") or 0.0,
                "adu_potential": r.get("adu_potential") or 0,
                "probate_flag": r.get("probate_flag") or 0,
                "long_term_owner_flag": r.get("long_term_owner_flag") or 0,
                "primary_distress_badge": r.get("primary_distress_badge") or "Value Opp"
            })
        
        cur.execute("SELECT * FROM scan_history ORDER BY scan_date DESC LIMIT 10")
        raw_history = [dict(row) for row in cur.fetchall()]
        scan_history = [{
            "date": h.get("scan_date", ""),
            "source": h.get("source", ""),
            "scanned": h.get("properties_scanned", 0),
            "new_deals": h.get("new_deals_found", 0),
            "top_deal": h.get("top_deal_address", ""),
            "top_score": h.get("top_deal_score", 0)
        } for h in raw_history]
        
        conn.close()
        return properties, scan_history
    except Exception as e:
        print(f"Error reading DB: {e}")
        return [], []

def build_dashboard(sample_mode=False):
    if sample_mode:
        print("Using sample data...")
        properties, scan_history = get_sample_data()
    else:
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'deals.db')
        properties, scan_history = get_db_data(db_path)
    
    # Compute KPIs
    total_deals = len(properties)
    strong_buys = len([p for p in properties if p.get('score', 0) >= 80])
    avg_score = sum(p.get('score', 0) for p in properties) / total_deals if total_deals > 0 else 0
    best_deal_prop = max(properties, key=lambda x: x.get('score', 0)) if properties else None
    
    kpis = {
        "total_deals": total_deals,
        "strong_buys": strong_buys,
        "avg_score": round(avg_score),
        "best_deal": f"{best_deal_prop['address']} ({best_deal_prop['score']})" if best_deal_prop else "N/A"
    }
    
    # Compute Chart Data
    chart_data = {
        "score_dist": [0,0,0,0,0], # 0-19, 20-39, 40-59, 60-79, 80-100
        "dom_dist": [0,0,0,0], # <30, 30-60, 60-90, 90+
        "city_data": {}
    }
    
    for p in properties:
        score = p.get('score', 0)
        if score < 20: chart_data["score_dist"][0] += 1
        elif score < 40: chart_data["score_dist"][1] += 1
        elif score < 60: chart_data["score_dist"][2] += 1
        elif score < 80: chart_data["score_dist"][3] += 1
        else: chart_data["score_dist"][4] += 1
        
        dom = p.get('dom', 0)
        if dom < 30: chart_data["dom_dist"][0] += 1
        elif dom < 60: chart_data["dom_dist"][1] += 1
        elif dom < 90: chart_data["dom_dist"][2] += 1
        else: chart_data["dom_dist"][3] += 1
        
        city = p.get('city', 'Unknown')
        if city not in chart_data["city_data"]:
            chart_data["city_data"][city] = []
        chart_data["city_data"][city].append(p.get('price', 0))
    
    chart_data["city_avg"] = {city: sum(prices)/len(prices) for city, prices in chart_data["city_data"].items()}
    
    # Read template
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'dashboard_template.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        html = f.read()
        
    html = html.replace('{{PROPERTIES_JSON}}', json.dumps(properties))
    html = html.replace('{{KPI_JSON}}', json.dumps(kpis))
    html = html.replace('{{CHART_DATA_JSON}}', json.dumps(chart_data))
    html = html.replace('{{SCAN_HISTORY_JSON}}', json.dumps(scan_history))
    html = html.replace('{{GENERATED_AT}}', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Write output
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'index.html')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
        
    print(f"Dashboard generated successfully at {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', action='store_true', help='Generate with sample data')
    args = parser.parse_args()
    build_dashboard(args.sample)
