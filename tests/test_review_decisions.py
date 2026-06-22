from __future__ import annotations

import unittest

import pandas as pd

from src.config import OUTPUT_COLUMNS
from src.exporter import build_output_frames
from src.matching import build_summary_metrics
from src.review import (
    ASSIGN_TO_CARDHOLDER,
    KEEP_IN_NEED_REVIEW,
    MANUAL_ASSIGNMENT_NOTE,
    MANUAL_UNMATCHED_NOTE,
    MARK_AS_UNMATCHED,
    apply_review_decisions,
)


def _results_df() -> pd.DataFrame:
    rows = [
        {
            "QBO Date": pd.Timestamp("2026-05-12"),
            "QBO Bank description": "UBER TRIP",
            "QBO Spent": 34.72,
            "QBO Received": 0,
            "QBO From/To": "Uber",
            "QBO Amount": 34.72,
            "Card number": "5555 4444 3333 9999",
            "Cardholder name": "",
            "Bank transaction date": pd.Timestamp("2026-05-13"),
            "Bank description": "UBER CANADA TRIP",
            "Bank amount": 34.72,
            "Match confidence": "Review",
            "Match note": "Amount/date matched, but the card number is not in the mapping.",
            "Date difference days": 1,
            "Description similarity": 80.0,
            "Bank reference": "MC1001",
        },
        {
            "QBO Date": pd.Timestamp("2026-05-14"),
            "QBO Bank description": "COURIER",
            "QBO Spent": 41.1,
            "QBO Received": 0,
            "QBO From/To": "Courier",
            "QBO Amount": 41.1,
            "Card number": "5555 4444 3333 8888",
            "Cardholder name": "",
            "Bank transaction date": pd.Timestamp("2026-05-14"),
            "Bank description": "LOCAL COURIER",
            "Bank amount": 41.1,
            "Match confidence": "Review",
            "Match note": "Multiple bank transactions matched amount/date.",
            "Date difference days": 0,
            "Description similarity": 72.0,
            "Bank reference": "MC1002",
        },
        {
            "QBO Date": pd.Timestamp("2026-05-15"),
            "QBO Bank description": "SUPPLIES",
            "QBO Spent": 12.5,
            "QBO Received": 0,
            "QBO From/To": "Supplies",
            "QBO Amount": 12.5,
            "Card number": "5555 4444 3333 3810",
            "Cardholder name": "",
            "Bank transaction date": pd.Timestamp("2026-05-15"),
            "Bank description": "SUPPLIES",
            "Bank amount": 12.5,
            "Match confidence": "Review",
            "Match note": "Pending review.",
            "Date difference days": 0,
            "Description similarity": 99.0,
            "Bank reference": "MC1003",
        },
    ]
    return pd.DataFrame(rows).reindex(columns=OUTPUT_COLUMNS)


class ReviewDecisionTests(unittest.TestCase):
    def test_review_decisions_assign_keep_and_mark_unmatched(self) -> None:
        reviewed = apply_review_decisions(
            _results_df(),
            {
                0: {
                    "action": ASSIGN_TO_CARDHOLDER,
                    "cardholder_name": "Shantae Gibson",
                },
                1: {
                    "action": MARK_AS_UNMATCHED,
                    "cardholder_name": "",
                },
                2: {
                    "action": KEEP_IN_NEED_REVIEW,
                    "cardholder_name": "",
                },
            },
        )

        self.assertEqual(reviewed.loc[0, "Cardholder name"], "Shantae Gibson")
        self.assertEqual(reviewed.loc[0, "Match confidence"], "Manual")
        self.assertEqual(reviewed.loc[0, "Match note"], MANUAL_ASSIGNMENT_NOTE)
        self.assertEqual(reviewed.loc[1, "Cardholder name"], "")
        self.assertEqual(reviewed.loc[1, "Match confidence"], "Unmatched")
        self.assertEqual(reviewed.loc[1, "Match note"], MANUAL_UNMATCHED_NOTE)
        self.assertEqual(reviewed.loc[2, "Match confidence"], "Review")

    def test_manual_assignments_export_to_cardholder_file(self) -> None:
        reviewed = apply_review_decisions(
            _results_df(),
            {
                0: {
                    "action": ASSIGN_TO_CARDHOLDER,
                    "cardholder_name": "Shantae Gibson",
                },
                1: {
                    "action": MARK_AS_UNMATCHED,
                    "cardholder_name": "",
                },
                2: {
                    "action": KEEP_IN_NEED_REVIEW,
                    "cardholder_name": "",
                },
            },
        )

        frames = build_output_frames(reviewed)

        self.assertIn("Shantae_Gibson.xlsx", frames)
        self.assertEqual(len(frames["Shantae_Gibson.xlsx"]), 1)
        self.assertEqual(len(frames["Need_Review.xlsx"]), 1)
        self.assertEqual(len(frames["Unmatched_QBO.xlsx"]), 1)

    def test_manual_assignments_count_as_matched_in_summary(self) -> None:
        reviewed = apply_review_decisions(
            _results_df(),
            {
                0: {
                    "action": ASSIGN_TO_CARDHOLDER,
                    "cardholder_name": "Shantae Gibson",
                },
            },
        )

        metrics = build_summary_metrics(reviewed)

        self.assertEqual(metrics["Matched transactions"], 1)
        self.assertEqual(metrics["Need review transactions"], 2)


if __name__ == "__main__":
    unittest.main()
