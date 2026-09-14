"""In-process data store.

Per the prompt's performance section: load -> clean -> derive -> CACHE once,
then filter/aggregate per-request from the cached frame. This is intentionally
a simple in-memory singleton (pandas) for v1; the service layer below does not
assume this and could be swapped for a DuckDB/Postgres-backed store later
without changing the API layer.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd


@dataclass
class DatasetMeta:
    filename: str
    uploaded_at: datetime
    sheet_used: str
    all_sheets: list[str]
    total_records: int
    date_range: tuple[Optional[str], Optional[str]]
    num_projects: int
    num_categories: int
    num_open: int
    num_closed: int
    data_quality: dict = field(default_factory=dict)
    unmapped_categories: list = field(default_factory=list)
    unmapped_statuses: list = field(default_factory=list)
    as_of: Optional[str] = None


class DataStore:
    _lock = threading.Lock()

    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.meta: Optional[DatasetMeta] = None

    def set(self, df: pd.DataFrame, meta: DatasetMeta):
        with self._lock:
            self.df = df
            self.meta = meta

    def is_loaded(self) -> bool:
        return self.df is not None

    def get(self) -> tuple[pd.DataFrame, DatasetMeta]:
        if self.df is None or self.meta is None:
            raise RuntimeError("No dataset uploaded yet.")
        return self.df, self.meta


store = DataStore()
