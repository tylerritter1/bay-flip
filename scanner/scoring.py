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
    Returns (score, tier) based on dynamic weight normalization.
    """
    score = 0.0
    weight_used = 0.0
    
    # 1. Price per sqft vs median (25%)
    try:
        price_sqft = property_dict.get('price_per_sqft')
        if price_sqft is not None:
            price_sqft = float(price_sqft)
            if price_sqft > 0 and median_price_per_sqft > 0:
                weight_used += W_PRICE_SQFT
                ratio = price_sqft / median_price_per_sqft
                # Softened: 20% below median gets max points (ratio < 0.8)
                if ratio < 0.8:
                    score += W_PRICE_SQFT * 100
                elif ratio < 1.0:
                    score += W_PRICE_SQFT * (1.0 - ratio) * 500  # scales up to 100
    except: pass
    
    # 2. Lot to building ratio (20%)
    try:
        lot = property_dict.get('lot_sqft')
        bldg = property_dict.get('sqft')
        if lot is not None and bldg is not None:
            lot = float(lot)
            bldg = float(bldg)
            if bldg > 0 and lot > 0:
                weight_used += W_LOT_RATIO
                ratio = lot / bldg
                # Softened: 3x lot ratio gets max points (ratio > 3)
                if ratio > 3:
                    score += W_LOT_RATIO * 100
                elif ratio > 1:
                    score += W_LOT_RATIO * ((ratio - 1.0) / 2.0) * 100
    except: pass
        
    # 3. Days on market (15%)
    try:
        dom = property_dict.get('days_on_market')
        if dom is not None:
            dom = float(dom)
            weight_used += W_DAYS_MARKET
            # Softened: 60+ days on market gets max points
            if dom > 60:
                score += W_DAYS_MARKET * 100
            elif dom > 14:
                score += W_DAYS_MARKET * ((dom - 14) / 46.0) * 100
    except: pass
        
    # 4. Distress Keywords (15%) - Remarks are always available
    distress = property_dict.get('distress_signals', [])
    if distress is None:
        distress = []
    elif isinstance(distress, str):
        distress = distress.split(',') if distress else []
    
    weight_used += W_DISTRESS
    # Softened: 2+ distress keywords gets max points
    if len(distress) >= 2:
        score += W_DISTRESS * 100
    elif len(distress) == 1:
        score += W_DISTRESS * 50
        
    # 5. Assessed vs List Price (15%)
    try:
        assessed = property_dict.get('assessed_value')
        list_price = property_dict.get('list_price') or property_dict.get('price')
        if assessed is not None and list_price is not None:
            assessed = float(assessed)
            list_price = float(list_price)
            if list_price > 0 and assessed > 0:
                weight_used += W_ASSESSED
                # Softened: Assessed value 1.2x list price gets max points
                if assessed > list_price * 1.2:
                    score += W_ASSESSED * 100
                elif assessed > list_price:
                    score += W_ASSESSED * 60
    except: pass
        
    # 6. Age and Condition (10%)
    try:
        year = property_dict.get('year_built')
        if year is not None:
            year = float(year)
            if year > 0:
                weight_used += W_AGE
                age = 2026 - year
                # Softened: 40+ years old gets max points
                if age > 40:
                    score += W_AGE * 100
                elif age > 15:
                    score += W_AGE * 50
    except: pass
    
    # Normalize score based on fields actually available
    if weight_used > 0:
        normalized_score = (score / (weight_used * 100.0)) * 100.0
    else:
        normalized_score = 0.0
        
    final_score = min(max(round(normalized_score, 2), 0.0), 100.0)
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
