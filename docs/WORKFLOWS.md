# Hanna Workflow Architecture

This document describes the three core n8n workflows that power the Hanna knowledge system.

## Overview

| Workflow | Purpose | Trigger | Input | Output |
|----------|---------|---------|-------|--------|
| **HannaIRC Reworked** | Real-time IRC bot & knowledge retrieval | IRC events | User messages | Chat responses + knowledge retrieval |
| **HannaLearns** | Auto-extract facts from IRC history | Daily (2 AM) | PostgreSQL chat history | Facts → Qdrant |
| **TeachHanna** | Manual fact submission | Webhook POST | JSON schema object | Stored in Qdrant |

## Unified Data Schema

All three workflows share a unified schema for Qdrant storage:

```json
{
  "text": "string - the fact or knowledge item",
  "source_type": "enum - 'chat_correction' | 'manual' | 'web'",
  "confidence": "number - 0.0 to 1.0",
  "timestamp": "string - ISO-8601 format",
  "sourceUser": "string or null - username if applicable",
  "url": "string or null - source URL if applicable",
  "title": "string or null - human-readable title",
  "tags": "array of strings - categorization",
  "related_entities": "array of strings - linked concepts"
}
```

### Field Definitions

- **text**: The core fact or knowledge item (required, searchable)
- **source_type**: Indicates origin (chat_correction, manual submission, or web scraping)
- **confidence**: Quality score (0.0-1.0); typically 0.7+ for storage
- **timestamp**: When the fact was added to knowledge base
- **sourceUser**: IRC username or bot name that contributed this fact
- **url**: Original source URL (web scraping or citations)
- **title**: Short human-readable name (optional)
- **tags**: Categories like "anime", "technology", "correction", etc.
- **related_entities**: Linked concepts ("Attack on Titan", "PostgreSQL", etc.)

## Workflow Details

### 1. HannaIRC Reworked (Primary - Real-Time)

**Location**: `HannaIRC Reworked.json`

**What it does**:
- Listens for IRC events (messages, mentions, etc.)
- Retrieves relevant knowledge from Qdrant when needed
- Uses GPT-4o-mini for responses
- Stores conversation history in PostgreSQL for learning

**Key Features**:
- Real-time mention detection and response
- Qdrant vector retrieval as LangChain tool
- PostgreSQL conversation memory
- Multiple IRC tools (SerpAPI, Calculator, Shoko Search)

**Qdrant Connection**: `retrieve-as-tool` mode
- Uses embeddings to find similar facts when responding
- No data insertion (read-only for live retrieval)

### 2. HannaLearns (Daily Learning)

**Location**: `HannaLearns.json`

**What it does**:
- Runs daily at 2 AM UTC
- Reads last 100 chat messages from PostgreSQL
- Analyzes human messages for educational facts
- Extracts facts using GPT-4o-mini agent
- Stores results in Qdrant with embeddings

**Data Flow**:
```
Schedule (2 AM)
  ↓
PostgreSQL: Read Chat History (100 most recent)
  ↓
Extract Message (get content from LangChain structure)
  ↓
Is Human? (filter for user messages only, skip AI)
  ↓
Extract Corrections (LLM analyzes for facts)
  ↓
Has Facts? (filter empty results)
  ↓
Parse Facts (extract JSON from agent response)
  ↓
Format Facts (map to unified schema)
  ↓
Qdrant Vector Store (insert with embeddings)
```

**Key Features**:
- Pre-filtering to minimize LLM processing (human messages only)
- Confidence threshold (>0.7) enforced in extraction prompt
- Batch processing (runOnceForAllItems)
- Automatic timestamp and metadata

**Qdrant Connection**: `insert` mode
- Three inputs: main (data flow), ai_document (Default Data Loader), ai_embedding (embeddings)

### 3. TeachHanna (Manual Submission)

**Location**: `TeachHanna.json`

**What it does**:
- Receives facts via webhook POST
- Maps request fields to unified schema
- Validates schema compliance
- Stores in Qdrant with embeddings

