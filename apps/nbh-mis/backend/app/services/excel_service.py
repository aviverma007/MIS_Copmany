"""File loading: accepts .xlsx / .xls / .csv, finds the source-of-truth sheet."""
from __future__ import annotations

import io
import os

import pandas as pd

from app import config
from app.utils.normalize import normalize_header


class UnsupportedFileError(Exception):
    pass


class EmptyDataError(Exception):
    pass


class CorruptFileError(Exception):
    pass


def _pick_compile_sheet(sheet_names: list[str]) -> str:
    normalized = {normalize_header(n): n for n in sheet_names}
    for candidate in config.COMPILE_SHEET_NAME_CANDIDATES:
        if candidate in normalized:
            return normalized[candidate]
    # fall back: the sheet with the most columns that also has a header row
    # looking like ticket data (contains something matching "ticket" or "status")
    for n in sheet_names:
        key = normalize_header(n)
        if "compile" in key:
            return n
    return sheet_names[0]


def load_workbook(filename: str, content: bytes) -> tuple[pd.DataFrame, str, list[str]]:
    """Returns (raw_dataframe, detected_sheet_name, all_sheet_names)."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in config.ALLOWED_UPLOAD_EXTENSIONS:
        raise UnsupportedFileError(
            f"Unsupported file type '{ext}'. Please upload .xlsx, .xls or .csv."
        )

    buf = io.BytesIO(content)
    try:
        if ext == ".csv":
            df = pd.read_csv(buf)
            if df.empty:
                raise EmptyDataError("The uploaded CSV file has no data rows.")
            return df, "CSV Upload", ["CSV Upload"]

        engine = "openpyxl" if ext == ".xlsx" else None
        xls = pd.ExcelFile(buf, engine=engine)
        sheet_names = xls.sheet_names
        if not sheet_names:
            raise EmptyDataError("The uploaded workbook has no worksheets.")

        target_sheet = _pick_compile_sheet(sheet_names)
        df = xls.parse(target_sheet)
        if df.empty:
            raise EmptyDataError(
                f"The detected sheet '{target_sheet}' has no data rows."
            )
        return df, target_sheet, sheet_names
    except (UnsupportedFileError, EmptyDataError):
        raise
    except Exception as exc:  # noqa: BLE001 - convert every parse failure to a friendly error
        raise CorruptFileError(
            "Could not read the uploaded file. It may be corrupted or in an "
            "unsupported format."
        ) from exc
