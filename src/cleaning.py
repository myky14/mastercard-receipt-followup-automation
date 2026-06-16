"""Data-cleaning helpers for QBO and Mastercard exports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass
class MissingColumnError(ValueError):
    """Raised when an uploaded file does not contain required columns."""

    file_label: str
    missing_columns: list[str]
    available_columns: list[str]

    def __str__(self) -> str:
        missing = ", ".join(self.missing_columns)
        available = ", ".join(self.available_columns) or "none"
        return (
            f"{self.file_label} is missing required column(s): {missing}. "
            f"Available columns: {available}."
        )


QBO_ALIASES = {
    "qbo_date": ["date", "qbo_date", "transaction_date", "txn_date"],
    "qbo_description": [
        "bank_description",
        "bank_desc",
        "description",
        "transaction_description",
        "memo_description",
    ],
    "qbo_spent": ["spent", "debit", "debits", "payment", "charge", "charges"],
    "qbo_received": ["received", "credit", "credits", "deposit", "refund", "refunds"],
    "qbo_from_to": ["from_to", "fromto", "payee", "vendor", "name", "customer_supplier"],
}

BANK_ALIASES = {
    "bank_transaction_date": [
        "transaction_date",
        "bank_transaction_date",
        "trans_date",
        "date",
        "txn_date",
    ],
    "card_number": [
        "card_number",
        "card_no",
        "card",
        "account_number",
        "credit_card_number",
    ],
    "date_carried_to_statement": [
        "date_carried_to_statement",
        "statement_date",
        "carried_to_statement",
    ],
    "bank_reference": ["reference", "ref", "reference_number", "transaction_reference"],
    "bank_status": ["status", "transaction_status"],
    "bank_description": [
        "description",
        "bank_description",
        "transaction_description",
        "merchant",
        "details",
    ],
    "bank_amount": ["amount", "transaction_amount", "bank_amount", "amt"],
}

REQUIRED_QBO_COLUMNS = [
    "qbo_date",
    "qbo_description",
    "qbo_spent",
    "qbo_received",
    "qbo_from_to",
]

REQUIRED_BANK_COLUMNS = [
    "bank_transaction_date",
    "card_number",
    "bank_description",
    "bank_amount",
]


def normalize_column_name(column_name: object) -> str:
    """Normalize a column name so capitalization and spacing variations still work."""
    normalized = str(column_name).strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    return normalized.strip("_")


def _first_available_column(
    normalized_columns: dict[str, str], aliases: Iterable[str]
) -> str | None:
    for alias in aliases:
        if alias in normalized_columns:
            return normalized_columns[alias]
    return None


def _standardize_columns(
    df: pd.DataFrame,
    alias_map: dict[str, list[str]],
    required_columns: list[str],
    file_label: str,
) -> pd.DataFrame:
    normalized_to_original = {
        normalize_column_name(column): column for column in df.columns
    }

    rename_map: dict[str, str] = {}
    missing_columns: list[str] = []

    for canonical_name, aliases in alias_map.items():
        original_name = _first_available_column(normalized_to_original, aliases)
        if original_name is not None:
            rename_map[original_name] = canonical_name
        elif canonical_name in required_columns:
            missing_columns.append(_pretty_required_name(canonical_name))

    if missing_columns:
        raise MissingColumnError(
            file_label=file_label,
            missing_columns=missing_columns,
            available_columns=[str(column) for column in df.columns],
        )

    cleaned = df.rename(columns=rename_map).copy()

    tax_columns = [
        column
        for column in cleaned.columns
        if normalize_column_name(column) == "tax"
    ]
    if tax_columns:
        cleaned = cleaned.drop(columns=tax_columns)

    return cleaned


def _pretty_required_name(canonical_name: str) -> str:
    return {
        "qbo_date": "Date",
        "qbo_description": "Bank description",
        "qbo_spent": "Spent",
        "qbo_received": "Received",
        "qbo_from_to": "From/To",
        "bank_transaction_date": "Transaction date",
        "card_number": "Card number",
        "bank_description": "Description",
        "bank_amount": "Amount",
    }.get(canonical_name, canonical_name)


def _parse_money(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip()
    values = values.str.replace(r"[\$,]", "", regex=True)
    values = values.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    values = values.str.replace(r"\s+", "", regex=True)
    return pd.to_numeric(values, errors="coerce").fillna(0)


def _parse_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _clean_card_number(value: object) -> str:
    raw_value = str(value).strip()
    raw_value = re.sub(r"\.0$", "", raw_value)
    return re.sub(r"\D", "", raw_value)


def prepare_qbo_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Return QBO transactions with canonical columns and normalized amounts."""
    qbo = _standardize_columns(
        df=df,
        alias_map=QBO_ALIASES,
        required_columns=REQUIRED_QBO_COLUMNS,
        file_label="QBO CSV",
    )

    qbo["qbo_date"] = _parse_dates(qbo["qbo_date"])
    qbo["qbo_spent"] = _parse_money(qbo["qbo_spent"])
    qbo["qbo_received"] = _parse_money(qbo["qbo_received"])
    qbo["qbo_amount"] = qbo["qbo_spent"].where(
        qbo["qbo_spent"].abs() > 0,
        qbo["qbo_received"],
    ).abs()

    qbo["qbo_description"] = qbo["qbo_description"].fillna("").astype(str).str.strip()
    qbo["qbo_from_to"] = qbo["qbo_from_to"].fillna("").astype(str).str.strip()
    qbo["qbo_row_id"] = range(1, len(qbo) + 1)

    return qbo


def prepare_bank_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Return bank transactions with canonical columns and normalized amounts."""
    bank = _standardize_columns(
        df=df,
        alias_map=BANK_ALIASES,
        required_columns=REQUIRED_BANK_COLUMNS,
        file_label="Bank CSV",
    )

    bank["bank_transaction_date"] = _parse_dates(bank["bank_transaction_date"])
    bank["bank_amount"] = _parse_money(bank["bank_amount"]).abs()
    bank["bank_description"] = bank["bank_description"].fillna("").astype(str).str.strip()
    bank["card_number"] = bank["card_number"].fillna("").astype(str).str.strip()
    bank["card_digits"] = bank["card_number"].map(_clean_card_number)
    bank["card_last4"] = bank["card_digits"].str[-4:]
    bank["bank_row_id"] = range(1, len(bank) + 1)

    if "bank_reference" not in bank.columns:
        bank["bank_reference"] = ""
    else:
        bank["bank_reference"] = bank["bank_reference"].fillna("").astype(str).str.strip()

    return bank
