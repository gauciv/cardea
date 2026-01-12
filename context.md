# Project Cardea - Comprehensive Context Documentation

> **Last Updated:** January 12, 2026  
> **License:** MIT License  
> **Repository:** gauciv/cardea  
> **Branch:** main

---

## Recent Changes (January 12, 2026)

### AI Persona & Action Center Overhaul
- **Grouped Alerts**: Oracle now groups related alerts by type into ONE actionable item
- **Simplified Flow**: AI shows one problem at a time, waits for user decision
- **Action Center Component**: New UI component with execution tracking
  - Shows grouped threat with source IP and event count
  - Two action buttons: "It's safe - ignore" or "Block [IP]"
  - Expandable dropdown showing execution steps
  - Visual feedback: pending → running → success/error
  - Auto-collapses and shows "Threat Resolved" on success

### Token Optimization
- **100% Deterministic Insights**: No AI tokens used for routine monitoring
- **5-minute Cache TTL**: Same situation won't regenerate
- **Cache key based on alert IDs**: Only regenerates when NEW alerts arrive

### Azure AI Search Integration
- **RAG-Enhanced Analysis**: Historical threat context for better recommendations
- **Auto-Index Creation**: Search index created on startup
- **Resolution Tracking**: User actions stored for future reference
- **Background Indexing**: High-severity alerts indexed asynchronously

### API Endpoints Added
- `DELETE /api/alerts/clear` - Clear all alerts (for demo/testing)
- `POST /api/actions/execute` - Execute user actions with safety checks
- `GET /api/actions/dismissed` - Get dismissed alerts and safe IPs

### Dashboard Components
- `ActionCenter.tsx` - Grouped threat display with execution tracking
- Simplified `AIPersona.tsx` - Just shows message, actions moved to ActionCenter
- Fixed timezone for greeting (uses local time +8)

