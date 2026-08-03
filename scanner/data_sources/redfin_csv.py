"""
Redfin CSV Parser
Parses Redfin 'Download All' CSV exports and extracts distress signals.
"""

import csv
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

DISTRESS_KEYWORDS = [
    'as-is', 'fixer', 'investor special', 'estate sale', 'reo', 'short sale',
    'deferred maintenance', 'needs work', 'tlc', 'handyman', 'potential',
    'contractor', 'gut renovation', 'fire damage', 'probate', 'bank owned',
    'foreclosure', 'auction', 'cash only', 'sold as-is', 'diamond in the rough',
    'bring your vision', 'development opportunity', 'tear-down', 'uninhabitable',
    'original owner', 'first time on market', 'longtime family', 'trust sale',
    'conservatorship', 'subject to court approval'
]

def parse_redfin_csv(filepath: str) -> List[Dict[str, Any]]:
    """
    Reads a Redfin CSV, normalizes column names, and returns a list of property dicts.
    """
    properties = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                norm_row = {}
                for k, v in row.items():
                    if k is None:
                        continue
                    # Normalize keys: upper to lower, spaces to underscores
                    norm_key = k.strip().lower().replace(' ', '_').replace('$/square_feet', 'price_per_sqft').replace('$/sqft', 'price_per_sqft')
                    if norm_key.startswith('url'):
                        norm_key = 'listing_url'
                    norm_row[norm_key] = v
                properties.append(norm_row)
    except Exception as e:
        logger.error(f"Failed to parse Redfin CSV {filepath}: {e}")
    
    return properties

def detect_distress_signals(listing_remarks: str) -> List[str]:
    """
    Scans listing remarks for distress keywords.
    """
    if not listing_remarks:
        return []
    
    signals = []
    remarks_lower = listing_remarks.lower()
    for kw in DISTRESS_KEYWORDS:
        if kw in remarks_lower:
            signals.append(kw)
    
    return signals

def calculate_lot_to_building_ratio(lot_sqft: float, building_sqft: float) -> float:
    """
    Calculates the ratio of lot size to building size.
    Returns 0.0 if data is invalid.
    """
    try:
        lot = float(lot_sqft)
        building = float(building_sqft)
        if building > 0:
            return lot / building
    except (ValueError, TypeError):
        pass
    return 0.0
