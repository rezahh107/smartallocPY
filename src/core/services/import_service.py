"""Service layer responsible for ingesting external files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from ..models.student import Student
from ..utils.excel_handler import ExcelHandler
from ..utils.persian_normalizer import normalize_persian_text
from ..utils.mobile_normalizer import normalize_mobile_number


class ImportService:
    """Import student data from Excel workbooks."""

    def __init__(self, path: Path) -> None:
        self.handler = ExcelHandler(path)

    def load_students(self, sheet_name: str | None = None) -> List[Student]:
        """Load students from the given sheet."""

        dataframe = self.handler.read_sheet(sheet_name=sheet_name)
        students: List[Student] = []
        for record in dataframe.to_dict(orient="records"):
            record["first_name"] = normalize_persian_text(record.get("first_name"))
            record["last_name"] = normalize_persian_text(record.get("last_name"))
            record["mobile_number"] = normalize_mobile_number(record.get("mobile_number"))
            students.append(Student(**record))
        return students

    @staticmethod
    def load_multiple(files: Iterable[Path]) -> List[Student]:
        """Load and combine students from multiple Excel files."""

        combined: List[Student] = []
        for path in files:
            combined.extend(ImportService(path).load_students())
        return combined
