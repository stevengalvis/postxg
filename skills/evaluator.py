"""
Evaluator module for PostXG pipeline briefs.
Uses Claude Haiku to score a generated brief against its source research,
then logs results to the eval_results Supabase table.
"""

import os
import json
import anthropic
from dotenv import load_dotenv
from skills.logger import log_eval_result

load_dotenv()

# Claude 3.5 Haiku pricing (per token)
_HAIKU_COST_PER_INPUT_TOKEN = 0.80 / 1_000_000
_HAIKU_COST_PER_OUTPUT_TOKEN = 4.00 / 1_000_000

EVAL_MODEL = "claude-haiku-4-5-20251001"

EVAL_SYSTEM_PROMPT = """You are a strict fact-checker for a football YouTube channel.

Your job is to evaluate a video brief against the research sources it was built from.
You must check every claim, stat, quote, and assertion in the brief.

EVALUATION CRITERIA:
- accuracy_score (0-100): How accurate are the claims? Deduct points for any stat, fact, or claim that is wrong, exaggerated, or contradicts the research.
- relevance_score (0-100): How relevant is the brief to the research topic? Deduct points if the brief goes off-topic or misses the central story.
- hallucination_risk ('low', 'medium', 'high'):
    low = all claims are clearly supported by the research
    medium = some claims are vague, stretched, or unverifiable from the research
    high = one or more claims appear invented or directly contradict the research
- flagged_claims: A list of specific statements from the brief that are problematic. Quote the exact text.
- eval_reasoning: A clear explanation of your scores and what you found.

RULES:
- Only use the research provided. Do not use outside knowledge to verify claims.
- If a claim is not in the research, flag it — even if it might be true.
- Be strict. This content will be published to a large audience.
- Return ONLY valid JSON. No preamble, no markdown, no code fences.

OUTPUT FORMAT (strict JSON, nothing else):
{
  "accuracy_score": <integer 0-100>,
  "relevance_score": <integer 0-100>,
  "hallucination_risk": "<low|medium|high>",
  "flagged_claims": ["<claim 1>", "<claim 2>"],
  "eval_reasoning": "<explanation>"
}"""


def evaluate_brief(
    brief_text: str,
    research_sources: str,
    run_id: str,
    attempt_number: int = 1,
) -> dict:
    """
    Evaluate a generated brief against its research sources using Claude Haiku.

    Calls the eval model, parses the JSON response, applies the pass/fail
    threshold, logs the result to the eval_results table, and returns the
    full result dict including a 'passed' boolean.

    Pass threshold:
        accuracy_score >= 85 AND relevance_score >= 80 AND hallucination_risk != 'high'

    Args:
        brief_text: The generated brief to evaluate.
        research_sources: The raw research the brief was built from.
        run_id: UUID of the parent pipeline_runs row (used for Supabase logging).
        attempt_number: Which eval attempt this is (default 1). Increment on retries.

    Returns:
        dict with keys:
            accuracy_score, relevance_score, hallucination_risk,
            flagged_claims, eval_reasoning, passed,
            eval_tokens_in, eval_tokens_out, eval_cost_usd

    Raises:
        Exception: If the Claude API call fails or returns unparseable JSON.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_message = f"""RESEARCH SOURCES:
{research_sources}

BRIEF TO EVALUATE:
{brief_text}

Check every claim in the brief against the research sources above. Return your evaluation as JSON."""

    try:
        response = client.messages.create(
            model=EVAL_MODEL,
            max_tokens=1024,
            system=EVAL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as e:
        raise Exception(f"Claude API call failed in evaluate_brief: {e}") from e

    raw_text = response.content[0].text
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    eval_cost = (tokens_in * _HAIKU_COST_PER_INPUT_TOKEN) + (tokens_out * _HAIKU_COST_PER_OUTPUT_TOKEN)

    try:
        # Strip markdown code fences if present
        clean_text = raw_text.strip()
        if clean_text.startswith('```json'):
            clean_text = clean_text[7:]  # Remove ```json
        if clean_text.startswith('```'):
            clean_text = clean_text[3:]   # Remove ```
        if clean_text.endswith('```'):
            clean_text = clean_text[:-3]  # Remove trailing ```
        clean_text = clean_text.strip()

        scores = json.loads(clean_text)
    except json.JSONDecodeError as e:
        raise Exception(f"evaluate_brief: could not parse JSON from eval response: {e}\nCleaned response:\n{clean_text}") from e

    passed = (
        scores["accuracy_score"] >= 85
        and scores["relevance_score"] >= 80
        and scores["hallucination_risk"] != "high"
    )

    try:
        log_eval_result(
            run_id=run_id,
            attempt_number=attempt_number,
            eval_model=EVAL_MODEL,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            eval_cost_usd=round(eval_cost, 6),
            accuracy_score=scores["accuracy_score"],
            relevance_score=scores["relevance_score"],
            hallucination_risk=scores["hallucination_risk"],
            passed=passed,
            flagged_claims=scores.get("flagged_claims", []),
            eval_reasoning=scores.get("eval_reasoning", ""),
        )
    except Exception as e:
        # Log failure is non-fatal — return the result even if Supabase write fails
        print(f"Warning: eval result could not be logged to Supabase: {e}")

    return {
        "accuracy_score": scores["accuracy_score"],
        "relevance_score": scores["relevance_score"],
        "hallucination_risk": scores["hallucination_risk"],
        "flagged_claims": scores.get("flagged_claims", []),
        "eval_reasoning": scores.get("eval_reasoning", ""),
        "passed": passed,
        "eval_tokens_in": tokens_in,
        "eval_tokens_out": tokens_out,
        "eval_cost_usd": round(eval_cost, 6),
    }
