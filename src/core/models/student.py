"""مدل پایدانتیک برای نمایش دانش‌آموز در سامانه تخصیص منتور."""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Dict, Optional

import re
from persiantools import characters, digits
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class Student(BaseModel):
    """مدل دامنه‌ای دانش‌آموز برای فاز نخست تخصیص منتور.

    این مدل با تکیه بر نیازهای فاز نخست سامانهٔ تخصیص، دادهٔ خام دانش‌آموز را
    نرمال‌سازی و اعتبارسنجی می‌کند تا برای پردازش‌های دسته‌ای با حجم بالای
    داده آماده شود.

    Attributes:
        national_id: کد ملی یکتا با کنترل صحت و چک‌سام.
        first_name: نام به صورت فارسی استانداردسازی‌شده.
        last_name: نام خانوادگی به صورت فارسی استانداردسازی‌شده.
        gender: شناسهٔ جنسیت (۰ برای دختر، ۱ برای پسر).
        edu_status: وضعیت تحصیلی (۰ فارغ‌التحصیل، ۱ محصل).
        reg_center: مرکز ثبت‌نام مجاز (۰، ۱ یا ۲).
        reg_status: وضعیت ثبت‌نام مجاز (۰، ۱ یا ۳).
        group_code: شناسهٔ گروه از جدول هم‌ارز.
        school_code: کد مدرسه در صورت وجود.
        mobile: شمارهٔ همراه نرمال‌سازی‌شده با پیش‌شمارهٔ ۰۹.
        counter: شمارندهٔ اختیاری مطابق الگوی ۹ رقمی تعریف‌شده.
        created_at: زمان ایجاد رکورد.
    """

    __slots__ = ()

    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    _non_digit_re: ClassVar[re.Pattern[str]] = re.compile(r"\D+")
    _multi_space_re: ClassVar[re.Pattern[str]] = re.compile(r"\s+")
    _counter_re: ClassVar[re.Pattern[str]] = re.compile(r"^(\d{2})(357|373)(\d{4})$")

    national_id: str = Field(..., description="کد ملی ۱۰ رقمی")
    first_name: str = Field(..., description="نام فارسی دانش‌آموز")
    last_name: str = Field(..., description="نام خانوادگی فارسی دانش‌آموز")
    gender: int = Field(..., description="جنسیت: ۰ برای دختر، ۱ برای پسر")
    edu_status: int = Field(..., description="وضعیت تحصیلی: ۰ فارغ‌التحصیل، ۱ محصل")
    reg_center: int = Field(..., description="مرکز ثبت‌نام مجاز (۰، ۱ یا ۲)")
    reg_status: int = Field(..., description="وضعیت ثبت‌نام مجاز (۰، ۱ یا ۳)")
    group_code: int = Field(..., description="کد گروه تخصیص")
    school_code: Optional[int] = Field(None, description="کد مدرسه در صورت وجود")
    mobile: str = Field(..., description="شمارهٔ همراه نرمال")
    counter: Optional[str] = Field(None, description="شمارندهٔ ۹ رقمی اختیاری")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="زمان ایجاد")

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _normalize_persian_text(cls, value: Any) -> str:
        """متن ورودی را برای نام‌ها به قالب فارسی یکنواخت تبدیل می‌کند."""

        if value is None:
            return ""
        text = str(value)
        text = characters.ar_to_fa(text)
        text = digits.ar_to_fa(text)
        text = cls._multi_space_re.sub(" ", text.strip())
        return text

    @field_validator("first_name", "last_name")
    @classmethod
    def _ensure_not_empty(cls, value: str) -> str:
        """اطمینان از خالی نبودن مقدار پس از نرمال‌سازی."""

        if not value:
            raise ValueError("این مقدار نباید خالی باشد")
        return value

    @field_validator("national_id", mode="before")
    @classmethod
    def _clean_national_id(cls, value: Any) -> str:
        """غیردیجیت‌ها را حذف و طول کد ملی را کنترل می‌کند."""

        if value is None:
            raise ValueError("کد ملی باید دقیقاً ۱۰ رقم باشد")
        digits_only = cls._non_digit_re.sub("", str(value))
        if len(digits_only) != 10:
            raise ValueError("کد ملی باید دقیقاً ۱۰ رقم باشد")
        return digits_only

    @field_validator("national_id")
    @classmethod
    def _validate_national_id(cls, value: str) -> str:
        """قوانین اختصاصی کد ملی ایران را اعمال می‌کند."""

        if value == value[0] * 10:
            raise ValueError("کد ملی معتبر نیست - چک‌سام نادرست")
        digits_list = [int(char) for char in value]
        checksum = digits_list[-1]
        total = sum(digits_list[i] * (10 - i) for i in range(9))
        remainder = total % 11
        if remainder < 2:
            expected = remainder
        else:
            expected = 11 - remainder
        if checksum != expected:
            raise ValueError("کد ملی معتبر نیست - چک‌سام نادرست")
        return value

    @field_validator("mobile", mode="before")
    @classmethod
    def _normalize_mobile(cls, value: Any) -> str:
        """شمارهٔ همراه را به قالب ۰۹XXXXXXXXX تبدیل می‌کند."""

        if value is None:
            raise ValueError("شماره موبایل باید با ۰۹ شروع شده و ۱۱ رقمی باشد")
        text = str(value).strip()
        text = digits.fa_to_en(digits.ar_to_fa(text))
        text = re.sub(r"[\s\-()]+", "", text)
        if text.startswith("+"):
            text = text[1:]
        if text.startswith("00"):
            text = text[2:]
        if text.startswith("98"):
            text = text[2:]
        if text.startswith("9") and len(text) == 10:
            text = f"0{text}"
        if not text.startswith("0"):
            text = f"0{text}"
        return text

    @field_validator("mobile")
    @classmethod
    def _validate_mobile(cls, value: str) -> str:
        """صحت طول و الگوی شمارهٔ همراه را بررسی می‌کند."""

        if not re.fullmatch(r"09\d{9}", value):
            raise ValueError("شماره موبایل باید با ۰۹ شروع شده و ۱۱ رقمی باشد")
        return value

    @field_validator("gender")
    @classmethod
    def _validate_gender(cls, value: int) -> int:
        """مقادیر مجاز برای جنسیت را بررسی می‌کند."""

        if value not in {0, 1}:
            raise ValueError("مقدار جنسیت باید یکی از {۰، ۱} باشد")
        return value

    @field_validator("edu_status")
    @classmethod
    def _validate_edu_status(cls, value: int) -> int:
        """مقدار وضعیت تحصیلی را محدود می‌کند."""

        if value not in {0, 1}:
            raise ValueError("مقدار وضعیت تحصیلی باید یکی از {۰، ۱} باشد")
        return value

    @field_validator("reg_center")
    @classmethod
    def _validate_reg_center(cls, value: int) -> int:
        """مقدار مرکز ثبت‌نام را کنترل می‌کند."""

        if value not in {0, 1, 2}:
            raise ValueError("مقدار مرکز ثبت‌نام باید یکی از {۰، ۱، ۲} باشد")
        return value

    @field_validator("reg_status")
    @classmethod
    def _validate_reg_status(cls, value: int) -> int:
        """مقدار وضعیت ثبت‌نام را کنترل می‌کند."""

        if value not in {0, 1, 3}:
            raise ValueError("مقدار وضعیت ثبت‌نام باید یکی از {۰، ۱، ۳} باشد")
        return value

    @field_validator("counter", mode="before")
    @classmethod
    def _normalize_counter(cls, value: Any) -> Optional[str]:
        """شمارندهٔ اختیاری را پاک‌سازی و اعتبارسنجی می‌کند."""

        if value in {None, ""}:
            return None
        text = str(value).strip()
        text = digits.fa_to_en(digits.ar_to_fa(text))
        text = cls._non_digit_re.sub("", text)
        if not text:
            return None
        if not cls._counter_re.fullmatch(text):
            raise ValueError("شمارنده باید با الگوی YY357#### یا YY373#### منطبق باشد")
        return text

    @computed_field
    @property
    def display_name(self) -> str:
        """نام کامل به صورت «نام خانوادگی، نام»"""

        return f"{self.last_name}، {self.first_name}".strip("، ")

    @computed_field
    @property
    def student_type(self) -> int:
        """تشخیص نوع دانش‌آموز بر اساس وجود کد مدرسه."""

        return 1 if self.school_code is not None else 0

    @property
    def full_name(self) -> str:
        """نام کامل را به صورت «نام نام خانوادگی» بازمی‌گرداند."""

        return f"{self.first_name} {self.last_name}".strip()

    def is_assignable(self) -> bool:
        """بررسی می‌کند آیا دانش‌آموز شرایط تخصیص منتور را دارد یا خیر."""

        return self.reg_status in {0, 1}

    def to_dict(self) -> Dict[str, Any]:
        """بازنمایی دیکشنری بدون فیلدهای محاسبه‌شده را برمی‌گرداند."""

        return self.model_dump(exclude={"display_name", "student_type"})
