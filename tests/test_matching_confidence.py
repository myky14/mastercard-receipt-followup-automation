from __future__ import annotations

import unittest

import pandas as pd

from src.matching import match_transactions


def _qbo_row(description: str = "UBER TRIP", amount: float = 34.72) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "qbo_date": pd.Timestamp("2026-05-12"),
                "qbo_description": description,
                "qbo_spent": amount,
                "qbo_received": 0,
                "qbo_from_to": description,
                "qbo_amount": amount,
            }
        ]
    )


def _bank_row(
    description: str,
    amount: float = 34.72,
    card_last4: str = "3894",
    reference: str = "MC1001",
) -> dict[str, object]:
    return {
        "bank_transaction_date": pd.Timestamp("2026-05-12"),
        "card_number": f"5555 4444 3333 {card_last4}",
        "card_last4": card_last4,
        "bank_description": description,
        "bank_amount": amount,
        "bank_reference": reference,
    }


class MatchingConfidenceTests(unittest.TestCase):
    def test_single_amount_date_candidate_is_high_even_with_low_description_similarity(self) -> None:
        bank_df = pd.DataFrame([_bank_row("FACEBK ADS")])

        results = match_transactions(_qbo_row("META"), bank_df)

        self.assertEqual(results.loc[0, "Match confidence"], "High")
        self.assertEqual(results.loc[0, "Cardholder name"], "Catherine Bainbridge")
        self.assertNotIn("very weak", results.loc[0, "Match note"])

    def test_multiple_candidates_use_description_similarity_for_medium_match(self) -> None:
        bank_df = pd.DataFrame(
            [
                _bank_row("AMZN MKTPLACE CA", reference="MC1001"),
                _bank_row("AMAZON WEB SERVICES", reference="MC1002"),
            ]
        )

        results = match_transactions(_qbo_row("AMAZON MKTPLACE PMTS", 34.72), bank_df)

        self.assertEqual(results.loc[0, "Match confidence"], "Medium")
        self.assertEqual(results.loc[0, "Bank reference"], "MC1001")
        self.assertIn("selected best description match", results.loc[0, "Match note"])

    def test_multiple_candidates_with_no_clear_best_remain_review(self) -> None:
        bank_df = pd.DataFrame(
            [
                _bank_row("UBER CANADA TRIP", reference="MC1001"),
                _bank_row("UBER TRIP TORONTO", reference="MC1002"),
            ]
        )

        results = match_transactions(_qbo_row("UBER TRIP"), bank_df)

        self.assertEqual(results.loc[0, "Match confidence"], "Review")
        self.assertIn("tie-breaker was not clear", results.loc[0, "Match note"])


if __name__ == "__main__":
    unittest.main()