### Environment Variables Required
```
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
AZURE_SEARCH_KEY=<your-admin-key>
```

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Sentry Layer (Edge)](#4-sentry-layer-edge)
5. [Oracle Layer (Cloud)](#5-oracle-layer-cloud)
6. [Dashboard Layer (UI)](#6-dashboard-layer-ui)
7. [Shared Libraries](#7-shared-libraries)
8. [Infrastructure](#8-infrastructure)
9. [Scripts & Automation](#9-scripts--automation)
10. [Configuration Details](#10-configuration-details)
11. [Technology Stack](#11-technology-stack)
12. [API Reference](#12-api-reference)
13. [Data Flow](#13-data-flow)
14. [Development Workflow](#14-development-workflow)
15. [Deployment](#15-deployment)

---

## 1. Project Overview

### 1.1 What is Cardea?

**Project Cardea** is a hybrid, agentic AI cybersecurity platform designed specifically for Small-to-Medium Enterprises (SMEs). The platform provides cost-effective 24/7 cybersecurity monitoring through a dual-layer architecture that combines edge computing with cloud-based AI analytics.

### 1.2 Naming Origin

Cardea is named after the Roman goddess of door hinges, thresholds, and handles - symbolizing protection at the entry points (network perimeter security).

### 1.3 Target Audience

- Small-to-Medium Enterprises (SMEs)
- Organizations requiring affordable cybersecurity monitoring
- Businesses without dedicated security operations centers (SOC)

### 1.4 Development Phases

| Phase | Component | Status | Description |
|-------|-----------|--------|-------------|
| Phase 1 | Project Foundation | ✅ Complete | Repository setup, architecture design |
| Phase 2 | Sentry Layer | ✅ Complete | Edge detection system fully functional |
| Phase 3 | Oracle Layer | 🚧 In Progress | Cloud AI analytics platform |
| Phase 4 | Dashboard | 📋 Planned | Web-based monitoring interface |

### 1.5 Core Value Proposition

- **Cost-Effective**: Designed for SME budgets
- **24/7 Monitoring**: Automated threat detection without human intervention
- **Hybrid Architecture**: Local edge processing + cloud AI intelligence
- **AI-Powered**: Uses Azure OpenAI GPT-4o for agentic threat reasoning
- **Cross-Platform**: Supports multiple Linux distributions and macOS

---

## 2. Architecture

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   CARDEA SENTRY     │────│   CARDEA ORACLE     │────│   WEB DASHBOARD     │
│   (Edge Layer)      │    │   (Cloud Layer)     │    │   (User Layer)      │
│      ✅ READY       │    │    🚧 PHASE 3       │    │    📋 PHASE 4       │
│                     │    │                     │    │                     │
│ • Zeek (Network)    │    │ • FastAPI Backend   │    │ • Vite + React 19   │
│ • Suricata (IDS)    │    │ • Azure OpenAI      │    │ • TypeScript        │
│ • KitNET (AI)       │    │ • Azure AI Search   │    │ • Shadcn/UI         │
│ • Bridge (API)      │    │ • PostgreSQL        │    │ • React Flow        │
│ • Redis (Cache)     │    │ • Redis             │    │ • TailwindCSS 4     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
        │                          │                          │
        └──────────────────────────┼──────────────────────────┘
                                   │
                           Docker Networks:
                           • sentry_shared_network
                           • oracle-network
```

### 2.2 Communication Flow

```
Network Traffic
      │
      ▼
┌─────────────────┐
│      Zeek       │──────┐
│ (Protocol Logs) │      │
└─────────────────┘      │
                         ▼
┌─────────────────┐   ┌─────────────────┐
│    Suricata     │──▶│     Bridge      │──▶ Oracle Cloud ──▶ Dashboard
│   (IDS Alerts)  │   │  (Orchestrator) │
└─────────────────┘   └─────────────────┘
                         ▲
┌─────────────────┐      │
│     KitNET      │──────┘
│  (ML Anomalies) │
└─────────────────┘
```

### 2.3 Network Architecture

| Network Name | Type | Purpose |
|--------------|------|---------|
| `sentry_shared_network` | Docker Bridge | Internal Sentry service communication |
| `oracle-network` | Docker Bridge | Oracle backend service communication |
| Host Network | Host Mode | Packet capture (Zeek, Suricata, KitNET) |

---

## 3. Project Structure

### 3.1 Root Directory Layout

```
cardea/
├── LICENSE                    # MIT License (2026)
├── Makefile                   # Main build automation
├── package.json               # Root workspace (PostCSS, Autoprefixer)
├── requirements.txt           # Python dependencies (all components)
├── README.md                  # Project documentation
├── context.md                 # This file
│
├── sentry/                    # ✅ Edge Layer - Network Monitoring
├── oracle/                    # 🚧 Cloud Layer - AI Analytics
├── dashboard/                 # 📋 Web Dashboard - User Interface
├── shared/                    # ✅ Common Utilities
├── infrastructure/            # Terraform & DevOps
└── scripts/                   # Automation Scripts
```

### 3.2 Detailed Directory Breakdown

#### Sentry Directory (`/sentry/`)
```
sentry/
├── docker-compose.yml         # Service orchestration
├── Makefile                   # Local build targets
├── README.md                  # Sentry documentation
│
├── bridge/                    # Orchestration Service
│   ├── Dockerfile             # Python 3.9-slim based
│   ├── requirements.txt       # FastAPI, uvicorn, pydantic, etc.
│   ├── entrypoint.sh          # Container startup
│   └── src/
│       ├── __init__.py
│       ├── main.py            # Entry point (uvicorn launcher)
│       ├── bridge_service.py  # FastAPI application (318 lines)
│       ├── alert_processor.py # Alert queue management
│       ├── oracle_client.py   # Oracle communication client
│       ├── sentry_status.py   # Service health monitoring
│       └── templates/
│           └── index.html     # Consumer-facing setup UI
│
├── services/
│   ├── zeek/                  # Network Analysis
│   │   ├── Dockerfile         # Ubuntu 22.04 + Zeek
│   │   ├── entrypoint.sh
│   │   ├── config/
│   │   │   ├── node.cfg       # Cluster configuration
│   │   │   └── zeek.cfg       # Zeek scripts/settings
│   │   └── scripts/
│   │       └── health_check.py
│   │
│   ├── suricata/              # Intrusion Detection
│   │   ├── Dockerfile         # Ubuntu 22.04 + Suricata
│   │   ├── entrypoint.sh
│   │   ├── config/
│   │   │   └── suricata.yaml  # Detection rules & outputs
│   │   └── scripts/
│   │       ├── health_check.py
│   │       └── log_processor.py
│   │
│   └── kitnet/                # AI Anomaly Detection
│       ├── Dockerfile         # Python 3.9-slim
│       ├── requirements.txt   # numpy, scikit-learn, aiohttp
│       └── src/
│           ├── main.py        # Service entry point
│           ├── kitnet_detector.py  # KitNET ensemble autoencoder
│           ├── network_monitor.py  # Zeek log tailing
│           └── alert_manager.py    # Bridge communication
│
├── data/                      # Runtime data (gitignored)
│   ├── zeek/                  # Zeek connection logs
│   ├── suricata/              # EVE JSON alerts
│   ├── kitnet/                # ML model persistence
│   └── bridge/                # Bridge state
│
└── config/                    # Shared configuration
    └── bridge/                # Bridge config files
```

#### Oracle Directory (`/oracle/`)
```
oracle/
├── docker-compose.yml         # Oracle + PostgreSQL + Redis
├── Dockerfile                 # Python 3.11-slim
├── requirements.txt           # FastAPI, SQLAlchemy, OpenAI, Azure SDKs
├── README.md                  # Oracle documentation (192 lines)
│
├── src/
│   ├── main.py               # Application entry point
│   ├── oracle_service.py     # FastAPI routes + Redis safeguards
│   ├── analytics.py          # AI-powered threat analysis (978 lines)
│   ├── search_service.py     # Azure AI Search RAG integration
│   ├── database.py           # SQLAlchemy async models
│   ├── models.py             # Pydantic request/response schemas
│   ├── config.py             # Environment configuration
│   └── auth.py               # Authentication handlers
│
└── config/                   # Configuration files
    └── README.md
```

#### Dashboard Directory (`/dashboard/`)
```
dashboard/
├── package.json              # Vite + React 19 + TypeScript
├── vite.config.ts            # Vite configuration
├── tailwind.config.ts        # TailwindCSS 4 theming
├── tsconfig.json             # TypeScript configuration
├── tsconfig.app.json         # App-specific TS config
├── tsconfig.node.json        # Node-specific TS config
├── postcss.config.js         # PostCSS configuration
├── eslint.config.js          # ESLint flat config
├── components.json           # shadcn/ui configuration
├── index.html                # HTML entry point
├── README.md                 # Vite template docs
│
├── @/components/ui/          # shadcn/ui components (aliased)
│   ├── badge.tsx
│   ├── card.tsx
│   ├── scroll-area.tsx
│   └── table.tsx
│
├── public/                   # Static assets
│
└── src/
    ├── main.tsx              # React entry point
    ├── App.tsx               # Main application (164 lines)
    ├── App.css               # Application styles
    ├── index.css             # Global styles + CSS variables
    ├── types.ts              # TypeScript interfaces
    ├── assets/               # Static assets
    └── components/
        ├── LoginPage.tsx     # Authentication UI (259 lines)
        ├── NetworkMap.tsx    # React Flow network visualization
        └── ui/
            └── button.tsx    # UI button component
```

#### Shared Directory (`/shared/`)
```
shared/
├── __init__.py               # Python package marker
├── README.md                 # Shared library documentation
│
└── utils/
    ├── __init__.py
    ├── platform_detector.py   # OS/network/Docker detection (375 lines)
    ├── environment_configurator.py  # Dynamic env generation (309 lines)
    └── platform_cli.py        # CLI interface for platform tools
```

#### Infrastructure Directory (`/infrastructure/`)
```
infrastructure/
├── README.md                 # Infrastructure documentation
│
└── terraform/
    └── main.tf               # Azure resource definitions
```

#### Scripts Directory (`/scripts/`)
```
scripts/
├── setup-dev.sh              # Development environment setup (219 lines)
├── setup-platform.sh         # Platform-aware configuration (242 lines)
├── start-sentry.sh           # Sentry startup script (254 lines)
├── validate_runtime.py       # Runtime validation
├── validate-institutional.sh # Institutional validation
└── validate-sentry.sh        # Sentry validation
```

---

## 4. Sentry Layer (Edge)

### 4.1 Purpose

The Sentry layer is the "Reflex" of the system - a local edge detection system running on-premise that provides:
- Real-time network traffic monitoring
- Intrusion detection
- AI-based anomaly detection
- Alert aggregation and escalation to Oracle

### 4.2 Service Components

#### 4.2.1 Zeek (Network Analysis)

| Attribute | Value |
|-----------|-------|
| **Base Image** | Ubuntu 22.04 |
| **Package** | Zeek from OpenSUSE repository |
| **Function** | Passive network traffic monitoring |
| **Output** | JSON connection logs (`conn.log`) |
| **Network Mode** | Host (for packet capture) |
| **Port** | 47760/tcp |

**Configuration Files:**
- `node.cfg`: Cluster configuration (manager, logger, worker)
- `zeek.cfg`: Script loading and JSON output settings

**Key Features:**
- Real-time protocol analysis
- Metadata extraction
- JSON logging with ISO8601 timestamps
- Cluster mode support

#### 4.2.2 Suricata (Intrusion Detection)

| Attribute | Value |
|-----------|-------|
| **Base Image** | Ubuntu 22.04 |
| **Package** | Suricata from APT |
| **Function** | Real-time threat detection and alerting |
| **Output** | EVE JSON format (`eve.json`) |
| **Network Mode** | Host (for packet capture) |

**Configuration (`suricata.yaml`):**
```yaml
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
    EXTERNAL_NET: "!$HOME_NET"

outputs:
  - eve-log:
      types: [alert, http, dns, tls, files, flow]

detect:
  profile: medium
```

**Key Features:**
- Signature-based detection
- Protocol anomaly detection
- Extended HTTP logging
- Payload capture

#### 4.2.3 KitNET (AI Anomaly Detection)

| Attribute | Value |
|-----------|-------|
| **Base Image** | Python 3.9-slim |
| **Framework** | Custom implementation |
| **Function** | Machine learning anomaly detection |
| **Input** | Zeek connection logs |
| **Network Mode** | Host |

**Architecture:**
- **Ensemble Autoencoders**: Multiple simple autoencoders for different feature groups
- **Training Phase**: 1000 samples for model initialization
- **Anomaly Scoring**: 0.0 - 1.0 scale (higher = more anomalous)
- **Default Threshold**: 0.95

**Feature Extraction:**
```python
features = [
    orig_bytes,          # Original bytes sent
    resp_bytes,          # Response bytes
    duration,            # Connection duration
    src_port,            # Source port
    dest_port,           # Destination port
    src_ip (encoded),    # Source IP as integer
    dest_ip (encoded),   # Destination IP as integer
    protocol (encoded),  # Protocol type
    orig_pkts,           # Packets from originator
    resp_pkts,           # Packets from responder
    time_features...,    # Hour, minute, day of week
    flow_features...     # Zeek-specific flow data
]
```

**Dependencies:**
```
numpy==1.24.3
scipy==1.10.1
scikit-learn==1.3.0
pandas==2.0.3
aiohttp==3.8.4
```

#### 4.2.4 Bridge (Orchestration Service)

| Attribute | Value |
|-----------|-------|
| **Base Image** | Python 3.9-slim |
| **Framework** | FastAPI |
| **Function** | Service coordination and API gateway |
| **Port** | 8001 |
| **Network** | sentry_shared_network (bridge mode) |

**Key Components:**

1. **EnhancedPlatformDetector**: Auto-detects container environment, OS, network interfaces, Docker capabilities

2. **AlertProcessor**: Queue-based alert processing with history management (last 1000 alerts)

3. **OracleClient**: Handles escalation to Oracle cloud service with evidence snapshot collection

4. **SentryStatus**: Background monitoring of all service health (30-second intervals)

**API Endpoints:**
- `GET /health` - Service health check
- `POST /alerts` - Receive alerts from services
- `GET /api/discovery` - Network device discovery
- `GET /` - Consumer setup UI

**Consumer UI:**
- Located at `src/templates/index.html`
- Shows Sentry status and setup instructions
- Real-time anomaly score logging
- "Connect to Cloud Oracle" functionality

#### 4.2.5 Redis (Cache)

| Attribute | Value |
|-----------|-------|
| **Image** | redis:7-alpine |
| **Port** | 6380:6379 |
| **Function** | Caching and state management |

### 4.3 Docker Compose Configuration

```yaml
services:
  zeek:      # Network mode: host, depends_on: bridge
  suricata:  # Network mode: host, depends_on: bridge
  kitnet:    # Network mode: host, depends_on: bridge
  bridge:    # Port 8001, network: sentry_shared_network
  redis:     # Port 6380, network: sentry_shared_network

networks:
  sentry-network:
    name: sentry_shared_network
    driver: bridge

volumes:
  redis_data:
```

### 4.4 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEEK_INTERFACE` | auto | Network interface for Zeek |
| `SURICATA_INTERFACE` | eth0 | Network interface for Suricata |
| `KITNET_INTERFACE` | wlan0 | Network interface for KitNET |
| `KITNET_THRESHOLD` | 0.95 | Anomaly detection threshold |
| `LOG_LEVEL` | info | Logging verbosity |
| `BRIDGE_URL` | http://localhost:8001/alerts | Bridge alert endpoint |
| `ORACLE_WEBHOOK_URL` | http://cardea-oracle:8000/api/alerts | Oracle endpoint |
| `SENTRY_ID` | sentry_001 | Unique Sentry identifier |
| `ALERT_THRESHOLD` | 0.95 | Alert escalation threshold |
| `DEV_MODE` | true | Development mode flag |

---

## 5. Oracle Layer (Cloud)

### 5.1 Purpose

The Oracle layer is the "Brain" of the system - a cloud-based AI threat analysis and management platform that provides:
- AI-powered threat reasoning using Azure OpenAI GPT-4o
- RAG-enhanced context using Azure AI Search
- Time-series alert storage
- Advanced threat correlation
- Human-readable security recommendations

### 5.2 Service Components

#### 5.2.1 FastAPI Backend

| Attribute | Value |
|-----------|-------|
| **Base Image** | Python 3.11-slim |
| **Framework** | FastAPI with async SQLAlchemy |
| **Port** | 8000 |

**Key Modules:**

1. **oracle_service.py** (256 lines)
   - FastAPI application factory
   - CORS middleware configuration
   - Redis-based abuse safeguards (de-duplication, rate limiting)
   - API route handlers

2. **analytics.py** (978 lines)
   - `ThreatAnalyzer`: AI-powered threat scoring
   - `AlertCorrelator`: Temporal/spatial alert correlation
   - Azure OpenAI integration for agentic reasoning
   - Cyber Kill Chain stage identification
   - Adaptive threshold recommendations

3. **search_service.py** (437 lines)
   - Azure AI Search integration
   - Threat intelligence index schema
   - Semantic search for historical threats (RAG)
   - Vector search with HNSW algorithm

4. **database.py** (155 lines)
   - Async PostgreSQL with SQLAlchemy 2.0
   - Models: Alert, ThreatIntelligence
   - Timezone-aware timestamps
   - Optimized indexes for querying

5. **models.py** (133 lines)
   - Pydantic v2 request/response schemas
   - Alert severity enum: LOW, MEDIUM, HIGH, CRITICAL
   - Alert types: NETWORK_ANOMALY, INTRUSION_DETECTION, MALWARE_DETECTION, etc.

6. **config.py**
   - Pydantic Settings with environment variable support
   - Azure OpenAI configuration
   - Azure AI Search configuration
   - Database and Redis URLs

#### 5.2.2 PostgreSQL Database

| Attribute | Value |
|-----------|-------|
| **Image** | postgres:15-alpine |
| **Port** | 5433:5432 |
| **Database** | cardea_oracle |
| **User** | oracle |

**Schema:**
```sql
-- alerts table
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    threat_score FLOAT,
    risk_level VARCHAR(20),
    raw_data JSONB,
    network_context JSONB,
    correlations JSONB,
    indicators JSONB
);

-- Indexes for performance
CREATE INDEX idx_alerts_timestamp_severity ON alerts(timestamp, severity);
CREATE INDEX idx_alerts_source_type ON alerts(source, alert_type);
CREATE INDEX idx_alerts_threat_score ON alerts(threat_score);
```

#### 5.2.3 Redis (Abuse Protection)

| Attribute | Value |
|-----------|-------|
| **Image** | redis:7-alpine |
| **Port** | 6381:6379 |

**Safeguard Features:**
- **De-duplication**: 60-second window for identical alerts
- **Rate Limiting**: Max 50 AI-processed alerts per minute
- **Token Optimization**: 150 max response tokens per AI call

### 5.3 AI Features

#### 5.3.1 Azure OpenAI Integration

| Setting | Value |
|---------|-------|
| **Model** | gpt-4o (production) / gpt-4o-mini (development) |
| **API Version** | 2024-08-01-preview |
| **Temperature** | 0.3 (for consistent analysis) |
| **Max Tokens** | 1500 |

**Capabilities:**
1. **Intent Analysis**: Identifies attack intent and motive
2. **Kill Chain Mapping**: Determines Cyber Kill Chain stage
3. **Human-Readable Output**: Business-owner friendly explanations
4. **Threshold Recommendations**: Adaptive KitNET sensitivity tuning

#### 5.3.2 Azure AI Search (RAG)

| Setting | Value |
|---------|-------|
| **Index Name** | threat-intelligence |
| **Algorithm** | HNSW (Hierarchical Navigable Small World) |
| **Analyzer** | en.microsoft |

**Index Schema Fields:**
- `threat_id` (key)
- `alert_type`, `severity` (filterable, facetable)
- `title`, `description`, `resolution` (searchable)
- `indicators`, `attack_patterns` (collection)
- `threat_score`, `confidence_score` (sortable)
- `first_seen`, `last_seen` (datetime)

### 5.4 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health with DB/Redis status |
| POST | `/api/v1/alerts` | Receive alerts from Sentry |
| POST | `/api/v1/analyze/threats` | AI threat analysis |
| GET | `/api/v1/analytics` | Dashboard analytics data |

### 5.5 Docker Compose Configuration

```yaml
services:
  db:        # PostgreSQL 15, port 5433
  redis:     # Redis 7, port 6381
  oracle:    # FastAPI app, port 8000

networks:
  oracle-network: internal
  sentry_shared_network: external

volumes:
  postgres_data:
  redis_data:
```

### 5.6 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql+asyncpg://oracle:...@db:5432/cardea_oracle | Database connection |
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `AZURE_OPENAI_API_KEY` | (required) | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | (required) | Azure OpenAI endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | gpt-4o | Model deployment name |
| `AZURE_SEARCH_ENDPOINT` | (optional) | Azure AI Search endpoint |
| `AZURE_SEARCH_KEY` | (optional) | Azure AI Search key |
| `AI_ENABLED` | false | Enable AI features |
| `THREAT_SCORE_THRESHOLD` | 0.7 | Threat scoring threshold |
| `LOG_LEVEL` | INFO | Logging verbosity |
| `DEBUG` | true | Debug mode |

---

## 6. Dashboard Layer (UI)

### 6.1 Purpose

The Dashboard layer provides a real-time web-based monitoring interface for security operators and business owners to:
- Visualize network topology
- Monitor live threat feeds
- View AI-generated threat analysis
- Manage security incidents

### 6.2 Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **Vite** | 7.2.4 | Build tool and dev server |
| **React** | 19.2.0 | UI framework |
| **TypeScript** | 5.9.3 | Type safety |
| **TailwindCSS** | 4.1.18 | Utility-first CSS |
| **React Flow** | 12.10.0 (xyflow) | Network visualization |
| **shadcn/ui** | New York style | UI components |
| **Axios** | 1.13.2 | HTTP client |
| **React Router** | 7.11.0 | Client-side routing |
| **Lucide React** | 0.562.0 | Icon library |

### 6.3 Component Architecture

#### 6.3.1 App.tsx (Main Application)

```typescript
// State management
const [data, setData] = useState<AnalyticsResponse | null>(null);

// Data fetching from Oracle
const fetchData = async () => {
  const res = await axios.get<AnalyticsResponse>(`${ORACLE_URL}/api/analytics`);
  setData(res.data);
};

// Auto-refresh every 5 seconds
useEffect(() => {
  const interval = setInterval(fetchData, 5000);
  return () => clearInterval(interval);
}, []);
```

**Dashboard Sections:**
1. **Header**: Cardea branding, cloud link status, node identifier
2. **Network Map**: React Flow network topology
3. **Risk Index**: AI-calculated risk score (percentage)
4. **Telemetry Events**: Total alert count
5. **Live Anomaly Feed**: Real-time alert table

#### 6.3.2 NetworkMap.tsx (Network Visualization)

**Node Types:**
- `sentry`: Shield icon, cyan color, glow effect
- `cloud`: Globe icon, purple color, glow effect
- `asset`: Device icons (laptop, mobile, IoT)

**Device States:**
- `online`: Normal styling
- `offline`: Grayscale, dimmed
- `alert`: Red color, pulsing animation

**Data Source:**
```typescript
fetch('http://localhost:8001/api/discovery')
// Returns: { devices: [...], links: [...] }
```

#### 6.3.3 LoginPage.tsx (Authentication)

**Features:**
- Email/password authentication
- Social login buttons (Google, Microsoft)
- Form validation
- Loading states
- Error handling
- Route navigation

#### 6.3.4 UI Components (shadcn/ui)

Located in `@/components/ui/` and `src/components/ui/`:
- `badge.tsx`: Status badges
- `card.tsx`: Content containers
- `scroll-area.tsx`: Scrollable regions
- `table.tsx`: Data tables
- `button.tsx`: Interactive buttons

### 6.4 TypeScript Interfaces

```typescript
// types.ts
interface Alert {
  id: number;
  source: string;
  alert_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  timestamp: string;
  threat_score?: number;
  raw_data?: Record<string, any>;
}

interface AnalyticsResponse {
  total_alerts: number;
  risk_score: number;
  alerts: Alert[];
}

interface FlowData {
  nodes: Array<{
    id: string;
    type: string;
    data: { label: string; status?: string };
    position: { x: number; y: number };
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    animated?: boolean;
  }>;
}
```

### 6.5 Configuration

#### vite.config.ts
```typescript
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
```

#### tailwind.config.ts
- Dark mode: class-based
- Base color: slate
- CSS variables for theming
- Container: centered, 2rem padding, max 1400px

#### components.json (shadcn/ui)
```json
{
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "baseColor": "slate",
    "cssVariables": true
  }
}
```

### 6.6 Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Preview production build
npm run preview
```

---

## 7. Shared Libraries

### 7.1 Purpose

Common utilities and types shared across all Cardea components to ensure consistency and reduce code duplication.

### 7.2 Platform Detection (`platform_detector.py`)

**Class: PlatformDetector**

Detects and reports on the deployment environment:

```python
# Detection capabilities
- Operating system (Linux distro, macOS, Windows)
- Network interfaces (type, state, name)
- Docker capabilities (installed, running, compose version)
- Hardware info (CPU, memory)
- Container environment (Docker, Podman)
```

**Supported Platforms:**
| Platform | Package Manager | Optimizations |
|----------|-----------------|---------------|
| Ubuntu/Debian | APT | Standard paths |
| Arch Linux | Pacman | Rolling release support |
| CentOS/RHEL | YUM/DNF | SELinux awareness |
| macOS | Homebrew | Darwin compatibility |

### 7.3 Environment Configuration (`environment_configurator.py`)

**Class: EnvironmentConfigurator**

Generates platform-optimized configuration:

```python
# Capabilities
- generate_sentry_env()     # Environment variables
- generate_docker_compose_config()  # Docker Compose YAML
- generate_platform_report()  # Human-readable report
```

**Memory Optimization Logic:**
| System Memory | Zeek Limit | Suricata Limit | KitNET Limit |
|---------------|------------|----------------|--------------|
| ≥ 8 GB | 2g | 1g | 2g |
| ≥ 4 GB | 1g | 512m | 1g |
| < 4 GB | 512m | 256m | 512m |

### 7.4 Platform CLI (`platform_cli.py`)

Command-line interface for platform tools:

```bash
# Commands
python platform_cli.py report     # Full platform report
python platform_cli.py config     # Generate environment config
python platform_cli.py validate   # Validate deployment readiness
python platform_cli.py interface  # Get recommended network interface
```

---

## 8. Infrastructure

### 8.1 Terraform Configuration

**Provider:** Azure Resource Manager (azurerm ~> 3.0)

**Resources:**

| Resource | Name | Location |
|----------|------|----------|
| Resource Group | rg-cardea-oracle | East Asia |
| Azure OpenAI | cardea-openai-service | Sweden Central |
| Azure AI Search | cardea-threat-search | Sweden Central |

**Model Selection Logic:**
```hcl
# Development: gpt-4o-mini (cheaper)
# Production: gpt-4o (more capable)
model {
  name = var.is_production ? "gpt-4o" : "gpt-4o-mini"
}

# Development: Free tier ($0)
# Production: Basic tier (~$73/mo)
sku = var.is_production ? "basic" : "free"
```

**Outputs:**
- `openai_endpoint`: Azure OpenAI endpoint URL
- `search_endpoint`: Azure AI Search endpoint URL
- `current_mode`: PRODUCTION or DEVELOPMENT indicator

### 8.2 Docker Architecture

**Container Images:**

| Service | Base Image | Size Class |
|---------|------------|------------|
| Zeek | ubuntu:22.04 | Large |
| Suricata | ubuntu:22.04 | Large |
| KitNET | python:3.9-slim | Medium |
| Bridge | python:3.9-slim | Small |
| Oracle | python:3.11-slim | Medium |
| PostgreSQL | postgres:15-alpine | Medium |
| Redis | redis:7-alpine | Small |

**Network Modes:**
- **Host Mode**: Zeek, Suricata, KitNET (required for packet capture)
- **Bridge Mode**: Bridge, Oracle services

**Capabilities Required:**
- `NET_ADMIN`: Network administration
- `NET_RAW`: Raw socket access

---

## 9. Scripts & Automation

### 9.1 start-sentry.sh

**Purpose:** Main Sentry startup and validation script

**Features:**
- Docker availability check
- Docker Compose detection (v1 and v2)
- Python dependency validation
- Configuration file validation
- Data directory creation
- Service startup

**Usage:**
```bash
./scripts/start-sentry.sh           # Start services
./scripts/start-sentry.sh check     # Validate only
./scripts/start-sentry.sh stop      # Stop services
```

### 9.2 setup-dev.sh

**Purpose:** Development environment setup

**Steps:**
1. Check prerequisites (Docker, Node.js, Python)
2. Setup shared libraries
3. Create Python setup.py
4. Create TypeScript package.json
5. Generate development Docker Compose

### 9.3 setup-platform.sh

**Purpose:** Platform-aware configuration generation

**Steps:**
1. Check Python dependencies (pyyaml)
2. Run platform detection
3. Generate environment configuration
4. Create platform-optimized Docker Compose
5. Validate deployment readiness

### 9.4 Makefile Targets

| Target | Description |
|--------|-------------|
| `help` | Show available targets |
| `dev-setup` | Set up development environment |
| `platform-info` | Show platform detection results |
| `clean` | Clean build artifacts and containers |
| `test` | Run all tests |
| `lint` | Run linting |
| `format` | Format code |
| `sentry-dev` | Start Sentry development mode |
| `oracle-dev` | Start Oracle development mode |
| `dashboard-dev` | Start Dashboard development mode |
| `integration` | Run integration tests |
| `deploy-local` | Deploy full stack locally |

---

## 10. Configuration Details

### 10.1 Root Package.json

```json
{
  "devDependencies": {
    "@tailwindcss/postcss": "^4.1.18",
    "autoprefixer": "^10.4.23",
    "postcss": "^8.5.6"
  }
}
```

### 10.2 Root Requirements.txt

**Core Dependencies:**
- fastapi>=0.104.0
- uvicorn[standard]>=0.24.0
- aiohttp>=3.9.0
- aiofiles>=23.2.0

**Data Processing:**
- pandas>=2.1.0
- numpy>=1.24.0
- scikit-learn>=1.3.0

**Network/Security:**
- scapy>=2.5.0
- pyzmq>=25.1.0

**Configuration:**
- pydantic>=2.5.0
- pyyaml>=6.0.1
- python-dotenv>=1.0.0

**Development:**
- pytest>=7.4.0
- black>=23.11.0
- mypy>=1.7.0

**Cloud (Phase 3):**
- oci>=2.115.0

### 10.3 Zeek Configuration

**node.cfg:**
```ini
[manager]
type=manager
host=localhost

[logger]
type=logger
host=localhost

[worker-1]
type=worker
host=localhost
interface=eth0
```

**zeek.cfg:**
```zeek
@load base/frameworks/cluster
@load base/frameworks/logging
@load base/protocols/conn
@load base/protocols/http
@load base/protocols/dns

redef LogAscii::use_json = T;
redef LogAscii::json_timestamps = JSON::TS_ISO8601;
```

### 10.4 Suricata Configuration

**suricata.yaml:**
```yaml
vars:
  address-groups:
    HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.16.0.0/12]"
    EXTERNAL_NET: "!$HOME_NET"

outputs:
  - fast: { enabled: yes, filename: fast.log }
  - eve-log:
      enabled: yes
      filename: eve.json
      types: [alert, http, dns, tls, files, flow]

detect:
  profile: medium
```

---

## 11. Technology Stack

### 11.1 Languages

| Language | Version | Usage |
|----------|---------|-------|
| Python | 3.9 - 3.11 | Backend services, ML |
| TypeScript | 5.9.3 | Dashboard frontend |
| Bash | 5.x | Scripts and automation |
| HCL | 1.x | Terraform infrastructure |

### 11.2 Frameworks & Libraries

#### Backend
| Framework | Version | Service |
|-----------|---------|---------|
| FastAPI | 0.104.1 | Bridge, Oracle |
| SQLAlchemy | 2.0.23 | Oracle ORM |
| Pydantic | 2.5.0 | Data validation |
| uvicorn | 0.24.0 | ASGI server |

#### Frontend
| Framework | Version | Purpose |
|-----------|---------|---------|
| React | 19.2.0 | UI framework |
| Vite | 7.2.4 | Build tool |
| TailwindCSS | 4.1.18 | Styling |
| React Flow | 12.10.0 | Network viz |
| shadcn/ui | latest | Components |

#### Machine Learning
| Library | Version | Purpose |
|---------|---------|---------|
| scikit-learn | 1.3.x | ML algorithms |
| numpy | 1.24.x | Numerical ops |
| pandas | 2.x | Data processing |

#### Cloud Services
| Service | Provider | Purpose |
|---------|----------|---------|
| Azure OpenAI | Microsoft | GPT-4o reasoning |
| Azure AI Search | Microsoft | RAG search |
| PostgreSQL | Self-hosted | Data storage |
| Redis | Self-hosted | Caching |

### 11.3 Security Tools

| Tool | Version | Function |
|------|---------|----------|
| Zeek | Latest | Network analysis |
| Suricata | Latest | IDS/IPS |
| KitNET | Custom | Anomaly detection |

### 11.4 Infrastructure

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 20.10+ | Containerization |
| Docker Compose | v2+ | Orchestration |
| Terraform | 1.x | IaC |

---

## 12. API Reference

### 12.1 Bridge API (Port 8001)

#### Health Check
```http
GET /health
Response: {
  "status": "healthy",
  "services": {...},
  "uptime": 12345
}
```

#### Submit Alert
```http
POST /alerts
Content-Type: application/json

{
  "source": "kitnet",
  "severity": "high",
  "event_type": "network_anomaly",
  "description": "AI detected anomaly with score 0.9876",
  "raw_data": {...},
  "confidence": 0.95
}

Response: {
  "alert_id": "uuid",
  "status": "accepted"
}
```

#### Network Discovery
```http
GET /api/discovery
Response: {
  "devices": [
    {
      "id": "sentry_001",
      "name": "Cardea Sentry",
      "role": "sentry",
      "ip": "192.168.1.100",
      "status": "online"
    }
  ],
  "links": [
    {
      "source": "sentry_001",
      "target": "device_001",
      "active": true,
      "status": "normal"
    }
  ]
}
```

### 12.2 Oracle API (Port 8000)

#### Health Check
```http
GET /health
Response: {
  "status": "healthy",
  "timestamp": "2026-01-06T...",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy"
  },
  "system": {...}
}
```

#### Submit Alert
```http
POST /api/v1/alerts
Content-Type: application/json

{
  "source": "sentry_001",
  "alert_type": "network_anomaly",
  "severity": "high",
  "title": "Suspicious outbound connection",
  "description": "...",
  "raw_data": {...}
}

Response: {
  "alert_id": 123,
  "status": "processed",
  "threat_score": 0.85,
  "processing_time_ms": 250
}
```

#### AI Threat Analysis
```http
POST /api/v1/analyze/threats
Content-Type: application/json

{
  "time_window": 3600,
  "threat_types": ["data_exfiltration"],
  "include_correlations": true
}

Response: {
  "analysis_id": "uuid",
  "threats_detected": [...],
  "risk_score": 0.72,
  "recommendations": [...],
  "processing_time_ms": 1500
}
```

#### Dashboard Analytics
```http
GET /api/v1/analytics?time_range=24h
Response: {
  "total_alerts": 150,
  "risk_score": 0.35,
  "alerts": [...],
  "alerts_by_severity": {...},
  "alerts_by_type": {...}
}
```

---

## 13. Data Flow

### 13.1 Alert Processing Pipeline

```
1. CAPTURE
   └── Zeek/Suricata capture network packets
   
2. ANALYSIS
   ├── Zeek → conn.log (connection metadata)
   ├── Suricata → eve.json (IDS alerts)
   └── KitNET → anomaly scores

3. AGGREGATION
   └── Bridge receives alerts from all sources
       ├── Queue-based processing
       └── History management (last 1000)

4. ESCALATION
   └── High-score alerts → Oracle Cloud
       ├── Evidence snapshot collection
       └── Webhook delivery

5. AI ANALYSIS
   └── Oracle processes alerts
       ├── De-duplication (60s window)
       ├── Rate limiting (50/min)
       ├── RAG context retrieval
       └── GPT-4o threat reasoning

6. STORAGE
   └── PostgreSQL persistence
       ├── Alert records
       └── Threat intelligence

7. VISUALIZATION
   └── Dashboard displays
       ├── Real-time updates (5s interval)
       ├── Network topology
       └── Risk metrics
```

### 13.2 KitNET ML Pipeline

```
1. INPUT
   └── Zeek conn.log entries

2. FEATURE EXTRACTION
   ├── Numeric features (10+)
   ├── Time-based features
   └── Flow features

3. NORMALIZATION
   └── StandardScaler

4. TRAINING (if model doesn't exist)
   ├── Initialize autoencoders
   ├── 1000 sample training phase
   └── Model persistence

5. INFERENCE
   ├── Feature normalization
   ├── Autoencoder reconstruction
   └── Reconstruction error = anomaly score

6. ALERTING
   └── score >= threshold → Alert to Bridge
```

---

## 14. Development Workflow

### 14.1 Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Docker | 20.10+ | Containerization |
| Docker Compose | v2+ | Service orchestration |
| Python | 3.9+ | Backend development |
| Node.js | 18+ | Frontend development |
| Git | 2.x | Version control |

### 14.2 Local Development Setup

```bash
# 1. Clone repository
git clone <repository>
cd cardea

# 2. Make scripts executable
chmod +x scripts/*.sh

# 3. Setup development environment
make dev-setup

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Install Dashboard dependencies
cd dashboard && npm install && cd ..

# 6. Start Sentry services
./scripts/start-sentry.sh

# 7. Start Oracle (in another terminal)
cd oracle && docker-compose up

# 8. Start Dashboard (in another terminal)
cd dashboard && npm run dev
```

### 14.3 Development Mode Commands

```bash
# Sentry development with hot reload
cd sentry/bridge
uvicorn src.bridge_service:app --reload --host 0.0.0.0 --port 8001

# Oracle development
cd oracle
python src/main.py

# Dashboard development
cd dashboard
npm run dev
```

### 14.4 Testing

```bash
# Run all tests
make test

# Sentry runtime validation
python3 test_runtime_basic.py

# Platform compatibility test
python3 shared/utils/platform_cli.py validate

# Dashboard linting
cd dashboard && npm run lint
```

---

## 15. Deployment

### 15.1 Quick Start (Sentry Only)

```bash
# Automated startup
./scripts/start-sentry.sh

# Or manually
cd sentry
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:8001/health
```

### 15.2 Full Stack Deployment

```bash
# 1. Start Sentry
./scripts/start-sentry.sh

# 2. Start Oracle
cd oracle
docker-compose up -d

# 3. Start Dashboard
cd dashboard
npm run build
npm run preview
```

### 15.3 Production Checklist

- [ ] Configure network interface environment variables
- [ ] Set strong passwords for PostgreSQL
- [ ] Configure Azure OpenAI credentials
- [ ] Configure Azure AI Search credentials
- [ ] Enable HTTPS/TLS
- [ ] Set up monitoring and logging
- [ ] Configure backup procedures
- [ ] Test network packet capture permissions
- [ ] Validate Suricata rules
- [ ] Test alert escalation pipeline

### 15.4 Cloud Deployment (Azure)

```bash
# 1. Initialize Terraform
cd infrastructure/terraform
terraform init

# 2. Plan deployment
terraform plan -var="is_production=false"

# 3. Apply infrastructure
terraform apply

# 4. Get outputs
terraform output openai_endpoint
terraform output search_endpoint
```

---

## Appendix A: Environment Variable Reference

| Variable | Component | Required | Default |
|----------|-----------|----------|---------|
| `ZEEK_INTERFACE` | Sentry | No | auto |
| `SURICATA_INTERFACE` | Sentry | No | eth0 |
| `KITNET_INTERFACE` | Sentry | No | wlan0 |
| `KITNET_THRESHOLD` | Sentry | No | 0.95 |
| `ALERT_THRESHOLD` | Sentry | No | 0.95 |
| `LOG_LEVEL` | All | No | info |
| `SENTRY_ID` | Sentry | No | sentry_001 |
| `BRIDGE_URL` | KitNET | No | http://localhost:8001/alerts |
| `ORACLE_WEBHOOK_URL` | Bridge | No | http://cardea-oracle:8000/api/alerts |
| `DATABASE_URL` | Oracle | Yes | - |
| `REDIS_URL` | Oracle | No | redis://redis:6379/0 |
| `AZURE_OPENAI_API_KEY` | Oracle | For AI | - |
| `AZURE_OPENAI_ENDPOINT` | Oracle | For AI | - |
| `AZURE_OPENAI_DEPLOYMENT` | Oracle | No | gpt-4o |
| `AZURE_SEARCH_ENDPOINT` | Oracle | For RAG | - |
| `AZURE_SEARCH_KEY` | Oracle | For RAG | - |
| `AI_ENABLED` | Oracle | No | false |
| `DEBUG` | Oracle | No | true |

---

## Appendix B: Port Reference

| Port | Service | Protocol | Description |
|------|---------|----------|-------------|
| 8001 | Bridge | HTTP | Sentry API gateway |
| 8000 | Oracle | HTTP | Cloud API |
| 5433 | PostgreSQL | PostgreSQL | Database (mapped from 5432) |
| 6380 | Sentry Redis | Redis | Sentry cache (mapped from 6379) |
| 6381 | Oracle Redis | Redis | Oracle cache (mapped from 6379) |
| 47760 | Zeek | TCP | Zeek communication |
| 5173 | Dashboard | HTTP | Vite dev server |

---

## Appendix C: File Count Summary

| Directory | Files | Lines (approx) |
|-----------|-------|----------------|
| `/sentry/bridge/src/` | 6 | ~900 |
| `/sentry/services/kitnet/src/` | 4 | ~700 |
| `/sentry/services/zeek/` | 5 | ~150 |
| `/sentry/services/suricata/` | 5 | ~150 |
| `/oracle/src/` | 7 | ~2,300 |
| `/dashboard/src/` | 8 | ~700 |
| `/shared/utils/` | 3 | ~750 |
| `/scripts/` | 6 | ~800 |
| `/infrastructure/` | 2 | ~80 |
| **Total** | **~46** | **~6,500** |

---

*Generated for Project Cardea - Hybrid AI Cybersecurity Platform*
*Copyright © 2026 Project Cardea - MIT License*
