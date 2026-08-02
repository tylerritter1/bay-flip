"""
County Assessor SODA API Integration
Integrates with Bay Area county open data portals via the Socrata Open Data API (SODA).
"""

import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)

COUNTY_CONFIGS = {
    'san francisco': {
        'domain': 'data.sfgov.org',
        'assessor_dataset': 'todo_sf_assessor_id', # TODO: Find exact SODA dataset ID
    },
    'alameda': {
        'domain': 'data.acgov.org',
        'assessor_dataset': 'todo_al_assessor_id',
    },
    'santa clara': {
        'domain': 'data.sccgov.org',
        'assessor_dataset': 'todo_sc_assessor_id',
    },
    'san mateo': {
        'domain': 'data.smcgov.org',
        'assessor_dataset': 'todo_sm_assessor_id',
    },
    'contra costa': {
        'domain': 'data.cccounty.us',
        'assessor_dataset': 'todo_cc_assessor_id', # Uses ArcGIS, may need different query pattern
    },
    'marin': {
        'domain': 'data.marincounty.org',
        'assessor_dataset': 'todo_marin_assessor_id',
    },
    'napa': {
        'domain': 'data.countyofnapa.org',
        'assessor_dataset': 'todo_napa_assessor_id',
    },
    'sonoma': {
        'domain': 'data.sonomacounty.ca.gov',
        'assessor_dataset': 'todo_sonoma_assessor_id',
    },
}

def query_assessor_data(county: str, address: str) -> Dict[str, Any]:
    """
    Query county for assessed value, lot info, and zoning.
    """
    county_lower = county.lower()
    if county_lower not in COUNTY_CONFIGS:
        logger.warning(f"No SODA config for county: {county}")
        return {}
        
    config = COUNTY_CONFIGS[county_lower]
    domain = config['domain']
    dataset = config['assessor_dataset']
    
    # Placeholder for actual SODA query logic
    url = f"https://{domain}/resource/{dataset}.json"
    
    # In a real implementation we would do:
    # try:
    #     res = requests.get(url, params={"$where": f"address like '%{address}%'", "$limit": 1})
    #     return res.json()[0] if res.json() else {}
    # except Exception as e: ...
    
    return {}

def get_tax_delinquency(county: str, address: str) -> Dict[str, Any]:
    """
    Check for tax delinquency status.
    """
    # Placeholder for MVP
    return {}

def enrich_property(property_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add county data to a property record.
    """
    county = property_dict.get('county', '')
    address = property_dict.get('address', '')
    
    if county and address:
        assessor_data = query_assessor_data(county, address)
        tax_data = get_tax_delinquency(county, address)
        
        # Merge data gracefully
        property_dict['assessed_value'] = assessor_data.get('assessed_value')
        property_dict['zoning'] = assessor_data.get('zoning')
        property_dict['tax_delinquent'] = tax_data.get('is_delinquent', False)
        
    return property_dict
