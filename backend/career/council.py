"""Career track council orchestration — runs the 3-stage pipeline for career ideation."""

import asyncio
from typing import List, Dict, Any, Tuple

from ..config import COUNCIL_MEMBERS, BASE_MODEL, CHAIRMAN_MODEL
from ..openrouter import query_personas_parallel, query_model
from ..council import parse_ranking_from_text, calculate_aggregate_rankings, get_member_by_id
from .config import CAREER_PERSONA_OVERLAYS, MODERATOR_CAREER_PROMPT, MODES


def build_career_personas(mode: str) -> List[Dict[str, Any]]:
    """Build career-specific personas by overlaying career prompts onto base personas."""
    mode_config = MODES[mode]
    mode_label = mode_config["label"].lower()
    personas = []
    for member in COUNCIL_MEMBERS:
        overlay = CAREER_PERSONA_OVERLAYS.get(member["id"], "")
        overlay_formatted = overlay.format(mode_label=mode_label)
        career_prompt = f"{overlay_formatted}\n\n{member['system_prompt']}"
        personas.append({**member, "system_prompt": career_prompt})
    return personas


def build_user_context(background: str) -> str:
    """Format the user's professional background into a structured prompt."""
    return (
        "Here is the person's professional background, resume, and any other context they've provided. "
        "Study it carefully — your suggestions must connect to their ACTUAL skills, experience, and interests.\n\n"
        f"--- BACKGROUND ---\n{background}\n--- END BACKGROUND ---\n\n"
        "Now, based on this background, propose your most in-character suggestions. "
        "Each suggestion should:\n"
        "- Have a catchy name/title\n"
        "- Explain the core concept\n"
        "- Explain specifically how it connects to this person's background\n"
        "- Include any other details that fit your persona's style\n\n"
        "Propose 3-5 ideas."
    )


async def career_stage1(background: str, mode: str) -> List[Dict[str, Any]]:
    """Stage 1: Each maniac generates career ideas in character."""
    personas = build_career_personas(mode)
    user_message = build_user_context(background)
    responses = await query_personas_parallel(BASE_MODEL, personas, user_message)

    results = []
    for member in COUNCIL_MEMBERS:
        resp = responses.get(member["id"])
        if resp is not None:
            results.append({
                "member_id": member["id"],
                "name": member["name"],
                "tagline": member["tagline"],
                "response": resp.get("content", ""),
            })
    return results


async def career_stage2(
    background: str,
    mode: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Stage 2: Each maniac ranks the others' ideas in character."""
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_member = {
        f"Response {label}": result["member_id"]
        for label, result in zip(labels, stage1_results)
    }

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    mode_config = MODES[mode]
    ranking_prompt = f"""You are evaluating different sets of {mode_config['label'].lower()} ideas proposed for someone with this background:

{background}

Here are the proposals from different council members (anonymized):

{responses_text}

Your task:
1. Evaluate each set of proposals. Which ideas are actually viable given this person's background? Which are pure fantasy? Stay in character.
2. Then provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")

Now provide your in-character evaluation and ranking:"""

    personas = build_career_personas(mode)
    active_personas = [p for p in personas if p["id"] in [r["member_id"] for r in stage1_results]]
    ranking_results = await query_personas_parallel(BASE_MODEL, active_personas, ranking_prompt)

    stage2_results = []
    for member in COUNCIL_MEMBERS:
        resp = ranking_results.get(member["id"])
        if resp is not None:
            full_text = resp.get("content", "")
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "member_id": member["id"],
                "name": member["name"],
                "ranking": full_text,
                "parsed_ranking": parsed,
            })

    return stage2_results, label_to_member


async def career_stage3(
    background: str,
    mode: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Stage 3: Moderator synthesizes actionable career ideas from the chaos."""
    mode_config = MODES[mode]

    stage1_text = "\n\n".join([
        f"{r['name']} ({r['tagline']}):\n{r['response']}" for r in stage1_results
    ])
    stage2_text = "\n\n".join([
        f"{r['name']}:\n{r['ranking']}" for r in stage2_results
    ])

    moderator_prompt = MODERATOR_CAREER_PROMPT.format(
        mode_label=mode_config["label"].lower(),
        moderator_focus=mode_config["moderator_focus"],
    )

    user_prompt = f"""The Council of Maniacs — Career Division has reviewed the following professional background:

{background}

MODE: {mode_config['label']}

STAGE 1 — Individual Maniac Proposals:
{stage1_text}

STAGE 2 — Peer Rankings (each maniac ranked the others, in character):
{stage2_text}

Now synthesize your final report. Extract the genuinely viable {mode_config['moderator_focus']} from the chaos. Rank your top picks and provide actionable next steps for each."""

    messages = [
        {"role": "system", "content": moderator_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = await query_model(CHAIRMAN_MODEL, messages)
    if response is None:
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: The Moderator couldn't wrangle this mess. Try again.",
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get("content", ""),
    }


async def run_career_council(background: str, mode: str) -> Dict[str, Any]:
    """Run the full 3-stage career council pipeline. Returns all results."""
    if mode not in MODES:
        raise ValueError(f"Unknown mode '{mode}'. Valid modes: {list(MODES.keys())}")

    stage1_results = await career_stage1(background, mode)
    if not stage1_results:
        return {
            "mode": mode,
            "stage1": [],
            "stage2": [],
            "stage3": {"model": "error", "response": "All maniacs failed to respond."},
            "metadata": {},
        }

    stage2_results, label_to_member = await career_stage2(background, mode, stage1_results)
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_member)
    stage3_result = await career_stage3(background, mode, stage1_results, stage2_results)

    return {
        "mode": mode,
        "mode_label": MODES[mode]["label"],
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": {
            "label_to_member": label_to_member,
            "aggregate_rankings": aggregate_rankings,
        },
    }
