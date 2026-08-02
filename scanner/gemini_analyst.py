"""
Gemini AI Deal Analysis
Leverages Gemini for in-depth real estate deal analysis using a multi-model fallback pattern.
"""

import os
import logging
import google.generativeai as genai
from typing import Dict, List

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def _init_gemini():
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Analysis will be skipped.")
        return False
    genai.configure(api_key=GEMINI_API_KEY.strip())
    return True

def analyze_deal(property_dict: Dict) -> str:
    """
    Generate an investment analysis narrative for a single deal.
    """
    if not _init_gemini():
        return ""
        
    system_instruction = (
        "You are an expert Bay Area real estate investor and flipper. "
        "Evaluate the following property data and provide a concise analysis covering:\n"
        "1. Renovation cost estimate\n"
        "2. After Repair Value (ARV) potential\n"
        "3. Neighborhood trends\n"
        "4. Risk factors\n"
        "5. Investment thesis (flip vs hold vs develop)\n\n"
        "Be concise and objective. Output plain text."
    )
    
    context = f"Property Address: {property_dict.get('address')}\n"
    for k, v in property_dict.items():
        if k not in ['address']:
            context += f"{k}: {v}\n"
            
    models_to_try = [
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
    ]
    
    for model_id in models_to_try:
        try:
            logger.info(f"Analyzing {property_dict.get('address')} with {model_id}...")
            model = genai.GenerativeModel(model_id, system_instruction=system_instruction)
            response = model.generate_content(context)
            
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.warning(f"Model {model_id} failed: {e}")
            continue
            
    return ""

def analyze_top_deals(deals: List[Dict], limit: int = 5) -> List[Dict]:
    """
    Batch analyze top deals.
    """
    top_deals = sorted(deals, key=lambda x: x.get('deal_score', 0), reverse=True)[:limit]
    for deal in top_deals:
        deal['ai_analysis'] = analyze_deal(deal)
    return top_deals
