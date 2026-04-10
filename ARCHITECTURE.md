# Architecture

This document describes the internal structure of the RPS Observer system.

## Project Layout

```
rps_observer/
├── backend/                    # FastAPI backend (Python)
│   ├── app/
│   │   ├── main.py             # App entry, CORS, route registration
│   │   ├── core/config.py      # Settings and environment variables
│   │   ├── api/v1/             # REST route handlers
│   │   ├── domain/             # Core business logic
│   │   ├── services/           # External service integrations
│   │   └── schemas/            # Pydantic request/response models
│   ├── requirements.txt
│   ├── env.example
│   └── Dockerfile
├── src/                        # React + Vite frontend
│   ├── components/
│   │   ├── RPSCalculator.jsx
│   │   └── ObserverDemo.jsx
│   └── lib/api.js
├── experiments/results/        # Experiment result charts
├── scripts/                    # Utility and experiment scripts
├── vite.config.js
└── package.json
```

---

## Backend (`backend/`)

### Entry Point — `app/main.py`

- Creates the FastAPI application
- Registers CORS middleware (all origins allowed for development)
- Mounts all API routers under `/api/v1`
- Exposes `GET /health` health check

### Configuration — `app/core/config.py`

Loads environment variables from `backend/.env` via `python-dotenv`.

Key settings:

| Variable | Description |
|----------|-------------|
| `MODEL_PROVIDER` | Active LLM provider (`openai`, `deepseek-official`, `deepseek-reasoner`, `gemini-2.5-pro`, `claude-3-7-sonnet-20250219`, `openrouter`) |
| `OPENAI_API_KEY` | OpenAI key (supports `_2`, `_3` suffixes for key rotation) |
| `DEEPSEEK_API_KEY` | DeepSeek key |
| `GEMINI_API_KEY` | Google Gemini key |
| `ANTHROPIC_API_KEY` | Anthropic Claude key |
| `OPENROUTER_API_KEY` | OpenRouter key |
| `USE_DYNAMIC_STRATEGIES` | Enable X/Y/Z strategies (default: `1`) |
| `LLM_LOG_PROMPT` | Log full prompts to disk (`0`/`1`) |
| `LLM_LOG_DIR` | Directory for prompt logs |

---

### API Layer (`app/api/v1/`)

| File | Endpoint(s) | Description |
|------|------------|-------------|
| `routes_observer.py` | `POST /observer/run`, `GET /observer/stream` | Core observer: run experiment, stream SSE results |
| `routes_simulate.py` | `POST /simulate` | Simulate strategy matchup for N rounds |
| `routes_strategies.py` | `GET /strategies/all`, `POST /strategies/matchup`, `POST /strategies/matrix` | Strategy list and win/loss calculations |
| `routes_player.py` | `POST /player/act` | Determine next move for a given strategy |
| `routes_eval.py` | `POST /evaluate` | Compute evaluation metrics |
| `routes_admin.py` | Admin/utility | Admin endpoints |

---

### Domain Layer (`app/domain/`)

#### `strategies.py` — Strategy Definitions and Calculations

Defines all 19 RPS strategies and the core game-theory logic.

**Static strategies (A–P):** Fixed probability distributions.

| Code | Name | Rock | Paper | Scissors |
|------|------|------|-------|----------|
| A | Pure Scissors | 0 | 0 | 1 |
| B | Pure Rock | 1 | 0 | 0 |
| C | Pure Paper | 0 | 1 | 0 |
| D | Random | 1/3 | 1/3 | 1/3 |
| E | Rock+Paper | 0.5 | 0.5 | 0 |
| F | Rock+Scissors | 0.5 | 0 | 0.5 |
| G | Paper+Scissors | 0 | 0.5 | 0.5 |
| H | Rock-biased | 0.5 | 0.25 | 0.25 |
| I | Paper-biased | 0.25 | 0.5 | 0.25 |
| J | Scissors-biased | 0.25 | 0.25 | 0.5 |
| K | Rock>Paper | 0.5 | 0.333 | 0.167 |
| L | Rock>Scissors | 0.5 | 0.167 | 0.333 |
| M | Paper>Rock | 0.333 | 0.5 | 0.167 |
| N | Paper>Scissors | 0.167 | 0.5 | 0.333 |
| O | Scissors>Rock | 0.333 | 0.167 | 0.5 |
| P | Scissors>Paper | 0.167 | 0.333 | 0.5 |

**Dynamic strategies (X/Y/Z):** Respond to opponent's last move.

| Code | Name | Rule |
|------|------|------|
| X | Win vs last | Play the move that beats the opponent's last move |
| Y | Lose vs last | Play the move that loses to the opponent's last move |
| Z | Follow last | Copy the opponent's last move |

Key functions:

| Function | Description |
|----------|-------------|
| `resolve_dist(key, opp_dist)` | Returns a strategy's distribution given opponent's last distribution |
| `iterate_dists(k1, k2, iters=50)` | Iterates to find steady-state distributions for two dynamic strategies |
| `calculate_matchup(s1, s2)` | Computes expected win/loss/draw percentages |
| `get_all_strategies()` | Returns the full strategy dictionary |