**Request Format**:
```json
POST /webhook/af59f0fd-2ae4-4ddf-af22-2a8d450859f3

{
  "body": {
    "text": "Fact content",
    "source_type": "manual",
    "confidence": 0.95,
    "timestamp": "2026-02-01T12:00:00Z",
    "sourceUser": "username",
    "url": null,
    "title": "Optional title",
    "tags": ["category"],
    "related_entities": ["Entity"]
  }
}
```

**Data Flow**:
```
Webhook (POST)
  ↓
Set: Map to schema (fact node)
  ↓
Qdrant Vector Store (insert with embeddings)
```

**Key Features**:
- Lightweight webhook-based ingestion
- Direct schema mapping (no transformation needed)
- Immediate Qdrant storage
- Perfect for programmatic submission

---

## Qdrant Connection Patterns

All three workflows connect to Qdrant differently based on their purpose:

### HannaIRC Reworked (Read-Only Retrieval)
```
Qdrant Vector Retrieve (mode: retrieve-as-tool)
├── ai_embedding ← Embeddings OpenAI
└── [used as LangChain tool for agent]
```

### HannaLearns & TeachHanna (Insert Mode)
```
Qdrant Vector Store (mode: insert)
├── main ← Formatted facts (Set node)
├── ai_document ← Default Data Loader
└── ai_embedding ← Embeddings OpenAI
```

**Important**: Default Data Loader is exclusively a *tool connector* (ai_document slot), never part of the main data flow.

---

## Credentials & Configuration

All workflows share the following environment variables (configure in n8n):
- **OpenAI**: Environment variable `OPENAI_CREDENTIAL` - LM Chat (gpt-4o-mini) + Embeddings (text-embedding-ada-002)
- **PostgreSQL**: Environment variable `POSTGRES_CREDENTIAL` - n8n_chat_histories table
- **Qdrant**: Environment variable `QDRANT_CREDENTIAL` - Collection: `hannabot_knowledge`

⚠️ **Never commit credentials to the repository. Use n8n's credential management system.**

---

## Best Practices

### Adding Facts via TeachHanna
```python
import requests
import json
from datetime import datetime

webhook_url = "https://your-n8n-instance/webhook/af59f0fd-2ae4-4ddf-af22-2a8d450859f3"

fact = {
    "body": {
        "text": "Attack on Titan Season 4 has 16 episodes",
        "source_type": "manual",
        "confidence": 0.95,
        "timestamp": datetime.now().isoformat(),
        "sourceUser": "botmaster",
        "url": None,
        "title": "AoT S4 Episode Count",
        "tags": ["anime", "metadata"],
        "related_entities": ["Attack on Titan", "Season 4"]
    }
}

response = requests.post(webhook_url, json=fact)
print(f"Status: {response.status_code}")
```

### HannaLearns Trigger
- Runs automatically at 2 AM UTC daily
- Processes up to 100 recent messages
- Only extracts facts with confidence > 0.7
- Filters out greetings, jokes, casual chat

### Retrieving Facts
- HannaIRC Reworked queries Qdrant based on conversation context
- Embeddings-based similarity search finds relevant facts
- Results fed to GPT-4o-mini for context-aware responses

---

## Monitoring & Troubleshooting

### Common Issues

**HannaLearns not extracting facts**:
1. Verify PostgreSQL has recent messages (n8n_chat_histories table)
2. Check Is Human? filter is matching actual message.type values
3. Review Extract Corrections prompt for confidence threshold

**TeachHanna webhook not storing**:
1. Verify schema matches exactly (9 required fields)
2. Check Qdrant connection has all three input types
3. Ensure credential IDs are correct

**Qdrant retrieval returning empty**:
1. Verify embeddings model matches: text-embedding-ada-002
2. Check collection exists: `hannabot_knowledge`
3. Ensure facts were actually inserted (check n8n execution logs)

---

## Future Enhancements

- [ ] Fact versioning / updates
- [ ] Confidence scoring refinement
- [ ] Multi-language support
- [ ] Fact expiration / TTL
- [ ] Citation tracking
- [ ] Collaborative tagging interface
