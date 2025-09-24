"""Counter service implementing reuse-or-generate workflow."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from .ports import COUNTER_PREFIX, AcademicYearProvider, CounterMetrics, CounterRecord, CounterRepository

LOGGER = logging.getLogger(__name__)
COUNTER_REGEX = re.compile(r"^\d{2}(357|373)\d{4}$")
NATIONAL_ID_REGEX = re.compile(r"^\d{10}$")
YEAR_CODE_REGEX = re.compile(r"^\d{2}$")


@dataclass(frozen=True)
class CounterServiceError(Exception):
    """Base error carrying structured metadata for clients."""

    code: str
    message_fa: str
    details: dict[str, str] | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code}: {self.message_fa}"

    def to_payload(self) -> dict[str, object]:
        """Return the JSON payload defined by the error contract."""

        payload: dict[str, object] = {"code": self.code, "message_fa": self.message_fa}
        if self.details:
            payload["details"] = self.details
        return payload


class CounterValidationError(CounterServiceError):
    """Raised when inputs fail validation."""


class CounterExhaustedError(CounterServiceError):
    """Raised when no more sequence numbers are available for a key."""


class CounterConflictError(CounterServiceError):
    """Raised when repository conflicts cannot be resolved automatically."""


@dataclass
class CounterService:
    """Pure domain service responsible for deterministic counter allocation."""

    repository: CounterRepository
    year_provider: AcademicYearProvider
    metrics: CounterMetrics
    pii_hash_salt: str

    def get_or_create(self, national_id: str, gender: Literal[0, 1]) -> str:
        """Return an existing counter or create a new one for ``national_id``."""

        correlation_id = uuid4().hex
        validated_national_id = self._validate_national_id(national_id)
        validated_gender = self._validate_gender(gender)
        year_code = self._validate_year_code(self.year_provider.current_year_code())
        hashed_id = self._hash_pii(validated_national_id)

        record = self.repository.get_prior_counter(validated_national_id)
        if record:
            self.metrics.observe_reuse(year=year_code, gender=validated_gender)
            self._log_event(
                "counter_reused",
                correlation_id=correlation_id,
                national_id_hash=hashed_id,
                counter=record.counter,
                year_code=record.year_code,
                requested_year=year_code,
            )
            if record.year_code != year_code:
                self._log_event(
                    "W_COUNTER_OLD_YEAR_REUSED",
                    correlation_id=correlation_id,
                    national_id_hash=hashed_id,
                    counter=record.counter,
                    original_year=record.year_code,
                    requested_year=year_code,
                )
            return record.counter

        prefix = COUNTER_PREFIX[validated_gender]
        sequence = self.repository.reserve_next_sequence(year_code, prefix)
        if sequence < 1:
            raise CounterConflictError(
                code="E_DB_CONFLICT",
                message_fa="خطای داخلی بانک اطلاعاتی در رزرو توالی.",
                details={"year_code": year_code, "prefix": prefix},
            )
        if sequence > 9999:
            self.metrics.observe_overflow(year=year_code, gender=validated_gender)
            self._log_event(
                "counter_overflow",
                correlation_id=correlation_id,
                national_id_hash=hashed_id,
                year_code=year_code,
                prefix=prefix,
                sequence=str(sequence),
            )
            raise CounterExhaustedError(
                code="E_COUNTER_EXHAUSTED",
                message_fa="ظرفیت توالی سال/پیشوند تکمیل شده است.",
                details={"year_code": year_code, "prefix": prefix},
            )
        self.metrics.record_sequence_position(year=year_code, prefix=prefix, sequence=sequence)

        counter = f"{year_code}{prefix}{sequence:04d}"
        if not COUNTER_REGEX.fullmatch(counter):
            raise CounterValidationError(
                code="E_COUNTER_PATTERN_INVALID",
                message_fa="قالب شماره تخصیص‌یافته نامعتبر است.",
                details={"counter": counter},
            )

        ledger_record = CounterRecord(
            national_id=validated_national_id,
            counter=counter,
            year_code=year_code,
            created_at=None,
        )

        try:
            stored = self.repository.bind_ledger(ledger_record)
        except CounterConflictError as conflict:
            self.metrics.observe_conflict(conflict_type="ledger_conflict")
            raise conflict
        except CounterServiceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            self.metrics.observe_conflict(conflict_type="ledger_exception")
            raise CounterConflictError(
                code="E_DB_CONFLICT",
                message_fa="ثبت رکورد در دفترچه با خطا مواجه شد.",
                details={"year_code": year_code, "prefix": prefix},
            ) from exc

        if stored.counter != counter:
            # A concurrent writer beat us: reuse stored value.
            self.metrics.observe_conflict(conflict_type="ledger_race")
            self._log_event(
                "counter_race",
                correlation_id=correlation_id,
                national_id_hash=hashed_id,
                generated_counter=counter,
                persisted_counter=stored.counter,
            )
            return stored.counter

        self.metrics.observe_generation(year=year_code, gender=validated_gender)
        self._log_event(
            "counter_generated",
            correlation_id=correlation_id,
            national_id_hash=hashed_id,
            counter=stored.counter,
            year_code=year_code,
            prefix=prefix,
            sequence=f"{sequence:04d}",
        )
        return stored.counter

    def _validate_national_id(self, national_id: str | None) -> str:
        if not isinstance(national_id, str) or not NATIONAL_ID_REGEX.fullmatch(national_id):
            raise CounterValidationError(
                code="E_INVALID_NID",
                message_fa="شناسه ملی باید شامل ۱۰ رقم باشد.",
                details={"national_id": str(national_id)},
            )
        return national_id

    def _validate_gender(self, gender: int | None) -> Literal[0, 1]:
        if gender not in COUNTER_PREFIX:
            raise CounterValidationError(
                code="E_INVALID_GENDER",
                message_fa="جنسیت نامعتبر است (صرفاً ۰ یا ۱ مجاز است).",
                details={"gender": str(gender)},
            )
        return gender  # type: ignore[return-value]

    def _validate_year_code(self, year_code: str | None) -> str:
        if not isinstance(year_code, str) or not YEAR_CODE_REGEX.fullmatch(year_code):
            raise CounterValidationError(
                code="E_YEAR_CODE_INVALID",
                message_fa="کد سال تحصیلی باید شامل دو رقم باشد.",
                details={"year_code": str(year_code)},
            )
        return year_code

    def _hash_pii(self, national_id: str) -> str:
        digest = sha256(f"{self.pii_hash_salt}{national_id}".encode("utf-8"))
        return digest.hexdigest()

    def _log_event(self, event: str, **kwargs: str) -> None:
        payload = {"event": event}
        for key, value in kwargs.items():
            if key in {"counter", "generated_counter", "persisted_counter"} and isinstance(value, str):
                payload[key] = self._mask_counter(value)
            else:
                payload[key] = value
        if "correlation_id" not in payload:
            payload["correlation_id"] = uuid4().hex
        LOGGER.info(json.dumps(payload, ensure_ascii=False))

    @staticmethod
    def _mask_counter(counter: str) -> str:
        return f"{counter[:3]}****{counter[-2:]}"
