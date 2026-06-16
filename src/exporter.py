"""Excel and ZIP export helpers."""

from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.config import CARDHOLDER_NAMES, OUTPUT_COLUMNS


def build_output_frames(results_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split matched results into the required workbook outputs."""
    frames: dict[str, pd.DataFrame] = {}
    confident = results_df["Match confidence"].isin(["High", "Medium"])

    for cardholder_name in CARDHOLDER_NAMES:
        filename = f"{cardholder_name.replace(' ', '_')}.xlsx"
        frames[filename] = _ensure_output_columns(
            results_df.loc[confident & (results_df["Cardholder name"] == cardholder_name)]
        )

    frames["Need_Review.xlsx"] = _ensure_output_columns(
        results_df.loc[results_df["Match confidence"] == "Review"]
    )
    frames["Unmatched_QBO.xlsx"] = _ensure_output_columns(
        results_df.loc[results_df["Match confidence"] == "Unmatched"]
    )

    return frames


def create_output_zip(results_df: pd.DataFrame) -> BytesIO:
    """Create the required workbook ZIP in memory for Streamlit download."""
    zip_buffer = BytesIO()
    frames = build_output_frames(results_df)

    with ZipFile(zip_buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for filename, frame in frames.items():
            archive.writestr(filename, dataframe_to_excel_bytes(frame).getvalue())

    zip_buffer.seek(0)
    return zip_buffer


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Transactions") -> BytesIO:
    """Write a DataFrame to a professionally formatted Excel workbook."""
    buffer = BytesIO()
    export_df = _ensure_output_columns(df).copy()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name=sheet_name)
        worksheet = writer.sheets[sheet_name]
        _format_worksheet(worksheet, export_df)

    buffer.seek(0)
    return buffer


def _ensure_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.reindex(columns=OUTPUT_COLUMNS)


def _format_worksheet(worksheet, df: pd.DataFrame) -> None:
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)

    for cell in worksheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    for column_cells in worksheet.columns:
        column_letter = get_column_letter(column_cells[0].column)
        header = str(column_cells[0].value)
        width = max(
            len(header),
            *[
                len(str(cell.value)) if cell.value is not None else 0
                for cell in column_cells[1:]
            ],
        )
        worksheet.column_dimensions[column_letter].width = min(max(width + 2, 12), 48)

        lower_header = header.lower()
        for cell in column_cells[1:]:
            if "date" in lower_header:
                cell.number_format = "yyyy-mm-dd"
            elif _is_amount_column(lower_header):
                cell.number_format = '$#,##0.00;[Red]-$#,##0.00'


def _is_amount_column(header: str) -> bool:
    return any(token in header for token in ["amount", "spent", "received"])
