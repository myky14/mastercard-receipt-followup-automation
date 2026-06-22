"""Manual review adjustment helpers."""

from __future__ import annotations

import pandas as pd


ASSIGN_TO_CARDHOLDER = "Assign to a cardholder"
KEEP_IN_NEED_REVIEW = "Keep in Need Review"
MARK_AS_UNMATCHED = "Mark as Unmatched"

MANUAL_ASSIGNMENT_NOTE = "Manually assigned in Streamlit review."
MANUAL_UNMATCHED_NOTE = "Marked as unmatched during Streamlit review."


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

        if action == ASSIGN_TO_CARDHOLDER and cardholder_name:
            reviewed.loc[row_index, "Cardholder name"] = cardholder_name
            reviewed.loc[row_index, "Match confidence"] = "Manual"
            reviewed.loc[row_index, "Match note"] = MANUAL_ASSIGNMENT_NOTE
        elif action == MARK_AS_UNMATCHED:
            reviewed.loc[row_index, "Cardholder name"] = ""
            reviewed.loc[row_index, "Match confidence"] = "Unmatched"
            reviewed.loc[row_index, "Match note"] = MANUAL_UNMATCHED_NOTE

    return reviewed
