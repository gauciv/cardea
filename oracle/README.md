# Oracle - Cloud Layer
> AI-powered agentic threat analysis and management

## ⚡ What's New: AI-Powered Agentic Analytics

The Oracle backend now features **AI-driven agentic reasoning** using Azure OpenAI:

### 🤖 Key Features
1. **Intent Analysis**: AI identifies attack intent and Cyber Kill Chain stage
2. **RAG-Enhanced Context**: Retrieves similar historical threats using Azure AI Search
3. **Human-Readable Recommendations**: Business-owner friendly explanations (What Happened, Why It Matters, What To Do)
4. **Adaptive Thresholds**: AI recommends KitNET sensitivity adjustments based on threat patterns
5. **Graceful Fallback**: Deterministic algorithms when AI unavailable

See [AI Analytics Documentation](../docs/agentic-ai-analytics.md) for full details.

## Overview
The Oracle module provides cloud-based threat intelligence through:
- **FastAPI**: RESTful API backend
- **Azure OpenAI**: GPT-4o agentic reasoning engine
- **Azure AI Search**: Vector-based semantic search for historical context (RAG)
- **Advanced Analytics**: AI-powered threat scoring and correlation
- **PostgreSQL**: Time-series alert storage

## Architecture
```
Sentry Alerts → FastAPI → Azure AI → RAG (Azure Search) → Dashboard
                      ↓
                   Supabase
```

## Quick Start

### 1. Configure Azure OpenAI & Search
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Azure credentials
# AZURE_OPENAI_API_KEY=your-key
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
# AZURE_SEARCH_KEY=your-search-key
# AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
```

### 2. Initialize Search Index
```bash
# Create the Azure AI Search index schema
python scripts/init_search_index.py
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start Oracle Service
```bash
# Development mode
python src/main.py

# With Docker
docker-compose up
```

### 5. Test AI Features
```bash
# Run AI analytics tests
pytest tests/test_analytics_ai.py -v

# Run Search integration tests
pytest tests/test_search_service.py -v

# Test health endpoint
curl http://localhost:8000/health
```

## Components
- `src/analytics.py` - **🤖 AI-powered threat analysis** (agentic reasoning + RAG)
- `src/search_service.py` - **🔍 Azure AI Search integration**
- `src/oracle_service.py` - FastAPI application and API routes
- `src/database.py` - PostgreSQL models and connections
- `src/models.py` - Pydantic request/response schemas
- `src/config.py` - Environment-based configuration

## API Endpoints

### Core Endpoints
- `POST /api/v1/alerts` - Receive alerts from Sentry
- `POST /api/v1/analyze/threats` - AI threat analysis
- `GET /api/v1/analytics` - Dashboard analytics
- `GET /health` - Service health check

### Example: AI Threat Analysis
```bash
curl -X POST http://localhost:8000/api/v1/analyze/threats \
  -H "Content-Type: application/json" \
  -d '{
    "time_window": 3600,
    "threat_types": ["data_exfiltration"],
    "include_correlations": true
  }'
```

**Response includes:**
- AI-generated threat scores with Cyber Kill Chain stages
- Human-readable recommendations (What/Why/How)
- Adaptive threshold recommendations for Sentry

## Configuration

### Environment Variables
```bash
# AI Configuration (Required for agentic features)
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AI_ENABLED=true

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/cardea

# Service
PORT=8000
LOG_LEVEL=INFO
```

See `.env.example` for full configuration options.

## Cost Optimization

**AI Token Usage** (per alert):
- Threat scoring: ~300-500 tokens
- Recommendations: ~800-1200 tokens

**Monthly estimates** (10 alerts/hour):
- **gpt-4o-mini**: $10-15/month (recommended for dev)
- **gpt-4o**: $300-400/month (best quality)
- **gpt-35-turbo**: $30-50/month (balanced)

**Fallback**: System uses deterministic algorithms if AI unavailable or quota exceeded.

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run AI-specific tests
pytest tests/test_analytics_ai.py -v

# Run Search integration tests
pytest tests/test_search_service.py -v

# Run with coverage
pytest --cov=src tests/
```

## Documentation
- [AI Analytics Guide](../docs/agentic-ai-analytics.md) - Comprehensive AI features documentation
- [Development Guide](../docs/development.md) - Development workflow
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)

## Troubleshooting

### AI Features Not Working
```bash
# Check AI configuration
python -c "from config import settings; print(f'AI Enabled: {settings.AI_ENABLED}')"

# Verify Azure credentials
curl -X GET "${AZURE_OPENAI_ENDPOINT}/openai/deployments?api-version=2024-08-01-preview" \
  -H "api-key: ${AZURE_OPENAI_API_KEY}"
```

### Fallback to Deterministic Mode
If you see: `⚠️ Azure OpenAI initialization failed`
- Check `AZURE_OPENAI_API_KEY` is set correctly
- Verify endpoint URL format
- Ensure deployment name matches your Azure resource
- System will continue working with deterministic algorithms

## Components
- `api/` - FastAPI application and routes
- `ai/` - Azure AI integration and RAG
- `database/` - Supabase schema and models
- `services/` - Business logic and threat analysis

See [Oracle Documentation](../docs/oracle/) for detailed information.