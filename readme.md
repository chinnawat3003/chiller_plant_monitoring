# Chiller Plant Monitoring + Recommendation System

A **Chiller Plant Monitoring + Recommendation system** that combines:
- **Real-time monitoring dashboard** (plant status, chiller/pump/thermoform power, temperatures, flow, charts)
- **Cost & energy summary** (kWh/THB)
- **Rule-based operational recommendation** (e.g., keep 1 chiller vs. run 2 chillers based on load/temperature stability)
- **LLM integration via Langflow (MCP tools)** so users can ask questions like “How about Thermoform?” and get structured “Decision/Reasoning” outputs.

## Outcome (End-to-End Stack)

Working pipeline:
1) **InfluxDB time-series data**  
→ 2) **FastAPI backend**  
→ 3) **Next.js Frontend dashboard + Swagger**  
→ 4) **MCP tools**  
→ 5) **Langflow chat-based reasoning**

---

## Table of Contents
- [System Architecture]
- [Backend APIs]
- [Recommendation Engine]
- [Mockup Mode]
- [Langflow + Docker + MCP Integration]
- [Tech Stack]

---

## System Architecture

### A) Data Layer (InfluxDB → Flux Queries)
- Backend reads time-series data from **InfluxDB** using the official Python client and **Flux** queries.
- Config via `.env` (URL/TOKEN/ORG/BUCKET).
- Queries grouped by **plant tag lists** (P1/P2), e.g.:
  - Chiller power, Pump power, Tank temperatures, Chiller temperatures, Thermoform power
- Supports:
  - **Snapshot (latest point)** for live KPI tiles
  - **History (aggregateWindow)** for charts + decision logic

### B) Backend Service (FastAPI)
- REST endpoints for dashboard & analytics
- Includes:
  - **CORS** for local frontend
  - **Plant selector** via request header `X-Plant-ID` (fallback default e.g. P2)

### C) Business Logic / Analytics Layer
Service module responsibilities:
- Normalize raw Influx data into **UI-friendly slot IDs** (CH1/CH2/P9/TF4, etc.)
- Compute metrics:
  - **Cooling capacity** (from flow and ΔT)
  - **COP**
  - **Pump energy cost history** (kWh → THB)
- Produce **rule-based recommendation** with **anti-flapping** (conditions must be stable for N points)

### D) LLM + Langflow Integration (MCP Tools)
MCP tools exposed for Langflow:
- `recommend_rule()` → rule-based suggestion used by UI
- `get_state()` → compact numeric snapshot for LLM
- `decide_actions()` → structured output combining metrics + recommendation

Includes an **MCP proxy** to:
- Forward `/mcp` requests
- Rewrite `Host` header (fixes common local integration issues)
- Support **SSE streaming** (text/event-stream)

### E) Frontend (Next.js)
Monitoring dashboard features:
- Plant selector + live connection status
- Chiller plant diagram visualization (CH/TF/P nodes)
- Real-time KPI cards (kW, temperature, flow)
- Interactive charts (e.g., 24-hour chiller power trend with limit lines)
- Cost & energy summary (kWh, THB)
- Recommendation panel (suggested action + reasoning)

---

## Backend APIs

### Health & Live Monitoring
- `GET /health`

Snapshot endpoints (latest point):
- `GET /api/chill_pw` — chiller power snapshot
- `GET /api/pump_pw` — pump power snapshot
- `GET /api/pump_flow` — flow snapshot
- `GET /api/chiller_temp` — evap entering/leaving temps
- `GET /api/chiller_tank_temp` — return/supply tank temps
- `GET /api/thermoform_power` — thermoform kW

### History Endpoints (Charts)
Each has common parameters:
- `start` (default: `24h`)
- `every` (default: `10m`)
- optional `from` and `to` timestamps

Examples:
- `GET /api/chiller_pw_history`
- `GET /api/pump_pw_history`
- `GET /api/pump_flow_history`
- `GET /api/chiller_temp_history`
- `GET /api/chiller_tank_temp_history`
- `GET /api/thermoform_power_history`
- `GET /api/cooling_capa_history`

### Analytics
- `GET /api/cop` — compute COP from power, flow, tank temperatures
- `GET /api/pump_power_cost_history?rate=4.0`
  - Converts power history to:
    - total kWh
    - total THB
    - per-interval history records

### Recommendation
- `GET /api/recommend` — rule-based operational suggestion (1 vs 2 chillers)
- `GET /api/limit_chiller_power_input` — UI limits depending on whether any chiller is online

---

## Recommendation Engine

Design goals:
- **Explainable**: returns `status / suggest / reason / metrics`
- **Stable**: anti-flapping using lookback windows + N-point persistence
- **Plant-aware**: plant definitions (P1/P2), tag lists, UI slot mapping, COP mapping centralized in config

Key concepts:
- “Chiller ON” inferred from `power > threshold` (e.g., 50 kW)
- Cooling demand estimated via **cooling capacity** from flow and ΔT (return - supply)
- Switching rules:
  - If running 1 chiller and load/temp is persistently high → recommend 2 chillers
  - If running 2 chillers and cooling is persistently low → recommend drop to 1 chiller

---

## Mock Mode

To support development without real plant data:
- Mock provider controlled by env flag
- Generates realistic snapshots + history with jitter/noise
- Uses real plant’s configured tag list so UI + logic behave identically
- Enables consistent demo behavior

---

## Langflow + Docker + MCP Integration

### What was done
- Langflow runs via **Docker** as orchestration UI for LLM pipeline
- Backend exposes MCP tools so Langflow calls the plant system as tools (not only text)
- Chat interface outputs structured actions like:
  - `Action: ON/OFF`
  - `Target: CH1 / TF4 ...`
  - `Reasoning` using returned metrics (e.g., thermoform_total_kw, chiller_on counts)

### Why the MCP Proxy exists
Some setups fail due to host header + streaming constraints. Proxy:
- Forwards requests to MCP server
- Rewrites `Host` header
- Supports `text/event-stream` (SSE streaming)

### MCP Tool Endpoints
- `recommend_rule(plant_id)`
- `get_state(plant_id)`
- `decide_actions(plant_id, objective="chiller_only" | "optimize")`

---

## Tech Stack

**Backend**
- Python
- FastAPI (REST API + Swagger)
- httpx (proxying MCP requests)
- pandas / numpy (data shaping, pivoting, cost & cooling calculations)
- InfluxDB Python client + Flux queries

**Data**
- InfluxDB (time-series storage)

**AI / Orchestration**
- Langflow (Docker)
- MCP server (tools for LLM)
- MCP proxy (Host/SSE compatibility)

**Frontend**
- Next.js (React)
- Dashboard UI (plant diagram, charts, KPI, recommendation cards)

**DevOps / Collaboration**
- Docker (Langflow runtime)
- Git (version control)

---

## Notes
- Plant selection via `X-Plant-ID` header (fallback default plant e.g., P2)
- Supports snapshot + history queries for UI and decision logic
