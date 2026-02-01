# N8N Workflow Examples

This folder contains examples of the n8n workflows that power Hanna's knowledge system.

**For detailed workflow architecture, see [WORKFLOWS.md](../WORKFLOWS.md)**

## Workflows

### 1. TeachHanna - Manual Fact Submission

**Purpose:** Receives facts from external sources via webhook, validates schema, generates embeddings, and stores in Qdrant.

**When it runs:** On-demand (HTTP POST webhook trigger)

**Trigger:** Webhook POST to `https://your-n8n/webhook/{webhook-id}`

**Input Schema:**
```json
{
  "body": {
    "text": "Fact content",
    "source_type": "manual",
    "confidence": 0.95,
    "timestamp": "2026-02-01T12:00:00Z",
    "sourceUser": "username",
  "url": "https://example.com",
  "title": "Example",
  "tags": ["tag1"],
  "related_entities": ["entity1"]
}
```

**Output:** Fact embedded and stored in Qdrant, queryable by Hanna

**Key nodes:**
- Webhook receiver (HTTP POST endpoint)
- Schema field extractor (maps incoming JSON)
- OpenAI embeddings (text-embedding-ada-002)
- Qdrant vector store (insert/upsert)

**See:** [TeachHanna-workflow.json](TeachHanna-workflow.json)

---

### HannaLearns - Automatic Learning from Chat

**Purpose:** Runs automatically on a schedule (default: 2 AM UTC daily). Reads recent chat history from PostgreSQL, uses GPT-4o-mini to identify corrections and facts from human messages only, and injects high-confidence items into knowledge base.

**When it runs:** Daily on schedule (configurable)

**Trigger:** Schedule Trigger (cron)

**Data Flow:**
1. Schedule triggers → Read last 100 messages from `n8n_chat_histories` (PostgreSQL)
2. Extract Message (Code node) → Pulls just message type and content from LangChain message object
3. Is Human? (Filter) → Skips AI responses, processes only human messages
4. Extract Corrections (LM Agent) → GPT-4o-mini analyzes content for facts/corrections
5. Has Facts? (Filter) → Stops empty results from propagating
6. Parse Facts (Code node) → Extracts JSON array from agent response wrapper
7. Format Facts (Set node) → Maps to unified schema (source_type="chat_correction")
8. Qdrant Vector Store → Embeds and stores with text-embedding-ada-002

**Input:** Raw PostgreSQL rows with LangChain message objects

**Output:** Extracted facts embedded and stored in Qdrant, tagged as chat_correction source

**Key Configuration:**
- PostgreSQL connection to n8n_chat_histories (auto-created by memoryPostgresChat)
- GPT-4o-mini model for fact extraction
- Minimum confidence threshold: 0.7
- Collection: hannabot_knowledge

**See:** [HannaLearns-workflow.json](HannaLearns-workflow.json)

**Process:**
1. Read last 50 messages from PostgreSQL chat history
2. LLM analyzes for: corrections, facts, learning value
3. Filters items with confidence > 0.7
4. Maps to unified schema
5. Generates embeddings and stores in Qdrant

**Output:** Chat-derived facts automatically available to Hanna for future conversations

**Key nodes:**
- Schedule trigger (cron-like, daily)
- PostgreSQL reader (queries chat_histories table)
- LLM agent (GPT-4o-mini for extraction)
- Fact formatter (unified schema mapping)
- Qdrant vector store (upsert)

**Configuration:**
- `session_key`: Your chat session identifier (e.g., `"hanna_global_v2"`)
- `timezone`: Set to your timezone (e.g., `"Europe/Stockholm"`)
- `triggerAtHour`: Hour to run daily (24-hour format)

**See:** [HannaLearns-workflow.json](HannaLearns-workflow.json)

---

### 3. HannaIRC - Live Bot Response Generation

**Purpose:** Primary IRC chat workflow. Receives IRC events, maintains conversation memory, and uses Qdrant knowledge retrieval + LLM agent to generate real-time responses.

**When it runs:** On every IRC event (mention, privmsg, etc.)

**Trigger:** IRC Event webhook (from Hanna Bot)

**Data Flow:**
1. IRC Event (webhook) → Receives message/mention from IRC
2. IRC SET (Set node) → Normalizes event data
3. Channel Mention Check → Routes private messages and mentions
4. Switch2 (event type router) → Handles privmsg, mention, mode, etc.
5. Chat Memory (Postgres) → Maintains conversation history for context
6. Mini Hanna (LM Agent) → GPT-4o-mini generates response using:
   - Conversation history (Chat Memory ai_memory connection)
   - Knowledge retrieval (Qdrant Vector Retrieve as ai_tool)
   - Calculators, SerpAPI, Shoko Search as ai_tools
7. Edit Fields (Set) → Formats bot response
8. Hanna Bot (TCP output) → Sends response back to IRC

**Output:** Live IRC message response

**Tools Available to Agent:**
- **Qdrant Vector Retrieve** - Search knowledge base for facts (hannabot_knowledge collection)
- **Calculator** - Math operations
- **SerpAPI** - Web search
- **Shoko Search** - Anime metadata from local Shoko Server
- **Message**, **SendNotice**, **Join**, **RawCMD** - IRC operations

**Key Configuration:**
- `sessionIdType`: "customKey" for unified conversation tracking
- `sessionKey`: "hanna_global_v2" (shared across all users)
- `timezone`: Your timezone
- IRC Bot auth token and credentials

**Note:** This is the primary workflow where Hanna learns from interactions and applies knowledge

**Reference:** HannaIRC Reworked.json in main workflows (note: public name is "HannaIRC")

---

## Unified Schema (All Workflows)

Every fact stored in Qdrant uses this schema:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | string | yes | Main content |
| `source_type` | string | yes | `web`, `manual`, `chat_correction`, `anidb_metadata` |
| `confidence` | number | yes | 0-1 scale |
| `timestamp` | string | yes | ISO 8601 UTC |
| `sourceUser` | string | no | Username or null |
| `url` | string | no | Source URL or null |
| `title` | string | no | Human-readable title |
| `tags` | array | no | Categories |
| `related_entities` | array | no | Related topics |

---

## How They Work Together

```
scrape_to_n8n.py   ─┐
manual_fact_to_n8n.py ├─→ TeachHanna Webhook ─→ Qdrant Vector Store
anime_lookup.py     ┤                              ↑
                    ┘                              │
                                            HannaLearns (daily)
                                          Extracts from chat history
```

**Result:** Unified knowledge base combining:
- Web scraping results
- Manual fact entry
- Anime database metadata
- Automatic learning from chat corrections

All queryable by Hanna for real-time responses.

---

## Integration Notes

- **Webhook URL:** Configure in your ingestion scripts (TeachHanna path)
- **Qdrant collection:** Ensure it exists with vector size 1536 (for ada-002)
- **PostgreSQL access:** Required for HannaLearns (n8n database)
- **API Keys:** OpenAI (embeddings + LLM), Qdrant
- **Timezone:** Set in HannaLearns for correct schedule
