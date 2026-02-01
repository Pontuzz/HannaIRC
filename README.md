# HannaIRC

Advanced IRC bot with AI-powered conversation, knowledge retrieval, and dynamic learning capabilities.

## Overview

HannaIRC is the central component of the Hanna ecosystem—an intelligent IRC bot built on n8n that provides:

- **Real-time conversation** via GPT-4o-mini with context awareness
- **Command routing** for specialized functions (anime lookup, web search, calculations)
- **Event handling** (mentions, joins, parts, mode changes)
- **Conversation memory** via PostgreSQL
- **Dynamic learning** from corrections and user-provided facts

## Quick Start

### Installation

**Option 1: Docker (Recommended)**
```bash
cp docs/docker-compose.example.yml docker-compose.yml
# Edit docker-compose.yml with your configuration
docker-compose up -d
```
See [docs/DOCKER.md](docs/DOCKER.md) for detailed deployment instructions.

**Option 2: Manual Setup**
👉 See [docs/SETUP.md](docs/SETUP.md) for manual installation and configuration.

## Features

### Commands
- `!a <anime>` - Search anime database (Shoko Server + AniDB)
- `!w <query>` - Web search results
- `!c <expression>` - Calculator

### Event Handling
- **Mentions** - Responds to @bot mentions (filters bot-to-bot interactions)
- **Direct Messages** - Authenticated botmaster commands
- **Logging** - Tracks joins, parts, mode changes

### Knowledge System
- Vector-based retrieval from Qdrant (1536-dim embeddings)
- Automatic embedding via text-embedding-ada-002
- Conversation memory in PostgreSQL
- Correction learning from HannaLearns workflow

## How It Works

HannaIRC operates through three complementary n8n workflows that work together to provide real-time conversation and continuous learning:

1. **HannaIRC** (Live Interaction) - Real-time IRC bot responding to mentions and commands
2. **HannaLearns** (Auto Learning) - Daily job that extracts facts from chat corrections
3. **TeachHanna** (Manual Entry) - Webhook for direct fact submission

**Data Pipeline:**
```
docs/scrapers/
├── scrape_to_n8n.py      ┐
└── addfact.py            ├─→ TeachHanna ─────────────┐
                          │                           │
                          └─→ Qdrant Knowledge Base ←─┤
                                      ↑              │
                                      │              │
                              HannaLearns (daily) ───┘
                              Extracts chat corrections
                                      ↓
                              HannaIRC (live)
                              Queries knowledge & responds
```

## Architecture

### System Design

```
┌─────────────────┐
│  IRC Bot (n8n)  │
│   HannaBot      │
└────────┬────────┘
         │ (IRC events: privmsg, mention, mode, etc.)
         ▼
┌───────────────────────────────────────────┐
│  HannaIRC Workflow (n8n)                  │
│  ├─ Command Detection & Routing           │
│  ├─ Event Type Switching                  │
│  ├─ Auth & Permission Checks              │
│  └─ Response Generation                   │
└────┬──────────────────────────┬────┬──────┘
     │                          │    │
     ▼                          ▼    ▼
┌─────────────┐  ┌──────────────┐  ┌────────────────┐
│  Mini Hanna │  │ PostgreSQL   │  │ Qdrant Vector  │
│ (GPT-4o min)│  │ Chat History │  │ Database       │
└─────────────┘  └──────────────┘  └────────────────┘
     │
     ▼
 IRC Output
```

### Understanding the Workflows

For in-depth architecture documentation including data schemas, workflow connections, and event handling:
→ See [docs/WORKFLOWS.md](docs/WORKFLOWS.md)

## Configuration & Deployment

### Requirements & Infrastructure

**Services:**
- n8n instance with IRC bot integration
- PostgreSQL database for chat history
- Qdrant vector database for knowledge base
- Nginx reverse proxy (optional but recommended for production)

**API Keys & Credentials:**
- `OPENAI_API_KEY` - For GPT-4o-mini and embeddings
- `SERPAPI_KEY` - For web search
- `IRC_BOT_TOKEN` - For IRC bot authentication
- `POSTGRES_*` - Database connection details
- `QDRANT_API_KEY` - Vector database credentials

### Deployment Options

**Production with Docker Compose** (Recommended):
1. Copy template: `cp docs/docker-compose.example.yml docker-compose.yml`
2. Edit with your credentials and domain
3. Set up SSL certificates in `./certs/`
4. Start services: `docker-compose up -d`

→ See [docs/DOCKER.md](docs/DOCKER.md) for complete deployment guide

