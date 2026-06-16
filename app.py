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
REPOSITORY_URL = "https://github.com/myky14/mastercard-receipt-followup-automation"
GITHUB_URL = "https://github.com/myky14"
LINKEDIN_URL = "https://www.linkedin.com/in/myky14/"


st.markdown(
    """
    <style>
        .project-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0.75rem 0 0.25rem;
        }
        .project-badge {
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 999px;
            padding: 0.28rem 0.7rem;
            color: #334155;
            background: #f8fafc;
            font-size: 0.86rem;
            font-weight: 600;
        }
        .workflow-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 0.9rem;
            margin-top: 1rem;
        }
        .workflow-card {
            min-height: 150px;
            border: 1px solid rgba(49, 51, 63, 0.12);
            border-radius: 14px;
            background: #ffffff;
            padding: 1rem 0.9rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.55rem;
        }
        .workflow-number {
            width: 1.6rem;
            height: 1.6rem;
            border-radius: 999px;
            background: #eef2ff;
            color: #3730a3;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .workflow-icon {
            font-size: 1.9rem;
            line-height: 1;
        }
        .workflow-title {
            color: #1f2937;
            font-size: 0.98rem;
            font-weight: 700;
            line-height: 1.25;
        }
        .workflow-copy {
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.35;
        }
        .footer {
            text-align: center;
            color: #888888;
            font-size: 0.9rem;
            line-height: 1.65;
        }
        .footer a {
            color: #64748b;
            text-decoration: none;
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """Read uploaded CSV content while preserving card numbers as text."""
    return pd.read_csv(uploaded_file, dtype=str, keep_default_na=False)


def render_header() -> None:
    st.title("Mastercard Receipt Follow-up Automation")
    st.write(
        "Match unmatched QBO Mastercard transactions with bank exports and "
        "generate cardholder follow-up workbooks."
    )
    st.markdown(
        """
        <div class="project-badges">
            <span class="project-badge">QBO + Bank CSV Matching</span>
            <span class="project-badge">Cardholder Identification</span>
            <span class="project-badge">Receipt Follow-up Workflow</span>
            <span class="project-badge">Excel ZIP Export</span>
            <span class="project-badge">Human-in-the-Loop Review</span>
            <span class="project-badge">Streamlit Demo</span>
            <span class="project-badge">Portfolio Project</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.success(
        "Demo environment loaded. This application uses fictional sample data for public demonstration."
    )


def render_about_project() -> None:
    with st.expander("About This Project", expanded=False):
        st.markdown(
            """
            ### What it does

            This project automates Mastercard receipt follow-up preparation by:

            - Cleaning QBO unmatched Mastercard transaction exports
            - Cleaning bank Mastercard transaction exports
            - Matching QBO transactions to bank transactions by amount and date
            - Using description similarity to support uncertain matches
            - Identifying cardholders from the last four digits of the card number
            - Separating transactions into one Excel file per cardholder
            - Creating review and unmatched files for safer manual follow-up

            ### Why it was built

            Built as a personal learning project to practice:

            - Python
            - Data Cleaning
            - Transaction Matching
            - Excel Automation
            - Workflow Design
            - Streamlit Development

            The workflow was inspired by a repetitive accounting task where unmatched QBO Mastercard transactions had to be manually compared with bank exports to identify who used each card and prepare follow-up files for missing receipts.

            ### Workflow

            QBO Export
            -> Bank Export
            -> Clean CSV Data
            -> Transaction Matching
            -> Cardholder Identification
            -> Review Results
            -> ZIP Download

            ### Important

            This public demo uses fictional sample data only.

            No real QBO exports, bank exports, client data, employee data, or cardholder-sensitive data should be uploaded to the public repository.
            """
        )


def render_sidebar_info() -> None:
    st.subheader("Navigation")
    st.markdown(
        f"""

        **Author:** Nguyen Du My Ky

        **Demo Type:** Public Sample Data

        **Repository:** [GitHub Repository]({REPOSITORY_URL})
        """
    )
    st.divider()


def render_workflow_visual() -> None:
    st.markdown(
        """
        <div class="workflow-grid">
            <div class="workflow-card">
                <div class="workflow-number">1</div>
                <div class="workflow-title">Upload QBO CSV</div>
                <div class="workflow-copy">Start with unmatched Mastercard transactions from QBO.</div>
            </div>
            <div class="workflow-card">
                <div class="workflow-number">2</div>
                <div class="workflow-title">Upload Bank CSV</div>
                <div class="workflow-copy">Add the bank export that includes card numbers and transaction details.</div>
            </div>
            <div class="workflow-card">
                <div class="workflow-number">3</div>
                <div class="workflow-title">Match Transactions</div>
                <div class="workflow-copy">Compare amount, date, and description similarity.</div>
            </div>
            <div class="workflow-card">
                <div class="workflow-number">4</div>
                <div class="workflow-title">Identify Cardholders</div>
                <div class="workflow-copy">Use the last four card digits to assign follow-up ownership.</div>
            </div>
            <div class="workflow-card">
                <div class="workflow-number">5</div>
                <div class="workflow-title">Generate Excel Reports</div>
                <div class="workflow-copy">Create cardholder, review, and unmatched workbooks.</div>
            </div>
            <div class="workflow-card">
                <div class="workflow-number">6</div>
                <div class="workflow-title">Download ZIP</div>
                <div class="workflow-copy">Package every report into one ready-to-share download.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_project_metrics() -> None:
    metric_cols = st.columns(4)
    metric_cols[0].metric("Date Tolerance", "User Selected")
    metric_cols[1].metric("Card Mapping", "Built In")
    metric_cols[2].metric("Sample Data", "Available")
    metric_cols[3].metric("Demo Mode", "Fictional Data")


def render_input_status(qbo_upload, bank_upload) -> None:
    status_cols = st.columns(2)
    status_cols[0].metric("QBO CSV", qbo_upload.name if qbo_upload else "Waiting")
    status_cols[1].metric("Bank CSV", bank_upload.name if bank_upload else "Waiting")
    st.info("Upload both CSV files from the sidebar, then run matching to create review workbooks.")


def render_footer() -> None:
    st.markdown(
        f"""
        <hr>
        <div class="footer">
            Built and designed by Nguyen Du My Ky<br>
            <strong>Mastercard Receipt Follow-up Automation</strong><br>
            QBO Matching - Cardholder Identification - Excel Reports - Receipt Follow-up<br>
            GitHub: <a href="{GITHUB_URL}" target="_blank">github.com/myky14</a>
            &nbsp;|&nbsp;
            LinkedIn: <a href="{LINKEDIN_URL}" target="_blank">linkedin.com/in/myky14</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


render_header()
render_about_project()

with st.sidebar:
    render_sidebar_info()
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

st.divider()
st.subheader("Project Overview")
render_project_metrics()
render_workflow_visual()

st.divider()
st.subheader("Input Files")
render_input_status(qbo_upload, bank_upload)

if run_button:
    run_matching(qbo_upload, bank_upload, date_tolerance)

results_df = st.session_state.get("results")
zip_buffer = st.session_state.get("zip_buffer")

st.divider()
st.subheader("Processing")
if results_df is None:
    st.info("Upload both CSV files, choose a date tolerance, and run matching.")
else:
    metrics = build_summary_metrics(results_df)
    display_summary(metrics)

    matched_df = results_df[results_df["Match confidence"].isin(["High", "Medium"])]
    review_df = results_df[results_df["Match confidence"] == "Review"]
    unmatched_df = results_df[results_df["Match confidence"] == "Unmatched"]

    st.divider()
    st.subheader("Results")
    tab_matched, tab_review, tab_unmatched = st.tabs(
        ["Matched transactions", "Need review", "Unmatched QBO"]
    )

    with tab_matched:
        st.dataframe(matched_df, use_container_width=True, hide_index=True)

    with tab_review:
        st.dataframe(review_df, use_container_width=True, hide_index=True)

    with tab_unmatched:
        st.dataframe(unmatched_df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Downloads")
    st.download_button(
        label="Download ZIP output",
        data=zip_buffer,
        file_name="mastercard_receipt_followup_outputs.zip",
        mime="application/zip",
        type="primary",
    )

render_footer()
