"""Wrapper utilities around pandas for Excel operations."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


class ExcelHandler:
    """Read and write helper for Excel files."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_sheet(self, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """Return a dataframe for the given sheet."""

        return pd.read_excel(self.path, sheet_name=sheet_name)

    def read_all(self) -> dict[str, pd.DataFrame]:
        """Read all sheets from the workbook."""

        return pd.read_excel(self.path, sheet_name=None)

    def write_sheet(self, data: pd.DataFrame, sheet_name: str) -> None:
        """Write a dataframe to an Excel sheet."""

        with pd.ExcelWriter(self.path, engine="openpyxl", mode="a" if self.path.exists() else "w") as writer:
            data.to_excel(writer, sheet_name=sheet_name, index=False)

    @staticmethod
    def combine(workbooks: Iterable[Path]) -> pd.DataFrame:
        """Combine rows from multiple Excel files into a single dataframe."""

        frames = [pd.read_excel(book) for book in workbooks]
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)
