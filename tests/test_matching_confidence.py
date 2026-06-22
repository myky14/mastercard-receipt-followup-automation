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
        self.assertEqual(results.loc[0, "Match note"], "Matched by amount and date.")
        self.assertEqual(results.loc[0, "Cardholder name"], "Catherine Bainbridge")
        self.assertNotIn("very weak", results.loc[0, "Match note"])

    def test_real_world_single_candidate_description_variants_are_high(self) -> None:
        examples = [
            ("Bluebird", "BLUEBIRD (IN)"),
            ("Banff Springs Hotel", "BANFF SPRINGS HOTEL CO"),
            ("Anthropic", "ANTHROPIC"),
        ]

        for qbo_description, bank_description in examples:
            with self.subTest(qbo_description=qbo_description):
                results = match_transactions(
                    _qbo_row(qbo_description),
                    pd.DataFrame([_bank_row(bank_description)]),
                )

                self.assertEqual(results.loc[0, "Match confidence"], "High")
                self.assertEqual(results.loc[0, "Match note"], "Matched by amount and date.")
                self.assertEqual(results.loc[0, "Cardholder name"], "Catherine Bainbridge")

    def test_shantae_gibson_card_mapping_is_available(self) -> None:
        bank_df = pd.DataFrame([_bank_row("HOTEL PARKING", card_last4="3810")])

        results = match_transactions(_qbo_row("HOTEL PARKING"), bank_df)

        self.assertEqual(results.loc[0, "Match confidence"], "High")
        self.assertEqual(results.loc[0, "Cardholder name"], "Shantae Gibson")

    def test_mastercard_card_mapping_is_available(self) -> None:
        bank_df = pd.DataFrame([_bank_row("MONTHLY CARD FEE", card_last4="3812")])

        results = match_transactions(_qbo_row("MONTHLY CARD FEE"), bank_df)

        self.assertEqual(results.loc[0, "Match confidence"], "High")
        self.assertEqual(results.loc[0, "Cardholder name"], "Mastercard")

    def test_multiple_candidates_with_same_card_number_auto_assign_high(self) -> None:
        bank_df = pd.DataFrame(
            [
                _bank_row("UBER CANADA TRIP", card_last4="3818", reference="MC1001"),
                _bank_row("UBER TRIP TORONTO", card_last4="3818", reference="MC1002"),
            ]
        )

        results = match_transactions(_qbo_row("UBER TRIP"), bank_df)

        self.assertEqual(results.loc[0, "Match confidence"], "High")
        self.assertEqual(results.loc[0, "Cardholder name"], "Brittany Leborgne")
        self.assertEqual(
            results.loc[0, "Match note"],
            "Matched by amount/date; multiple bank candidates share the same card.",
        )
        self.assertEqual(results.loc[0, "Candidate count"], 2)

    def test_multiple_candidates_with_same_cardholder_auto_assign_high(self) -> None:
        bank_df = pd.DataFrame(
            [
                _bank_row("PARKING GARAGE", card_last4="5589", reference="MC1001"),
                _bank_row("AIRPORT PARKING", card_last4="2261", reference="MC1002"),
            ]
        )

        results = match_transactions(_qbo_row("PARKING"), bank_df)

        self.assertEqual(results.loc[0, "Match confidence"], "High")
        self.assertEqual(results.loc[0, "Cardholder name"], "Ernest Webb")
        self.assertEqual(
            results.loc[0, "Match note"],
            "Matched by amount/date; multiple cards resolve to the same cardholder.",
        )
        self.assertEqual(results.loc[0, "Candidate count"], 2)

    def test_multiple_candidates_use_description_similarity_for_medium_match(self) -> None:
        bank_df = pd.DataFrame(
            [
                _bank_row("AMZN MKTPLACE CA", card_last4="3894", reference="MC1001"),
                _bank_row("DELTA AIR LINES", card_last4="3811", reference="MC1002"),
            ]
        )

        results = match_transactions(_qbo_row("AMAZON MKTPLACE PMTS", 34.72), bank_df)

        self.assertEqual(results.loc[0, "Match confidence"], "Medium")
        self.assertEqual(results.loc[0, "Bank reference"], "MC1001")
        self.assertEqual(
            results.loc[0, "Match note"],
            "Matched by amount/date; selected best description match from multiple cardholders.",
        )

    def test_multiple_candidates_with_no_clear_best_remain_review(self) -> None:
        bank_df = pd.DataFrame(
            [
                _bank_row("UBER CANADA TRIP", card_last4="3894", reference="MC1001"),
                _bank_row("UBER TRIP TORONTO", card_last4="3811", reference="MC1002"),
            ]
        )

        results = match_transactions(_qbo_row("UBER TRIP"), bank_df)

        self.assertEqual(results.loc[0, "Match confidence"], "Review")
        self.assertEqual(
            results.loc[0, "Match note"],
            "Multiple bank transactions matched amount/date across different cardholders; "
            "manual review required.",
        )


if __name__ == "__main__":
    unittest.main()
