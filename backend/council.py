"""3-stage Council of Maniacs orchestration."""

import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict

from .openrouter import query_personas_parallel, query_model, query_persona
from .config import COUNCIL_MEMBERS, BASE_MODEL, CHAIRMAN_MODEL


def get_member_by_id(member_id: str) -> Dict[str, Any]:
    """Look up a council member by id."""
    for m in COUNCIL_MEMBERS:
        if m["id"] == member_id:
            return m
    return {"id": member_id, "name": member_id, "tagline": "", "system_prompt": ""}


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Each maniac responds to the query in character.

    Returns:
        List of dicts with 'member_id', 'name', 'tagline', and 'response'
    """
    responses = await query_personas_parallel(BASE_MODEL, COUNCIL_MEMBERS, user_query)

    stage1_results = []
    for member in COUNCIL_MEMBERS:
        resp = responses.get(member["id"])
        if resp is not None:
            stage1_results.append({
                "member_id": member["id"],
                "name": member["name"],
                "tagline": member["tagline"],
                "response": resp.get("content", ""),
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each maniac ranks the others' anonymized responses (in character).

    Returns:
        Tuple of (rankings list, label_to_member mapping)
    """
    labels = [chr(65 + i) for i in range(len(stage1_results))]

    label_to_member = {
        f"Response {label}": result["member_id"]
        for label, result in zip(labels, stage1_results)
    }

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_user_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different council members (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly — stay fully in character while doing so.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Now provide your in-character evaluation and ranking:"""

    # Each maniac evaluates in character using their own system prompt
    ranking_results = await query_personas_parallel(
        BASE_MODEL,
        [
            {**member, "system_prompt": member["system_prompt"]}
            for member in COUNCIL_MEMBERS
            if member["id"] in [r["member_id"] for r in stage1_results]
        ],
        ranking_user_prompt
    )

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


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: The Moderator synthesizes a final answer from the chaos.
    """
    stage1_text = "\n\n".join([
        f"{result['name']} ({result['tagline']}):\n{result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"{result['name']}:\n{result['ranking']}"
        for result in stage2_results
    ])

    moderator_prompt = (
        "You are the Moderator of the Council of Maniacs — a deliberation body made up of "
        "wildly unhinged personas: a contrarian, an eccentric professor, a wild-card creative, "
        "a doomsayer, a hype machine, a conspiracy theorist, an absurdist, and an overengineer. "
        "Your job is to read all of their unhinged responses and peer evaluations, then distill "
        "something genuinely useful from the chaos. Find the hidden gems of insight buried in "
        "the madness. Be honest about which maniacs actually had a point and which were just "
        "ranting. Your final synthesis should be practical, clear, and actually helpful — but "
        "feel free to acknowledge the entertainment value of the council's wilder suggestions."
    )

    user_prompt = f"""The Council of Maniacs has deliberated on the following question:

Question: {user_query}

STAGE 1 — Individual Maniac Responses:
{stage1_text}

STAGE 2 — Peer Rankings (each maniac ranked the others, in character):
{stage2_text}

Now synthesize a final, actually-useful answer. Highlight which maniacs made surprisingly good points, which were entertainingly wrong, and what the user should actually take away from this circus."""

    messages = [
        {"role": "system", "content": moderator_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: The Moderator couldn't make sense of this mess. Try again.",
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get("content", ""),
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """Parse the FINAL RANKING section from a maniac's evaluation."""
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_member: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Calculate aggregate rankings across all maniac evaluations."""
    member_positions = defaultdict(list)

    for ranking in stage2_results:
        parsed_ranking = parse_ranking_from_text(ranking["ranking"])
        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_member:
                member_id = label_to_member[label]
                member = get_member_by_id(member_id)
                member_positions[member["name"]].append(position)

    aggregate = []
    for name, positions in member_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "name": name,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions),
            })

    aggregate.sort(key=lambda x: x["average_rank"])
    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """Generate a short title for a conversation."""
    title_prompt = (
        "Generate a very short title (3-5 words maximum) that summarizes the following question. "
        "The title should be concise and descriptive. Do not use quotes or punctuation in the title.\n\n"
        f"Question: {user_query}\n\nTitle:"
    )

    messages = [{"role": "user", "content": title_prompt}]
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        return "New Conversation"

    title = response.get("content", "New Conversation").strip().strip("\"'")
    if len(title) > 50:
        title = title[:47] + "..."
    return title


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """Run the complete 3-stage Council of Maniacs process."""
    stage1_results = await stage1_collect_responses(user_query)

    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All maniacs failed to respond. Even they have limits.",
        }, {}

    stage2_results, label_to_member = await stage2_collect_rankings(
        user_query, stage1_results
    )

    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_member)

    stage3_result = await stage3_synthesize_final(
        user_query, stage1_results, stage2_results
    )

    metadata = {
        "label_to_member": label_to_member,
        "aggregate_rankings": aggregate_rankings,
    }

    return stage1_results, stage2_results, stage3_result, metadata
