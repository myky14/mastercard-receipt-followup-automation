from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.cleaning import (
    MissingColumnError,
    prepare_bank_transactions,
    prepare_qbo_transactions,
)
from src.config import DEFAULT_DATE_TOLERANCE_DAYS
from src.exporter import create_output_zip
from src.matching import build_summary_metrics, match_transactions


st.set_page_config(
    page_title="Mastercard Receipt Follow-up Automation",
    layout="wide",
)

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"


def read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """Read uploaded CSV content while preserving card numbers as text."""
    return pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)


def show_sample_downloads() -> None:
    st.caption("Need a quick test? Download the fake sample files below.")
    sample_columns = st.columns(3)
    samples = [
        ("QBO sample", "qbo_sample.csv"),
        ("Bank sample", "bank_sample.csv"),
        ("Card mapping reference", "card_mapping.csv"),
    ]

    for column, (label, filename) in zip(sample_columns, samples):
        sample_path = SAMPLE_DATA_DIR / filename
        if sample_path.exists():
            column.download_button(
                label=label,
                data=sample_path.read_bytes(),
                file_name=filename,
                mime="text/csv",
                use_container_width=True,
            )


def display_summary(metrics: dict[str, object]) -> None:
    cols = st.columns(5)
    cols[0].metric("Total QBO", metrics["Total QBO transactions"])
    cols[1].metric("Matched", metrics["Matched transactions"])
    cols[2].metric("Need review", metrics["Need review transactions"])
    cols[3].metric("Unmatched", metrics["Unmatched QBO transactions"])
    cols[4].metric("Match rate", f"{metrics['Match rate']:.1%}")


def run_matching(qbo_upload, bank_upload, date_tolerance: int) -> None:
    try:
        qbo_raw = read_uploaded_csv(qbo_upload)
        bank_raw = read_uploaded_csv(bank_upload)
        qbo_clean = prepare_qbo_transactions(qbo_raw)
        bank_clean = prepare_bank_transactions(bank_raw)
        results = match_transactions(
            qbo_clean,
            bank_clean,
            date_tolerance_days=date_tolerance,
        )
    except MissingColumnError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # Keeps unexpected file issues visible to non-technical users.
        st.error(f"Could not process the uploaded files: {exc}")
        return

    st.session_state["results"] = results
    st.session_state["zip_buffer"] = create_output_zip(results)


st.title("Mastercard Receipt Follow-up Automation")
st.write(
    "Upload current unmatched QBO transactions and the bank Mastercard export to "
    "produce one follow-up workbook per cardholder."
)

with st.sidebar:
    st.header("Controls")
    qbo_upload = st.file_uploader("Upload QBO CSV", type=["csv"])
    bank_upload = st.file_uploader("Upload Bank CSV", type=["csv"])
    date_tolerance = st.slider(
        "Date tolerance",
        min_value=0,
        max_value=14,
        value=DEFAULT_DATE_TOLERANCE_DAYS,
        help="Allowed day difference between the QBO date and bank transaction date.",
    )

    run_button = st.button(
        "Run matching",
        type="primary",
        use_container_width=True,
        disabled=not qbo_upload or not bank_upload,
    )

    st.divider()
    show_sample_downloads()

if run_button:
    run_matching(qbo_upload, bank_upload, date_tolerance)

results_df = st.session_state.get("results")
zip_buffer = st.session_state.get("zip_buffer")

if results_df is None:
    st.info("Upload both CSV files, choose a date tolerance, and run matching.")
else:
    metrics = build_summary_metrics(results_df)
    display_summary(metrics)

    matched_df = results_df[results_df["Match confidence"].isin(["High", "Medium"])]
    review_df = results_df[results_df["Match confidence"] == "Review"]
    unmatched_df = results_df[results_df["Match confidence"] == "Unmatched"]

    tab_matched, tab_review, tab_unmatched = st.tabs(
        ["Matched transactions", "Need review", "Unmatched QBO"]
    )

    with tab_matched:
        st.dataframe(matched_df, use_container_width=True, hide_index=True)

    with tab_review:
        st.dataframe(review_df, use_container_width=True, hide_index=True)

    with tab_unmatched:
        st.dataframe(unmatched_df, use_container_width=True, hide_index=True)

    st.download_button(
        label="Download ZIP output",
        data=zip_buffer,
        file_name="mastercard_receipt_followup_outputs.zip",
        mime="application/zip",
        type="primary",
    )
