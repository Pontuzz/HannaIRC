import requests
import uuid
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime
import os
import json

"""
Web Scraper Template - Schema Reference

This script scrapes web content and submits to TeachHanna using the unified Qdrant schema:

  text              (str)  - Extracted page text
  source_type       (str)  - Always "web"
  confidence        (float) - 0.0-1.0 quality score (user-provided)
  timestamp         (str)  - ISO-8601 date (auto-generated)
  sourceUser        (null) - Not applicable for web scraping
  url               (str)  - Source URL
  title             (str)  - Page title extracted
  tags              (array) - User-provided categories
  related_entities  (array) - User-provided concepts

Configuration:
  1. Set webhook_url to your n8n TeachHanna endpoint
  2. Set ca_cert_path if using self-signed SSL
  3. Place excluded_domains.json in working directory

Run:
  python scrape_to_n8n.py
  (then provide URLs and metadata when prompted)

Respects excluded_domains.json for ethical scraping.
"""

def load_excluded_domains_json(filepath):
    """Load excluded domains from a JSON file with detailed info."""
    if not os.path.exists(filepath):
        return set()
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            return set(entry['domain'].strip().lower() for entry in data if 'domain' in entry)
        except Exception as e:
            print(f"Error loading exclusions JSON: {e}")
            return set()


def scrape_and_send_to_n8n(urls, webhook_url, ca_cert_path=None, excluded_domains_path=None):
    """
    Scrape multiple webpages and send their text content to an n8n webhook for embedding and vector storage.
    Args:
        urls (list): List of URLs to scrape.
        webhook_url (str): The n8n webhook endpoint (TeachHanna).
        ca_cert_path (str): Path to CA certificate for SSL verification.
        excluded_domains_path (str): Path to exclusions list (JSON).
    """
    excluded_domains = load_excluded_domains_json(excluded_domains_path) if excluded_domains_path else set()
    tags = input("Tags for this batch (comma-separated, optional): ").strip()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    source_type = "web"
    confidence = 0.8
    related_entities = input("Related entities for this batch (comma-separated, optional): ").strip()
    related_list = [t.strip() for t in related_entities.split(",") if t.strip()] if related_entities else []
    user_agent = "HannaWebScraper/1.0 (+https://botinfo.hivenet.dev/)"
    headers = {"User-Agent": user_agent}
    for url in urls:
        domain = urlparse(url).netloc.lower()
        if any(domain == ex or domain.endswith('.' + ex) for ex in excluded_domains):
            print(f"Skipping excluded domain: {domain}")
            continue
        try:
            print(f"Scraping: {url}")
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            title = soup.title.string.strip() if soup.title and soup.title.string else url
            print(f"Scraped text (first 500 chars):\n{text[:500]}\n---")
            fact_id = str(uuid.uuid4())
            facts.append(payload)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    if not facts:
        print("No facts to send. Exiting.")
        return
    try:
        verify = ca_cert_path if ca_cert_path else True
        for i, fact in enumerate(facts, 1):
            print(f"\nSending fact {i}/{len(facts)} to n8n webhook: {webhook_url}")
            r = requests.post(webhook_url, json=fact, timeout=10, verify=verify)
            print(f"Status: {r.status_code}")
            print(f"Response: {r.text}")
    except Exception as e:
        print(f"Error sending to webhook: {e}")

if __name__ == "__main__":
    # Example usage
    urls = [
        "https://example.com",
        "https://another-example.com"
    ]
    # Replace with your n8n webhook endpoint
    webhook_url = "https://your-n8n-instance/webhook/your-webhook-id"
    # Path to CA certificate (if needed)
    ca_cert_path = None  # e.g., r"/path/to/your-ca.pem"
    # Path to exclusions list (JSON)
    excluded_domains_path = os.path.join(os.path.dirname(__file__), "excluded_domains.json")
    scrape_and_send_to_n8n(urls, webhook_url, ca_cert_path, excluded_domains_path)
