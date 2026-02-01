import requests
import uuid
import os
import json
from datetime import datetime

"""
Manual Fact Entry Template - Schema Reference

This script submits facts to TeachHanna webhook using the unified Qdrant schema:

  text              (str, required) - The fact content
  source_type       (str, required) - "manual" | "web" | "chat_correction"
  confidence        (float)         - 0.0-1.0 quality score
  timestamp         (str)           - ISO-8601 date
  sourceUser        (str or null)   - Username if applicable
  url               (str or null)   - Source URL
  title             (str or null)   - Human-readable name
  tags              (array)         - Categories
  related_entities  (array)         - Linked concepts

Example:
  text: "PostgreSQL supports JSON querying"
  source_type: "manual"
  confidence: 0.95
  timestamp: "2026-02-01T12:00:00Z"
  sourceUser: "botmaster"
  url: "https://postgresql.org/docs"
  title: "PostgreSQL JSON"
  tags: ["database", "postgresql"]
  related_entities: ["PostgreSQL", "JSON"]

Configuration:
  1. Set webhook_url to your n8n TeachHanna endpoint
  2. Set ca_cert_path if using self-signed SSL
  3. Set excluded_domains_path to respect site exclusions

Run:
  python manual_fact_to_n8n.py
"""

def load_excluded_domains_json(filepath):
    """Load excluded domains from a JSON file with detailed info."""
    if not filepath or not os.path.exists(filepath):
        return set()
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            return set(entry['domain'].strip().lower() for entry in data if 'domain' in entry)
        except Exception as e:
            print(f"Error loading exclusions JSON: {e}")
            return set()

def manual_fact_entry_and_send(webhook_url, ca_cert_path=None, excluded_domains_path=None):
    """
    Prompt user to manually enter facts and send them to an n8n webhook for embedding and vector storage.
    Args:
        webhook_url (str): The n8n webhook endpoint.
        ca_cert_path (str): Path to CA certificate for SSL verification.
        excluded_domains_path (str): Path to exclusions list (JSON).
    """
    excluded_domains = load_excluded_domains_json(excluded_domains_path) if excluded_domains_path else set()
    while True:
        url = input("Source URL (or leave blank): ").strip()
        if url:
            domain = url.split('/')[2].lower() if '://' in url else url.lower()
            if any(domain == ex or domain.endswith('.' + ex) for ex in excluded_domains):
                print(f"Skipping excluded domain: {domain}")
                continue
        title = input("Title (optional): ").strip()
        text = input("Fact text (or 'quit' to exit): ").strip()
        if text.lower() == 'quit':
            print("Exiting.")
            break
        tags = input("Tags for this fact (comma-separated, optional): ").strip()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        source_type = input("Source type (default: manual): ").strip() or "manual"
        confidence = input("Confidence (0-1, default: 1.0): ").strip()
        try:
            confidence = float(confidence) if confidence else 1.0
        except Exception:
            confidence = 1.0
        related_entities = input("Related entities (comma-separated, optional): ").strip()
        related_list = [t.strip() for t in related_entities.split(",") if t.strip()] if related_entities else []
        fact_id = str(uuid.uuid4())
        payload = {
            "id": fact_id,
            "text": text,
            "url": url if url else None,
            "title": title if title else None,
            "source_type": source_type,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "sourceUser": None,
            "tags": tag_list,
            "related_entities": related_list
        }
        try:
            verify = ca_cert_path if ca_cert_path else True
            print(f"Sending payload to n8n webhook: {webhook_url}")
            r = requests.post(webhook_url, json=payload, timeout=10, verify=verify)
            print(f"Status: {r.status_code}")
            print(f"Response: {r.text}")
        except Exception as e:
            print(f"Error sending to webhook: {e}")

if __name__ == "__main__":
    # Replace with your n8n webhook endpoint
    webhook_url = "https://your-n8n-instance/webhook/your-webhook-id"
    # Path to CA certificate (if needed)
    ca_cert_path = None  # e.g., r"/path/to/your-ca.pem"
    # Path to exclusions list (JSON)
    excluded_domains_path = os.path.join(os.path.dirname(__file__), "excluded_domains.json")
    manual_fact_entry_and_send(webhook_url, ca_cert_path, excluded_domains_path)
