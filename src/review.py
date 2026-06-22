"""Manual review adjustment helpers."""

from __future__ import annotations

import pandas as pd


APPROVE_SUGGESTED_ASSIGNMENT = "Approve suggested assignment"
CHANGE_CARDHOLDER = "Change cardholder"
KEEP_IN_NEED_REVIEW = "Keep in Need Review"
MARK_AS_UNMATCHED = "Mark as Unmatched"

APPROVED_SUGGESTION_NOTE = "Approved suggested assignment in Streamlit review."
MANUAL_CARDHOLDER_CHANGE_NOTE = "Manually changed cardholder in Streamlit review."
MANUAL_UNMATCHED_NOTE = "Marked as unmatched during Streamlit review."


def default_review_action(row: pd.Series) -> str:
    """Choose the friendliest default action for a review row."""
    suggested_cardholder = str(row.get("Cardholder name", "") or "").strip()
    if suggested_cardholder:
        return APPROVE_SUGGESTED_ASSIGNMENT
    return KEEP_IN_NEED_REVIEW


def apply_review_decisions(
    results_df: pd.DataFrame,
    decisions: dict[int, dict[str, str]],
) -> pd.DataFrame:
    """Apply Streamlit review decisions to a matched results DataFrame."""
    reviewed = results_df.copy()

    for row_index, decision in decisions.items():
        if row_index not in reviewed.index:
            continue

        action = decision.get("action", KEEP_IN_NEED_REVIEW)
        cardholder_name = decision.get("cardholder_name", "")
        suggested_cardholder = decision.get("suggested_cardholder_name", "")

        if action == APPROVE_SUGGESTED_ASSIGNMENT and suggested_cardholder:
            reviewed.loc[row_index, "Cardholder name"] = suggested_cardholder
            reviewed.loc[row_index, "Match confidence"] = "Manual"
            reviewed.loc[row_index, "Match note"] = APPROVED_SUGGESTION_NOTE
        elif action == CHANGE_CARDHOLDER and cardholder_name:
            reviewed.loc[row_index, "Cardholder name"] = cardholder_name
            reviewed.loc[row_index, "Match confidence"] = "Manual"
            reviewed.loc[row_index, "Match note"] = MANUAL_CARDHOLDER_CHANGE_NOTE
        elif action == MARK_AS_UNMATCHED:
            reviewed.loc[row_index, "Cardholder name"] = ""
            reviewed.loc[row_index, "Match confidence"] = "Unmatched"
            reviewed.loc[row_index, "Match note"] = MANUAL_UNMATCHED_NOTE

    return reviewed
