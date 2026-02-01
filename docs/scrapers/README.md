# Scrapers

Tools for ingesting data into Hanna's knowledge base (Qdrant vector database).

## Scripts

### `addfact.py`
Interactively add facts to the knowledge base with optional source URLs.

```bash
python addfact.py
```

Configure the n8n webhook URL in the script before running.

### `scrape_to_n8n.py`
Scrape webpages and send their content for embedding and storage.

```bash
python scrape_to_n8n.py
```

Supports batch scraping with tags, confidence scores, and entity relationships.

## Setup

1. Install dependencies:
   ```bash
   pip install requests beautifulsoup4
   ```

2. Update webhook URLs to point to your n8n instance

3. Run scripts as needed to ingest data

## Output

Both scripts send JSON payloads to n8n webhooks, which handle:
- Text embedding (using OpenAI embeddings)
- Vector storage in Qdrant
- Metadata preservation (tags, source URLs, timestamps)
