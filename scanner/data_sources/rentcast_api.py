"""
RentCast API Client
Lightweight client for the RentCast API to fetch property data and valuations.
"""

import logging
import requests
from typing import Dict, List, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class RentCastClient:
    BASE_URL = "https://api.rentcast.io/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": self.api_key,
            "Accept": "application/json"
        })
        
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        
        self.calls_this_month = 0
        self.MONTHLY_LIMIT = 50
        self.WARN_THRESHOLD = 40

    def _track_call(self):
        self.calls_this_month += 1
        if self.calls_this_month == self.WARN_THRESHOLD:
            logger.warning(f"RentCast API: Reached {self.WARN_THRESHOLD}/{self.MONTHLY_LIMIT} monthly limit.")
        elif self.calls_this_month > self.MONTHLY_LIMIT:
            logger.error("RentCast API: Monthly limit exceeded.")

    def get_property(self, address: str) -> Optional[Dict]:
        """Single property lookup by address."""
        self._track_call()
        url = f"{self.BASE_URL}/properties"
        try:
            response = self.session.get(url, params={"address": address}, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                return data[0]
        except Exception as e:
            logger.error(f"Failed to fetch property {address}: {e}")
        return None

    def get_listings(self, zip_code: str, status: str = 'Active') -> List[Dict]:
        """Fetch active for-sale listings in a zip code."""
        self._track_call()
        url = f"{self.BASE_URL}/listings/sale"
        try:
            response = self.session.get(url, params={"zipCode": zip_code, "status": status}, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch listings for zip {zip_code}: {e}")
            return []

    def get_valuation(self, address: str) -> Optional[Dict]:
        """Fetch Automated Valuation Model (AVM) estimate."""
        self._track_call()
        url = f"{self.BASE_URL}/avm/value"
        try:
            response = self.session.get(url, params={"address": address, "propertyType": "Single Family"}, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch valuation for {address}: {e}")
            return None