**Manual Installation:**
1. Install n8n, PostgreSQL, Qdrant separately
2. Configure IRC bot trigger in n8n
3. Import workflow JSONs from `docs/examples/`
4. Set credentials in n8n UI
5. Initialize knowledge base using `docs/scrapers/` tools

→ See [docs/SETUP.md](docs/SETUP.md) for manual setup instructions

## File Structure

```
HannaIRC/
├── docs/                       # Documentation & templates
│   ├── SETUP.md                # Installation & configuration guide
│   ├── WORKFLOWS.md            # Detailed workflow architecture & data schema
│   ├── DOCKER.md               # Docker deployment guide
│   ├── docker-compose.example.yml  # Production Docker Compose template
│   ├── nginx.conf.example      # Nginx reverse proxy template
│   ├── examples/               # n8n workflow JSON templates
│   │   ├── HannaIRC-workflow.json
│   │   ├── HannaLearns-workflow.json
│   │   └── TeachHanna-workflow.json
│   └── scrapers/               # Data ingestion tools & templates
│       ├── scrape_to_n8n.py    # Web scraper tool (template)
│       ├── addfact.py          # Interactive fact entry (template)
│       ├── manual_fact_to_n8n.py # Manual fact submission (template)
│       ├── anime_lookup.py     # Anime database lookup (template)
│       └── excluded_domains.json
├── index.html                  # Bot info page (served at botinfo.hivenet.dev)
├── LICENSE, PRIVACY.md, SECURITY.md
└── README.md                   # This file
```

**⚠️ Note**: Root-level JSON files (workflows) and scripts with credentials are production-only and excluded from version control.

## Development & Customization

### Adding Commands

To add a new command to the bot:

1. Update the Command Detector regex pattern
2. Create a new Switch branch in the Commands node
3. Implement a preparation node (e.g., "Prepare Query")
4. Connect to the Mini Hanna agent
5. Test with IRC trigger

### Adding Knowledge Sources

Seed the knowledge base using these tools:

```bash
# Interactive fact addition (step-by-step prompts)
python docs/scrapers/addfact.py

# Batch web scraping
python docs/scrapers/scrape_to_n8n.py

# Query anime database
python docs/scrapers/anime_lookup.py
```

Or trigger automatic learning from chat corrections via the HannaLearns workflow (runs daily).

### Modifying Workflows

Edit workflow JSONs in n8n UI to:
- Change LLM model parameters (temperature, max tokens)
- Modify command patterns and responses
- Adjust response constraints (length, format, tone)
- Add new event handlers or triggers
- Fine-tune knowledge retrieval thresholds

## Monitoring & Logging

### Production Monitoring

- **n8n Logs**: View execution history and workflow runs in n8n UI
- **Chat History**: Stored in PostgreSQL for analysis and learning
- **Event Logs**: Track IRC connections, messages, and bot interactions
- **Server Logs**: Monitor nginx access and error logs for deployment issues

### Debugging

```bash
# View n8n logs
docker-compose logs -f n8n

# Check database connectivity
docker-compose exec postgres psql -U n8n -d n8n

# Test Qdrant connectivity
curl https://your-domain/qdrant/collections

# Check bot health
curl https://your-domain/api/hanna-bot/health
```

## Privacy & Security

Your privacy and security are important. For detailed information:

- **Privacy**: See [PRIVACY.md](PRIVACY.md)
- **Security**: See [SECURITY.md](SECURITY.md)

### Key Principles

- No user data stored beyond conversation context necessary for operation
- Authentication via messageTags.account (IRC account field)
- Botmaster-only access to direct messages
- Credentials excluded from version control
- Respectful scraping with opt-out mechanisms

## Respectful Scraping

This tool respects site owners and their wishes regarding data collection:

- Respects exclusion list in `docs/scrapers/excluded_domains.json`
- Uses descriptive User-Agent: `HannaWebScraper/1.0 (+https://botinfo.hivenet.dev/)`
- Site owners can request exclusion via [botinfo.hivenet.dev](https://botinfo.hivenet.dev/) or GitHub issues

## Contributing

To contribute improvements, fixes, or new features:

1. Test changes in n8n UI first
2. Document any architecture modifications
3. If contributing examples: anonymize credentials (use placeholders)
4. Keep root workflow files production-ready
5. Update relevant documentation

## Acknowledgments

HannaIRC is built upon the foundation of the original [Hanna project](https://github.com/h4ks-com/hanna). This fork extends the concept with:

- IRC bot integration
- n8n workflow orchestration
- Vector database (Qdrant) for semantic search
- Automatic learning from chat corrections
- Community-driven knowledge base capabilities

## License

See [LICENSE](LICENSE) - MIT License


