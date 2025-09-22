"""Wrapper utilities around pandas for Excel operations."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

try:  # pragma: no cover - optional dependency
    import pandas as pd
except ImportError:  # pragma: no cover - fallback for test environment
    pd = None  # type: ignore[assignment]


class ExcelHandler:
    """Read and write helper for Excel files."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _require_pandas(self) -> None:
        if pd is None:
            raise ImportError(
                "pandas is required for Excel operations. Install the optional "
                "dependency with `pip install pandas openpyxl`."
            )

    def read_sheet(self, sheet_name: Optional[str] = None) -> "pd.DataFrame":
        """Return a dataframe for the given sheet."""

        self._require_pandas()
        return pd.read_excel(self.path, sheet_name=sheet_name)

    def read_all(self) -> dict[str, "pd.DataFrame"]:
        """Read all sheets from the workbook."""

        self._require_pandas()
        return pd.read_excel(self.path, sheet_name=None)

    def write_sheet(self, data: "pd.DataFrame", sheet_name: str) -> None:
        """Write a dataframe to an Excel sheet."""

        self._require_pandas()
        with pd.ExcelWriter(self.path, engine="openpyxl", mode="a" if self.path.exists() else "w") as writer:
            data.to_excel(writer, sheet_name=sheet_name, index=False)

    @staticmethod
    def combine(workbooks: Iterable[Path]) -> "pd.DataFrame":
        """Combine rows from multiple Excel files into a single dataframe."""

        if pd is None:
            raise ImportError(
                "pandas is required for Excel operations. Install the optional "
                "dependency with `pip install pandas openpyxl`."
            )

        frames = [pd.read_excel(book) for book in workbooks]
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)
