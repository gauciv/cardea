# Project Cardea - Context Documentation

> **Last Updated:** January 12, 2026 (16:08 UTC+8)  
> **Status:** All Layers Functional ✅

---

## Recent Changes (January 12, 2026)

### UI Overhaul - Sidebar Navigation
- **Removed**: Old UserMenu dropdown in header
- **Added**: Collapsible left sidebar (`Sidebar.tsx`)
  - Collapsed: 56px wide, icons only with hover tooltips
  - Expanded: 192px wide, icons + labels
  - Toggle button on right edge (chevron)
  - Active page indicator (cyan highlight + left bar)
  - User avatar + name at bottom
  - Sign Out button
  - Smooth 200ms transitions
- **Layout Component**: Wraps all pages with sidebar
- **PageHeader**: Simplified to just title/subtitle + actions slot

### Dashboard Components
- **DeviceSetup**: Compact no-device state (icon + title + "Add Device" button)
- **ThreatMap**: Network topology visualization (works with internal IPs)
  - Central "SENTRY" hub
  - Nodes for each unique IP source
  - Animated connection lines colored by severity
  - Badge showing alert count per IP
- **DetailedLogs**: Expandable log viewer
  - Filter by severity (All/High/Critical)
  - Click to expand for full details (description, threat score, raw JSON)
  - Monospace font, color-coded severity badges

### Removed Components
- `NoDevicesState.tsx` - Replaced by compact DeviceSetup
- `OnboardingOverlay.tsx`, `OnboardingTooltip.tsx`, `useOnboarding.ts` - Onboarding flow removed
- `NavBar.tsx` - Replaced by Sidebar
- `UserMenu.tsx` - Functionality moved to Sidebar

### View Modes
- **Simple Mode**: AI Persona + SimpleStats cards
- **Detailed Mode**: + ThreatMap + DetailedLogs

---

## Architecture Overview

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   CARDEA SENTRY     │────│   CARDEA ORACLE     │────│   WEB DASHBOARD     │
│   (Edge Layer)      │    │   (Cloud Layer)     │    │   (User Layer)      │
│      ✅ READY       │    │      ✅ READY       │    │      ✅ READY       │
│                     │    │                     │    │                     │
│ • Zeek (Network)    │    │ • FastAPI Backend   │    │ • Vite + React 19   │
│ • Suricata (IDS)    │    │ • Azure OpenAI      │    │ • TypeScript 5.9    │
│ • KitNET (AI)       │    │ • Azure AI Search   │    │ • TailwindCSS 4     │
│ • Bridge (API)      │    │ • PostgreSQL        │    │ • Collapsible       │
│                     │    │ • Redis             │    │   Sidebar Nav       │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

---

## Dashboard Structure

### Pages & Routes
| Route | Component | Description |
|-------|-----------|-------------|
| `/dashboard` | `App.tsx` | Main dashboard with AI Persona |
| `/devices` | `DevicesPage.tsx` | Sentry device management |
| `/settings` | `SettingsPage.tsx` | User preferences |
| `/profile` | `ProfilePage.tsx` | User account info |
| `/login` | `LoginPage.tsx` | Authentication |
| `/` | `LandingPage.tsx` | Public landing page |

### Component Hierarchy
```
Layout (with Sidebar)
├── PageHeader (title, subtitle, actions)
└── Page Content
    ├── App.tsx
    │   ├── AIPersona (greeting, status, actions)
    │   ├── SimpleStats (device status, risk level)
    │   ├── DeviceSetup (when no devices)
    │   └── [Detailed Mode]
    │       ├── ThreatMap
    │       └── DetailedLogs
    ├── DevicesPage.tsx
    ├── SettingsPage.tsx
    └── ProfilePage.tsx
```

### Key Components
| Component | Location | Purpose |
|-----------|----------|---------|
| `Sidebar` | `/components/Sidebar.tsx` | Collapsible left navigation |
| `Layout` | `/components/Layout.tsx` | Page wrapper with sidebar |
| `PageHeader` | `/components/PageHeader.tsx` | Page title + actions |
| `AIPersona` | `/components/dashboard/AIPersona.tsx` | AI greeting + threat actions |
| `SimpleStats` | `/components/dashboard/AIPersona.tsx` | Status cards |
| `DeviceSetup` | `/components/dashboard/DeviceSetup.tsx` | No-device state |
| `ThreatMap` | `/components/dashboard/ThreatMap.tsx` | Network topology |
| `DetailedLogs` | `/components/dashboard/DetailedLogs.tsx` | Expandable alert logs |

---

## Oracle API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health (DB, Redis, AI) |
| POST | `/api/alerts` | Ingest alert from Sentry |
| GET | `/api/analytics` | Dashboard data + AI insight |
| DELETE | `/api/alerts/clear` | Clear all alerts (demo) |
| POST | `/api/actions/execute` | Execute user action (block IP) |
| GET | `/api/devices/list` | List user's devices |
| POST | `/api/devices/claim` | Claim device with pairing code |

---

## AI Token Optimization

- **100% Deterministic Insights**: No AI tokens for routine monitoring
- **5-minute Cache TTL**: Same situation won't regenerate
- **Cache key based on alert IDs**: Only regenerates when NEW alerts arrive
- **Alert Grouping**: Related alerts grouped into ONE actionable item

---

## Environment Variables

### Oracle Required
```
DATABASE_URL=postgresql+asyncpg://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://...openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### Oracle Optional (RAG)
```
AZURE_SEARCH_ENDPOINT=https://...search.windows.net
AZURE_SEARCH_KEY=...
```

### Dashboard
```
VITE_ORACLE_URL=http://localhost:8000
```

---

## Development Commands

```bash
# Dashboard
cd dashboard && npm run dev      # Dev server
cd dashboard && npm run build    # Production build

# Oracle
cd oracle && docker-compose up   # Start services
cd oracle && uvicorn src.main:app --reload  # Dev mode

# Sentry
./scripts/start-sentry.sh        # Start all services
```

---

## Port Reference

| Port | Service | Description |
|------|---------|-------------|
| 5173 | Dashboard | Vite dev server |
| 8000 | Oracle | FastAPI backend |
| 8001 | Sentry Bridge | Alert aggregation |
| 5433 | PostgreSQL | Database |
| 6381 | Redis | Cache |

---

*Project Cardea - Hybrid AI Cybersecurity Platform*
