# Council of Maniacs

A deliberation system where 8 wildly unhinged AI personas debate your questions. Same model, different system prompts, maximum chaos.

Inspired by [karpathy/llm-council](https://github.com/karpathy/llm-council), but instead of serious multi-model consensus, this is a council of maniacs arguing with each other in character — then a sane moderator extracts whatever wisdom survived.

![Header](header.jpg)

## The Council

| Persona | Role |
|---------|------|
| **The Contrarian** | Whatever you think, I think the opposite. |
| **The Eccentric Professor** | Brilliant but... what planet are they on? |
| **The Wild Card** | Only the craziest ideas survive. |
| **The Doomsayer** | Everything is terrible and getting worse. |
| **The Hype Machine** | This is going to change EVERYTHING! |
| **The Conspiracy Theorist** | That's exactly what THEY want you to think. |
| **The Absurdist** | Why not solve it with a trained pelican? |
| **The Overengineer** | We'll need a microservices architecture for that. |

## How It Works

**Stage 1 — The Maniacs Respond**: Your question goes to all 8 personas in parallel. Each responds fully in character.

**Stage 2 — The Maniacs Judge Each Other**: Responses are anonymized and each persona ranks the others — still in character. The Doomsayer explains why every answer will end in disaster. The Conspiracy Theorist sees hidden agendas in the rankings.

**Stage 3 — The Moderator's Verdict**: A sane moderator reads all the chaos and distills a genuinely useful answer, calling out which maniacs actually had a point.

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- An [OpenRouter](https://openrouter.ai/) API key

### Install

```bash
# Backend
uv sync

# Frontend
cd frontend && npm install
```

### Configure

Create a `.env` file in the project root:

```
OPENROUTER_API_KEY=your-key-here
BASE_MODEL=google/gemini-2.5-flash
CHAIRMAN_MODEL=google/gemini-2.5-flash
```

`BASE_MODEL` is the single model used for all 8 personas (via system prompts). `CHAIRMAN_MODEL` is used for the final moderator synthesis. Both default to Gemini 2.5 Flash if not set.

### Run

```bash
./start.sh
```

- Backend: http://localhost:8001
- Frontend: http://localhost:5173

## Career Division

The Career Division is a headless track (no frontend) where the 8 maniacs review a professional background and generate ideas across three modes:

- **Side Hustles** — Absurd side hustle ideas based on your skills
- **Career Pivots** — Radical career pivot proposals
- **Business Ideas** — Absurd but weirdly plausible business concepts

Each run goes through the full 3-stage pipeline (ideation, peer review, moderator synthesis) and outputs a PDF report.

```bash
# Write your background to a file, then:
uv run python -m backend.career.cli side-hustles -f background.txt
uv run python -m backend.career.cli career-pivots -f background.txt
uv run python -m backend.career.cli business-ideas -f background.txt
```

### Example Reports

These were generated from a real professional background ([danielrosehill.com](https://danielrosehill.com)):

- [Absurd Side Hustles (PDF)](examples/career-reports/career-side-hustles-20260410-191426.pdf) — 62 pages of unhinged income streams
- [Unhinged Career Pivots (PDF)](examples/career-reports/career-career-pivots-20260410-191427.pdf) — 55 pages of radical career reinvention

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, OpenRouter API
- **Frontend:** React + Vite, react-markdown
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv (Python), npm (JavaScript)