#### `metrics.py` — Evaluation Metrics

| Function | Metric |
|----------|--------|
| `compute_cross_entropy_loss()` | CE loss between true and predicted distributions |
| `compute_brier_score()` | Brier score |
| `compute_ev_loss()` | Expected value loss |
| `compute_union_loss()` | Average of CE, Brier, EV |
| `normalize_loss()` | Min-max normalization relative to full matrix |
| `compute_all_losses_for_matrix()` | Compute losses across entire strategy matrix |

#### `simulator.py` — Game Simulator

| Function | Description |
|----------|-------------|
| `play_round(s1_dist, s2_dist)` | Execute one round given two strategy distributions |
| `simulate(strategy1, strategy2, rounds)` | Run multi-round simulation |

---

### Services (`app/services/`)

#### `llm.py` — LLM Integration

`identify_from_history(history, model, ...)` is the main entry point. It:

1. Constructs a prompt describing the observed game history
2. Lists all 19 possible strategies with descriptions
3. Asks the LLM to identify the most likely strategy for each player and report confidence
4. Parses the structured response

Supported providers: OpenAI, DeepSeek (official + reasoner), Gemini, Anthropic Claude, OpenRouter.

#### `api_key_manager.py` — Key Rotation

Rotates between multiple keys of the same provider (e.g. `OPENAI_API_KEY`, `OPENAI_API_KEY_2`, `OPENAI_API_KEY_3`) to handle rate limits.

---

### Schemas (`app/schemas/`)

| File | Models |
|------|--------|
| `observer.py` | `ObserverRunReq`, `ObserverRunResp`, per-round result models |
| `simulate.py` | `SimulateRequest/Response`, `StrategyMatchupRequest/Response`, `StrategyMatrixRequest/Response` |
| `player.py` | `PlayerActReq/Resp` |
| `evaluate.py` | `EvaluateRequest/Response` |

---

## Frontend (`src/`)

The frontend is React 19 + Vite 7, styled with Tailwind CSS. Vite proxies all `/api/*` requests to the backend at `http://127.0.0.1:8002`.

### Components

#### `RPSCalculator.jsx`

Interactive strategy matrix calculator. Runs entirely client-side.

- Select any two strategies to see their expected win/loss/draw percentages
- Choose a "Predicted" strategy pair and compute CE, Brier, EV, and Union Loss against every cell in the 19×19 matrix
- Color-coded matrix visualization (win rate or normalized loss mode)
- Implements the same `iterateDists` logic as the backend for dynamic strategy steady-states

#### `ObserverDemo.jsx`

Live observer experiment interface.

- Configure model, rounds, warmup, history limit, reasoning interval
- Start an experiment and receive results via SSE streaming (`GET /api/v1/observer/stream`)
- SVG line chart showing Union Loss trend over rounds (custom, no charting library dependency)
- Table of per-round strategy guesses and confidence

### API Client — `src/lib/api.js`

Wraps all backend endpoints with consistent error handling. Key functions: `simulate`, `observerRun`, `openObserverStream`, `getAllStrategies`, `calculateStrategyMatchup`, `calculateStrategyMatrix`, `evaluate`.

---

## Data Flow

### Observer Experiment

```
ObserverDemo (UI)
  │  POST /api/v1/observer/run  (or GET /stream for SSE)
  ▼
routes_observer.py
  │  for each round:
  │    simulator.py → play_round()        # generate actual moves
  │    llm.py → identify_from_history()   # LLM identifies strategy
  │    metrics.py → compute_all_losses()  # evaluate prediction
  ▼
Returns per_round[] + final_guess + trend statistics
```

### Strategy Matrix

```
RPSCalculator (UI)
  │  (client-side only, no API call)
  ▼
calculateMatchup() for all 19×19 pairs
  │  Static × Static → direct distribution multiplication
  │  Static × Dynamic → resolve_dist(dynamic, static_dist)
  │  Dynamic × Dynamic → iterateDists(50 iterations)
  ▼
Loss computation for each cell vs. selected Pred A/B
  ▼
Color-coded matrix render
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI 0.116 |
| Data validation | Pydantic v2 |
| Numerical computing | NumPy, SciPy |
| LLM clients | openai, anthropic, google-genai, httpx |
| Frontend framework | React 19 |
| Build tool | Vite 7 |
| Styling | Tailwind CSS 4 |
| Data export | openpyxl |

---

## Extending the System

**Add a new strategy:**
1. Add to `BASE_STRATEGIES` or `DYNAMIC_STRATEGIES` in `backend/app/domain/strategies.py`
2. Mirror the definition in `src/components/RPSCalculator.jsx` (`baseStrategies` object)

**Add a new LLM provider:**
1. Add provider handling in `backend/app/services/llm.py`
2. Add the corresponding API key variable in `backend/app/core/config.py` and `backend/env.example`

**Add a new API endpoint:**
1. Create a route file in `backend/app/api/v1/`
2. Define request/response models in `backend/app/schemas/`
3. Register the router in `backend/app/main.py`
4. Add the client function in `src/lib/api.js`
