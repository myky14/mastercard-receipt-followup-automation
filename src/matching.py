"""Transaction matching logic."""

from __future__ import annotations

import pandas as pd
from rapidfuzz import fuzz

from src.config import (
    AMOUNT_TOLERANCE,
    DEFAULT_CARDHOLDER_MAP,
    HIGH_SIMILARITY_THRESHOLD,
    MEDIUM_SIMILARITY_THRESHOLD,
    OUTPUT_COLUMNS,
)


def match_transactions(
    qbo_df: pd.DataFrame,
    bank_df: pd.DataFrame,
    date_tolerance_days: int = 3,
    cardholder_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Match QBO transactions to bank transactions using amount, date, and text similarity."""
    mapping = cardholder_map or DEFAULT_CARDHOLDER_MAP
    used_bank_indexes: set[int] = set()
    match_records: list[dict[str, object]] = []

    for qbo_index, qbo_row in qbo_df.iterrows():
        candidates = _find_candidates(
            qbo_row=qbo_row,
            bank_df=bank_df,
            used_bank_indexes=used_bank_indexes,
            date_tolerance_days=date_tolerance_days,
        )

        if candidates.empty:
            match_records.append(_unmatched_record(qbo_row))
            continue

        candidates = _score_candidates(qbo_row, candidates, mapping)
        best_match = candidates.iloc[0]
        record = _build_match_record(qbo_row, best_match)

        if len(candidates) > 1:
            record["Match confidence"] = "Review"
            record["Match note"] = (
                f"Multiple bank transactions matched amount/date; best candidate selected "
                f"from {len(candidates)} possible matches."
            )
        elif not best_match["cardholder_name"]:
            record["Match confidence"] = "Review"
            record["Match note"] = "Amount/date matched, but the card number is not in the mapping."
        elif best_match["description_similarity"] >= HIGH_SIMILARITY_THRESHOLD:
            record["Match confidence"] = "High"
            record["Match note"] = "Amount/date matched and descriptions are strongly similar."
            used_bank_indexes.add(int(best_match.name))
        elif best_match["description_similarity"] >= MEDIUM_SIMILARITY_THRESHOLD:
            record["Match confidence"] = "Medium"
            record["Match note"] = "Amount/date matched, but description similarity is weaker."
            used_bank_indexes.add(int(best_match.name))
        else:
            record["Match confidence"] = "Review"
            record["Match note"] = "Amount/date matched, but description similarity is very weak."

        match_records.append(record)

    result = pd.DataFrame(match_records)
    return result.reindex(columns=OUTPUT_COLUMNS)


def build_summary_metrics(results_df: pd.DataFrame) -> dict[str, object]:
    """Build the metrics shown in the Streamlit dashboard."""
    total_qbo = len(results_df)
    matched = int(results_df["Match confidence"].isin(["High", "Medium"]).sum())
    review = int((results_df["Match confidence"] == "Review").sum())
    unmatched = int((results_df["Match confidence"] == "Unmatched").sum())
    match_rate = matched / total_qbo if total_qbo else 0

    return {
        "Total QBO transactions": total_qbo,
        "Matched transactions": matched,
        "Need review transactions": review,
        "Unmatched QBO transactions": unmatched,
        "Match rate": match_rate,
    }


def _find_candidates(
    qbo_row: pd.Series,
    bank_df: pd.DataFrame,
    used_bank_indexes: set[int],
    date_tolerance_days: int,
) -> pd.DataFrame:
    if pd.isna(qbo_row["qbo_date"]) or qbo_row["qbo_amount"] <= 0:
        return bank_df.iloc[0:0].copy()

    amount_matches = (bank_df["bank_amount"] - qbo_row["qbo_amount"]).abs() <= AMOUNT_TOLERANCE
    date_difference = (bank_df["bank_transaction_date"] - qbo_row["qbo_date"]).dt.days.abs()
    date_matches = date_difference <= date_tolerance_days
    not_already_used = ~bank_df.index.isin(used_bank_indexes)

    return bank_df.loc[amount_matches & date_matches & not_already_used].copy()


def _score_candidates(
    qbo_row: pd.Series,
    candidates: pd.DataFrame,
    cardholder_map: dict[str, str],
) -> pd.DataFrame:
    scored = candidates.copy()
    scored["date_difference_days"] = (
        scored["bank_transaction_date"] - qbo_row["qbo_date"]
    ).dt.days.abs()
    scored["description_similarity"] = scored["bank_description"].apply(
        lambda description: fuzz.token_set_ratio(
            str(qbo_row["qbo_description"]),
            str(description),
        )
    )
    scored["cardholder_name"] = scored["card_last4"].map(cardholder_map).fillna("")
    scored = scored.sort_values(
        by=["description_similarity", "date_difference_days"],
        ascending=[False, True],
    )
    return scored


def _base_qbo_record(qbo_row: pd.Series) -> dict[str, object]:
    return {
        "QBO Date": qbo_row.get("qbo_date"),
        "QBO Bank description": qbo_row.get("qbo_description", ""),
        "QBO Spent": qbo_row.get("qbo_spent", 0),
        "QBO Received": qbo_row.get("qbo_received", 0),
        "QBO From/To": qbo_row.get("qbo_from_to", ""),
        "QBO Amount": qbo_row.get("qbo_amount", 0),
    }


def _unmatched_record(qbo_row: pd.Series) -> dict[str, object]:
    record = _base_qbo_record(qbo_row)
    record.update(
        {
            "Card number": "",
            "Cardholder name": "",
            "Bank transaction date": pd.NaT,
            "Bank description": "",
            "Bank amount": 0,
            "Match confidence": "Unmatched",
            "Match note": "No bank transaction matched amount/date within the selected tolerance.",
            "Date difference days": "",
            "Description similarity": "",
            "Bank reference": "",
        }
    )
    return record


def _build_match_record(qbo_row: pd.Series, bank_row: pd.Series) -> dict[str, object]:
    record = _base_qbo_record(qbo_row)
    record.update(
        {
            "Card number": bank_row.get("card_number", ""),
            "Cardholder name": bank_row.get("cardholder_name", ""),
            "Bank transaction date": bank_row.get("bank_transaction_date"),
            "Bank description": bank_row.get("bank_description", ""),
            "Bank amount": bank_row.get("bank_amount", 0),
            "Match confidence": "",
            "Match note": "",
            "Date difference days": int(bank_row.get("date_difference_days", 0)),
            "Description similarity": round(float(bank_row.get("description_similarity", 0)), 1),
            "Bank reference": bank_row.get("bank_reference", ""),
        }
    )
    return record
