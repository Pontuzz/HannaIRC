# Setup & Configuration Guide

## Prerequisites

- Python 3.8+
- Required libraries: `pip install requests beautifulsoup4`
- SSL certificate (if using HTTPS with custom CA)
- n8n webhook URL and API credentials

## Installation

1. **Copy template scripts to your working directory:**
   ```bash
   cp docs/scrapers/scrape_to_n8n.py ./scrape_to_n8n.py
   cp docs/scrapers/manual_fact_to_n8n.py ./manual_fact_to_n8n.py
   cp docs/scrapers/excluded_domains.json ./excluded_domains.json
   ```

2. **Edit with your credentials:**
   ```python
   # In scrape_to_n8n.py and manual_fact_to_n8n.py
   webhook_url = "https://your-n8n-instance/webhook/your-webhook-id"
   ca_cert_path = r"path/to/your-ca.pem"  # if needed
   ```

3. **Run:**
   ```bash
   python scrape_to_n8n.py
   ```

## Excluding Domains

Respectful web scraping means honoring site owner requests. This tool supports domain exclusions.

### How It Works

1. `docs/scrapers/excluded_domains.json` contains domains to skip during scraping
2. Copy to your working directory (step 1 above does this)
3. Both `scrape_to_n8n.py` and `manual_fact_to_n8n.py` automatically load and respect this list
4. The scraper checks each URL against excluded domains before processing

### File Format

```json
[
  {"domain": "example.com"},
  {"domain": "spam-site.org"},
  {"domain": "private-company.net"}
]
```

### Adding Exclusions

Edit your local `excluded_domains.json` to add domains you should not scrape:

```bash
# Manual: Open excluded_domains.json and add entries
# Or programmatically:
python -c "import json; data = json.load(open('excluded_domains.json')); data.append({'domain': 'newsite.com'}); json.dump(data, open('excluded_domains.json', 'w'), indent=2)"
```

### Contributing Exclusions Back

If you maintain a site and want to be excluded globally:
- File an issue on [GitHub](https://github.com/Pontuzz/HannaIRC)
- Contact via [botinfo.hivenet.dev](https://botinfo.hivenet.dev/)
- Domains will be added to `docs/scrapers/excluded_domains.json` for all users

## Scripts

### `scrape_to_n8n.py`

Scrapes websites and sends content to n8n for embedding and knowledge base injection.

**Features:**
- Multi-URL batch processing
- Automatic domain exclusion checking
- Custom tags and related entities
- Unified Qdrant schema compliance

**Usage:**
```bash
python scrape_to_n8n.py

# When prompted:
# Tags for this batch (comma-separated, optional): anime, media
# Related entities for this batch (comma-separated, optional): Shoko, Anime
```

**How it works:**
1. Requests list of URLs to scrape
2. Checks each domain against `excluded_domains.json`
3. Extracts page text and title
4. Prompts for tags and related entities
5. Sends unified schema payload to n8n webhook for each URL

### `manual_fact_to_n8n.py`

Interactive CLI for manually entering facts into the knowledge base.

**Features:**
- Interactive prompts for all schema fields
- Domain exclusion checking
- Custom confidence levels (0-1)
- User attribution support

**Usage:**
```bash
python manual_fact_to_n8n.py

# When prompted, enter:
# Source URL (or leave blank): https://example.com
# Title (optional): Example Fact Title
# Fact text (or 'quit' to exit): This is a useful fact...
# Tags for this fact (comma-separated, optional): category, tag
# Source type (default: manual): manual
# Confidence (0-1, default: 1.0): 0.95
# Related entities (comma-separated, optional): entity1, entity2
```

Repeat to add multiple facts in one session.

## Schema Reference

All ingestion methods produce this unified schema for storage in Qdrant:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | auto | UUID, auto-generated |
| `text` | string | yes | Main fact content |
| `source_type` | string | yes | "web", "manual", or "chat_correction" |
| `confidence` | number | yes | 0-1 scale; higher = more trustworthy |
| `timestamp` | string | yes | ISO 8601 UTC format |
| `sourceUser` | string | no | Username or null |
| `url` | string | no | Source URL or null |
| `title` | string | no | Human-readable title |
| `tags` | array | no | Categories (e.g., `["anime", "media"]`) |
| `related_entities` | array | no | Related topics (e.g., `["Shoko", "Anime"]`) |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **SSL Certificate Error** | Pass your CA cert path: `ca_cert_path = r"/path/to/ca.pem"` |
| **Webhook Returns 404** | Verify n8n endpoint exists and webhook is active |
| **Webhook Returns 401/403** | Check API credentials and webhook URL configuration |
| **Rate Limiting / Timeouts** | Add `time.sleep(1)` between requests; increase timeout |
| **Domain Not Excluded** | Verify format in `excluded_domains.json`: exactly `{"domain": "example.com"}` |
| **Duplicate Facts Appearing** | Check timestamp—embeddings are unique per timestamp, so duplicates won't collide |

## Production Deployment

**Security:**
- Production scripts in your working directory should NOT be committed to git
- Template scripts in `docs/scrapers/` are public and credential-free
- Your `.gitignore` automatically excludes root-level scripts
- Never share your n8n webhook URL or API credentials

**Best Practices:**
- Use environment variables for sensitive config: `os.getenv('N8N_WEBHOOK_URL')`
- Rotate API keys regularly
- Monitor webhook response codes for errors
- Log all scraping activity for auditing

## Privacy & Respect

This tool respects site owner wishes and user privacy:
- Check `excluded_domains.json` before adding new URLs
- Honor `robots.txt` guidelines
- Use descriptive User-Agent: `HannaWebScraper/1.0 (+https://botinfo.hivenet.dev/)`
- See [PRIVACY.md](../PRIVACY.md) and [SECURITY.md](../SECURITY.md) for full policies
- Site owners can request exclusion via GitHub or botinfo.hivenet.dev
