"""
Logger module for PostXG pipeline runs.
Handles all Supabase logging via the pipeline_runs table.
"""

import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def _get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def log_pipeline_start(
    interface: str,
    sources_count: int,
    grok_used: bool,
    youtube_count: int,
    manual_count: int,
) -> str:
    """
    Insert a new row into pipeline_runs to mark the start of a pipeline run.

    Args:
        interface: The interface used to trigger the run ('terminal', 'telegram', or 'streamlit').
        sources_count: Total number of input sources provided.
        grok_used: Whether Grok was used to fetch live news.
        youtube_count: Number of YouTube transcript sources.
        manual_count: Number of manually provided sources.

    Returns:
        run_id: The UUID of the newly created pipeline_runs row.

    Raises:
        Exception: If the Supabase insert fails.
    """
    try:
        client = _get_client()
        row = {
            "status": "in_progress",
            "interface": interface,
            "input_sources_count": sources_count,
            "grok_used": grok_used,
            "youtube_count": youtube_count,
            "manual_count": manual_count,
        }
        response = client.table("pipeline_runs").insert(row).execute()
        run_id = response.data[0]["run_id"]
        return run_id
    except Exception as e:
        raise Exception(f"log_pipeline_start failed: {e}") from e


def log_pipeline_update(run_id: str, update_data: dict) -> None:
    """
    Update an existing pipeline_runs row with new data mid-run.

    Useful for writing intermediate results such as extraction costs, brief
    costs, router classification, or any other fields as they become available.

    Args:
        run_id: UUID of the pipeline_runs row to update.
        update_data: Dict of column names to values to write. Any column from
                     the pipeline_runs table is valid (e.g. extraction_model,
                     extraction_tokens_in, content_type, router_confidence, ...).

    Raises:
        Exception: If the Supabase update fails.
    """
    try:
        client = _get_client()
        client.table("pipeline_runs").update(update_data).eq("run_id", run_id).execute()
    except Exception as e:
        raise Exception(f"log_pipeline_update failed for run_id={run_id}: {e}") from e


def log_eval_result(
    run_id: str,
    attempt_number: int,
    eval_model: str,
    tokens_in: int,
    tokens_out: int,
    eval_cost_usd: float,
    accuracy_score: int,
    relevance_score: int,
    hallucination_risk: str,
    passed: bool,
    flagged_claims: list,
    eval_reasoning: str,
) -> str:
    """
    Insert a row into eval_results for a single evaluation attempt.

    Args:
        run_id: UUID of the parent pipeline_runs row.
        attempt_number: Which eval attempt this is (1-indexed).
        eval_model: Model used for evaluation.
        tokens_in: Input token count.
        tokens_out: Output token count.
        eval_cost_usd: Cost of this eval call in USD.
        accuracy_score: 0-100 accuracy score.
        relevance_score: 0-100 relevance score.
        hallucination_risk: 'low', 'medium', or 'high'.
        passed: Whether the brief passed the eval threshold.
        flagged_claims: List of problematic statements identified.
        eval_reasoning: Explanation of the scores.

    Returns:
        eval_id: UUID of the newly created eval_results row.

    Raises:
        Exception: If the Supabase insert fails.
    """
    try:
        client = _get_client()
        row = {
            "run_id": run_id,
            "attempt_number": attempt_number,
            "eval_model": eval_model,
            "eval_tokens_in": tokens_in,
            "eval_tokens_out": tokens_out,
            "eval_cost_usd": eval_cost_usd,
            "accuracy_score": accuracy_score,
            "relevance_score": relevance_score,
            "hallucination_risk": hallucination_risk,
            "passed": passed,
            "flagged_claims": flagged_claims,
            "eval_reasoning": eval_reasoning,
        }
        response = client.table("eval_results").insert(row).execute()
        return response.data[0]["eval_id"]
    except Exception as e:
        raise Exception(f"log_eval_result failed for run_id={run_id}: {e}") from e


def log_pipeline_complete(run_id: str, final_data: dict) -> None:
    """
    Mark a pipeline run as completed and write final output metadata.

    Sets status to 'completed', records the completed_at timestamp, and
    merges any additional fields supplied in final_data (e.g. total_cost_usd,
    brief_output, format_type, output_length_chars, output_length_words).

    Args:
        run_id: UUID of the pipeline_runs row to finalise.
        final_data: Dict of column names to values for the final update.
                    total_cost_usd should be included here if known.

    Raises:
        Exception: If the Supabase update fails.
    """
    try:
        client = _get_client()
        payload = {
            **final_data,
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        client.table("pipeline_runs").update(payload).eq("run_id", run_id).execute()
    except Exception as e:
        raise Exception(f"log_pipeline_complete failed for run_id={run_id}: {e}") from e
