"""
Deal Scoring Engine
Computes a composite score 0-100 based on multiple weighted factors.
"""

from typing import Dict, Tuple

# Weights
W_PRICE_SQFT = 0.25
W_LOT_RATIO = 0.20
W_DAYS_MARKET = 0.15
W_DISTRESS = 0.15
W_ASSESSED = 0.15
W_AGE = 0.10

def score_property(property_dict: Dict, median_price_per_sqft: float) -> Tuple[float, str]:
    """
    Returns (score, tier)
    """
    score = 0.0
    
    # 1. Price per sqft vs median (25%)
    try:
        price_sqft = float(property_dict.get('price_per_sqft', 0))
        if price_sqft > 0 and median_price_per_sqft > 0:
            ratio = price_sqft / median_price_per_sqft
            # If property is 20% below median, it gets high score
            if ratio < 0.7:
                score += W_PRICE_SQFT * 100
            elif ratio < 1.0:
                score += W_PRICE_SQFT * (1.0 - ratio) * 333  # scales up to ~100
    except: pass
    
    # 2. Lot to building ratio (20%)
    try:
        lot = float(property_dict.get('lot_sqft', 0))
        bldg = float(property_dict.get('sqft', 0))
        if bldg > 0:
            ratio = lot / bldg
            if ratio > 5:
                score += W_LOT_RATIO * 100
            elif ratio > 1:
                score += W_LOT_RATIO * (ratio / 5.0) * 100
    except: pass
        
    # 3. Days on market (15%)
    try:
        dom = float(property_dict.get('days_on_market', 0))
        if dom > 90:
            score += W_DAYS_MARKET * 100
        elif dom > 30:
            score += W_DAYS_MARKET * ((dom - 30) / 60.0) * 100
    except: pass
        
    # 4. Distress Keywords (15%)
    distress = property_dict.get('distress_signals', [])
    if distress is None:
        distress = []
    elif isinstance(distress, str):
        distress = distress.split(',') if distress else []
    
    if len(distress) >= 3:
        score += W_DISTRESS * 100
    elif len(distress) > 0:
        score += W_DISTRESS * (len(distress) / 3.0) * 100
        
    # 5. Assessed vs List Price (15%)
    try:
        assessed = float(property_dict.get('assessed_value', 0))
        list_price = float(property_dict.get('list_price', 0) or property_dict.get('price', 0))
        if list_price > 0 and assessed > 0:
            # If assessed is much higher than list, it's good
            if assessed > list_price * 1.5:
                score += W_ASSESSED * 100
            elif assessed > list_price:
                score += W_ASSESSED * 50
    except: pass
        
    # 6. Age and Condition (10%)
    try:
        year = float(property_dict.get('year_built', 0))
        if year > 0:
            age = 2026 - year
            if age > 50:
                score += W_AGE * 100
            elif age > 20:
                score += W_AGE * 50
    except: pass
    
    final_score = min(max(round(score, 2), 0.0), 100.0)
    tier = get_deal_tier(final_score)
    return final_score, tier

def get_deal_tier(score: float) -> str:
    """Returns 'strong_buy' (80-100), 'worth_a_look' (60-79), 'monitor' (40-59), 'pass' (0-39)"""
    if score >= 80:
        return 'strong_buy'
    elif score >= 60:
        return 'worth_a_look'
    elif score >= 40:
        return 'monitor'
    else:
        return 'pass'
