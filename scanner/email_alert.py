"""
Email Alert Service
Sends HTML digest alerts of the top deals using Gmail SMTP.
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD", "")

def send_deal_alert(deals: List[Dict], recipient: str):
    """Send dark-themed HTML email with top deals."""
    if not all([EMAIL_FROM, EMAIL_PASSWORD, recipient]):
        logger.warning("Email configuration missing. Skipping alert.")
        return
        
    today = datetime.today().strftime("%Y-%m-%d")
    
    html = f"""
    <html>
    <head>
      <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap" rel="stylesheet">
      <style>
        body {{ font-family: 'Outfit', sans-serif; background-color: #0f1115; color: #e0e0e0; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #ffffff; text-align: center; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        .card {{ background-color: #1a1d24; border-radius: 8px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #4CAF50; }}
        .card h2 {{ margin-top: 0; color: #fff; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-right: 10px; }}
        .score {{ background-color: #4CAF50; color: #000; }}
        .tier {{ background-color: #2196F3; color: #fff; }}
        .details {{ margin-top: 15px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 14px; }}
        .ai-summary {{ margin-top: 15px; padding: 10px; background-color: #2a2e39; border-radius: 4px; font-size: 13px; line-height: 1.5; }}
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Bay Flip Deals — {today}</h1>
    """
    
    for deal in deals:
        addr = deal.get('address', 'Unknown Address')
        price = deal.get('list_price') or deal.get('price', 0)
        score = deal.get('deal_score', 0)
        tier = deal.get('deal_tier', 'N/A')
        ai_text = deal.get('ai_analysis', 'No AI analysis available.')
        
        html += f"""
        <div class="card">
          <h2>{addr}</h2>
          <div>
            <span class="badge score">Score: {score}</span>
            <span class="badge tier">{tier.replace('_', ' ').title()}</span>
          </div>
          <div class="details">
            <div><strong>Price:</strong> ${price:,.0f}</div>
            <div><strong>Beds/Baths:</strong> {deal.get('beds', '-')} / {deal.get('baths', '-')}</div>
            <div><strong>Sqft:</strong> {deal.get('sqft', '-')}</div>
            <div><strong>Lot Sqft:</strong> {deal.get('lot_sqft', '-')}</div>
            <div><strong>Price/Sqft:</strong> ${deal.get('price_per_sqft', 0):.2f}</div>
            <div><strong>DOM:</strong> {deal.get('days_on_market', '-')}</div>
          </div>
          <div class="ai-summary">
            <strong>AI Analysis:</strong><br/>
            {ai_text.replace(chr(10), '<br/>')}
          </div>
        </div>
        """
        
    html += """
      </div>
    </body>
    </html>
    """
    
    msg = MIMEText(html, "html")
    msg["Subject"] = f"Bay Flip Top Deals — {today}"
    msg["From"] = EMAIL_FROM
    msg["To"] = recipient
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info("Deal alert email sent successfully.")
    except Exception as e:
        logger.error(f"Email failed: {e}")
