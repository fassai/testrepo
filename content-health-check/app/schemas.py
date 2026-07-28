"""Request/response models. The form IS the lead capture — results are gated behind it."""
import re

from pydantic import BaseModel, Field, field_validator, model_validator

_HANDLE_RE = re.compile(r"^[A-Za-z0-9._\-]{2,60}$")


def clean_handle(v: str | None) -> str | None:
    """Accept '@name', full profile URLs, or bare handles; normalize to bare handle."""
    if not v:
        return None
    v = v.strip()
    v = re.sub(r"^https?://(www\.)?(instagram\.com|facebook\.com|tiktok\.com)/(@)?", "", v, flags=re.I)
    v = v.strip("@/ ").split("?")[0].split("/")[0]
    if not v:
        return None
    if not _HANDLE_RE.match(v):
        raise ValueError("invalid handle")
    return v


class CheckupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    business_name: str = Field(min_length=1, max_length=160)
    sell_to: str = Field(min_length=1, max_length=300)
    industry: str = Field(min_length=1, max_length=160)
    ig_handle: str | None = Field(default=None, max_length=200)
    fb_handle: str | None = Field(default=None, max_length=200)
    tiktok_handle: str | None = Field(default=None, max_length=200)
    competitor_handle: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    line_id: str | None = Field(default=None, max_length=100)

    @field_validator("ig_handle", "fb_handle", "tiktok_handle", "competitor_handle")
    @classmethod
    def _handles(cls, v):
        return clean_handle(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        if v is None or not v.strip():
            return None
        v = v.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("invalid email")
        return v

    @model_validator(mode="after")
    def _gates(self):
        # Lead gate: must leave email or LINE to see results.
        if not self.email and not (self.line_id and self.line_id.strip()):
            raise ValueError("ต้องกรอกอีเมลหรือ LINE ID อย่างน้อย 1 ช่อง")
        # Need at least one own-channel handle to have anything to check.
        if not (self.ig_handle or self.fb_handle or self.tiktok_handle):
            raise ValueError("ต้องกรอก social handle ของธุรกิจอย่างน้อย 1 ช่องทาง")
        return self

    @property
    def primary_handle(self) -> str:
        return self.ig_handle or self.tiktok_handle or self.fb_handle  # type: ignore[return-value]
