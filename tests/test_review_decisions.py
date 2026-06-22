from __future__ import annotations

import unittest
from zipfile import ZipFile

import pandas as pd

from src.config import OUTPUT_COLUMNS
from src.exporter import CARDHOLDER_OUTPUT_COLUMNS, build_output_frames, create_output_zip
from src.matching import build_summary_metrics
from src.review import (
    APPROVE_SUGGESTED_ASSIGNMENT,
    APPROVED_SUGGESTION_NOTE,
    CHANGE_CARDHOLDER,
    KEEP_IN_NEED_REVIEW,
    MANUAL_CARDHOLDER_CHANGE_NOTE,
    MANUAL_UNMATCHED_NOTE,
    MARK_AS_UNMATCHED,
    apply_review_decisions,
    default_review_action,
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
            "Card number": "5555 4444 3333 3810",
            "Cardholder name": "Shantae Gibson",
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
                    "action": APPROVE_SUGGESTED_ASSIGNMENT,
                    "cardholder_name": "",
                    "suggested_cardholder_name": "Shantae Gibson",
                },
                1: {
                    "action": MARK_AS_UNMATCHED,
                    "cardholder_name": "",
                    "suggested_cardholder_name": "",
                },
                2: {
                    "action": KEEP_IN_NEED_REVIEW,
                    "cardholder_name": "",
                    "suggested_cardholder_name": "",
                },
            },
        )

        self.assertEqual(reviewed.loc[0, "Cardholder name"], "Shantae Gibson")
        self.assertEqual(reviewed.loc[0, "Match confidence"], "Manual")
        self.assertEqual(reviewed.loc[0, "Match note"], APPROVED_SUGGESTION_NOTE)
        self.assertEqual(reviewed.loc[1, "Cardholder name"], "")
        self.assertEqual(reviewed.loc[1, "Match confidence"], "Unmatched")
        self.assertEqual(reviewed.loc[1, "Match note"], MANUAL_UNMATCHED_NOTE)
        self.assertEqual(reviewed.loc[2, "Match confidence"], "Review")

    def test_manual_assignments_export_to_cardholder_file(self) -> None:
        reviewed = apply_review_decisions(
            _results_df(),
            {
                0: {
                    "action": APPROVE_SUGGESTED_ASSIGNMENT,
                    "cardholder_name": "",
                    "suggested_cardholder_name": "Shantae Gibson",
                },
                1: {
                    "action": MARK_AS_UNMATCHED,
                    "cardholder_name": "",
                    "suggested_cardholder_name": "",
                },
                2: {
                    "action": KEEP_IN_NEED_REVIEW,
                    "cardholder_name": "",
                    "suggested_cardholder_name": "",
                },
            },
        )

        frames = build_output_frames(reviewed)

        self.assertIn("Shantae_Gibson_missing_receipts.xlsx", frames)
        self.assertEqual(len(frames["Shantae_Gibson_missing_receipts.xlsx"]), 1)
        self.assertEqual(len(frames["Need_Review.xlsx"]), 1)
        self.assertEqual(len(frames["Unmatched_QBO.xlsx"]), 1)

    def test_cardholder_output_columns_are_clean_and_ordered(self) -> None:
        reviewed = apply_review_decisions(
            _results_df(),
            {
                0: {
                    "action": APPROVE_SUGGESTED_ASSIGNMENT,
                    "cardholder_name": "",
                    "suggested_cardholder_name": "Shantae Gibson",
                },
            },
        )

        frames = build_output_frames(reviewed)
        cardholder_frame = frames["Shantae_Gibson_missing_receipts.xlsx"]

        self.assertEqual(list(cardholder_frame.columns), CARDHOLDER_OUTPUT_COLUMNS)
        self.assertNotIn("Match confidence", cardholder_frame.columns)
        self.assertNotIn("Match note", cardholder_frame.columns)
        self.assertNotIn("Bank amount", cardholder_frame.columns)

    def test_cardholder_amount_uses_signed_qbo_spent_and_received(self) -> None:
        results = _results_df()
        results["QBO Received"] = results["QBO Received"].astype(float)
        results.loc[0, "Cardholder name"] = "Shantae Gibson"
        results.loc[0, "Match confidence"] = "Manual"
        results.loc[0, "QBO Spent"] = 34.72
        results.loc[0, "QBO Received"] = 0
        results.loc[2, "Cardholder name"] = "Shantae Gibson"
        results.loc[2, "Match confidence"] = "Manual"
        results.loc[2, "QBO Spent"] = 0
        results.loc[2, "QBO Received"] = 12.5
        results.loc[2, "Bank amount"] = -999

        frames = build_output_frames(results)
        amounts = frames["Shantae_Gibson_missing_receipts.xlsx"]["Amount"].tolist()

        self.assertEqual(amounts, [-34.72, 12.5])

    def test_mastercard_exports_to_missing_receipts_file(self) -> None:
        results = _results_df()
        results.loc[0, "Card number"] = "5555 4444 3333 3812"
        results.loc[0, "Cardholder name"] = "Mastercard"
        results.loc[0, "Match confidence"] = "Manual"

        frames = build_output_frames(results)

        self.assertIn("Mastercard_missing_receipts.xlsx", frames)
        self.assertEqual(len(frames["Mastercard_missing_receipts.xlsx"]), 1)

    def test_cardholder_filename_convention(self) -> None:
        frames = build_output_frames(_results_df())

        self.assertIn("Catherine_Bainbridge_missing_receipts.xlsx", frames)
        self.assertIn("Archita_Ghosh_missing_receipts.xlsx", frames)
        self.assertIn("Brittany_Leborgne_missing_receipts.xlsx", frames)
        self.assertIn("Ernest_Webb_missing_receipts.xlsx", frames)
        self.assertIn("Shantae_Gibson_missing_receipts.xlsx", frames)
        self.assertIn("Mastercard_missing_receipts.xlsx", frames)
        self.assertNotIn("Shantae_Gibson.xlsx", frames)

    def test_matching_log_exists_in_zip(self) -> None:
        zip_buffer = create_output_zip(_results_df())

        with ZipFile(zip_buffer) as archive:
            self.assertIn("Matching_Log.xlsx", archive.namelist())

    def test_manual_assignments_count_as_matched_in_summary(self) -> None:
        reviewed = apply_review_decisions(
            _results_df(),
            {
                0: {
                    "action": APPROVE_SUGGESTED_ASSIGNMENT,
                    "cardholder_name": "",
                    "suggested_cardholder_name": "Shantae Gibson",
                },
            },
        )

        metrics = build_summary_metrics(reviewed)

        self.assertEqual(metrics["Matched transactions"], 1)
        self.assertEqual(metrics["Need review transactions"], 2)

    def test_change_cardholder_uses_manual_change_note(self) -> None:
        reviewed = apply_review_decisions(
            _results_df(),
            {
                0: {
                    "action": CHANGE_CARDHOLDER,
                    "cardholder_name": "Mastercard",
                    "suggested_cardholder_name": "Shantae Gibson",
                },
            },
        )

        self.assertEqual(reviewed.loc[0, "Cardholder name"], "Mastercard")
        self.assertEqual(reviewed.loc[0, "Match confidence"], "Manual")
        self.assertEqual(reviewed.loc[0, "Match note"], MANUAL_CARDHOLDER_CHANGE_NOTE)

    def test_default_review_action_approves_when_suggestion_exists(self) -> None:
        suggested_row = _results_df().loc[0]
        unsuggested_row = _results_df().loc[1]

        self.assertEqual(default_review_action(suggested_row), APPROVE_SUGGESTED_ASSIGNMENT)
        self.assertEqual(default_review_action(unsuggested_row), KEEP_IN_NEED_REVIEW)


if __name__ == "__main__":
    unittest.main()
