# CLAUDE.md - Council of Maniacs

## Project Overview

Council of Maniacs is a 3-stage deliberation system where 8 wildly unhinged AI personas (all powered by the same model via different system prompts) debate user questions. A sane moderator then extracts useful insights from the chaos.

Fork lineage: inspired by karpathy/llm-council, but uses one model with persona system prompts instead of multiple different models.

## Architecture

### Backend (`backend/`)

**`config.py`**
- `COUNCIL_MEMBERS`: List of 8 persona dicts, each with `id`, `name`, `tagline`, `system_prompt`
- `BASE_MODEL`: Single model used for all personas (env var, defaults to `google/gemini-2.5-flash`)
- `CHAIRMAN_MODEL`: Model for the moderator synthesis step
- Uses `OPENROUTER_API_KEY` from `.env`
- Backend runs on **port 8001**

**`openrouter.py`**
- `query_model()`: Raw model query (used by moderator)
- `query_persona()`: Sends system prompt + user message to a model
- `query_personas_parallel()`: Fires all 8 personas in parallel against the same model

**`council.py`** - Core 3-stage logic
- `stage1_collect_responses()`: All personas respond in character
- `stage2_collect_rankings()`: Anonymized peer review, each persona ranks in character
- `stage3_synthesize_final()`: Moderator synthesizes from chaos
- `parse_ranking_from_text()` / `calculate_aggregate_rankings()`: Ranking extraction
- Response dicts use `member_id` and `name` instead of `model`

**`storage.py`** - JSON conversation storage in `data/conversations/`

**`main.py`** - FastAPI with SSE streaming. Extra endpoint: `GET /api/members` returns the council roster.

### Frontend (`frontend/src/`)

- **Stage1.jsx**: Tabs showing each persona's response with name + tagline
- **Stage2.jsx**: In-character peer evaluations with de-anonymization and aggregate rankings
- **Stage3.jsx**: Moderator's verdict
- **ChatInterface.jsx**: Main chat UI with streaming stage progression
- **Sidebar.jsx**: Conversation list

### Key Design Decisions

- **One model, many personas**: All council members use the same LLM. Personality differences come entirely from system prompts. This is the core twist vs the original llm-council.
- **In-character ranking**: Stage 2 evaluations use each persona's system prompt, so The Doomsayer ranks pessimistically, The Hype Machine ranks optimistically, etc.
- **Moderator is separate**: The moderator has its own prompt focused on extracting genuine insight from the chaos.

### Ports
- Backend: 8001
- Frontend: 5173 (Vite)

### Running
- Backend: `uv run python -m backend.main` from project root
- Frontend: `cd frontend && npm run dev`
- Both: `./start.sh`

### The 8 Personas
1. **The Contrarian** - Argues against conventional wisdom
2. **The Eccentric Professor** - Nonlinear genius with wild tangents
3. **The Wild Card** - Only proposes radical unconventional solutions
4. **The Doomsayer** - Extreme pessimist, sees catastrophic failure everywhere
5. **The Hype Machine** - Extreme optimist, everything is a game-changer
6. **The Conspiracy Theorist** - Sees hidden agendas behind everything
7. **The Absurdist** - Seeks the most comically impractical solutions
8. **The Overengineer** - Enterprise-grade solutions for trivial problems
