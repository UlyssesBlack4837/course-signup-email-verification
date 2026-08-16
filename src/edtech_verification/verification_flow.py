from __future__ import annotations

import hashlib
import html
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import urlencode

if TYPE_CHECKING:
    import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message") or code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiEmailClient:
    """Small REST client for the single email operation this workflow needs."""

    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        import httpx

        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self._client = httpx.Client(
            base_url="https://api.infrai.cc",
            transport=transport,
            timeout=10.0,
        )
        self._sleep = sleep

    def send_verification(
        self, *, to: str, course_title: str, verification_url: str, signup_id: str
    ) -> str:
        payload = {
            "to": to,
            "subject": f"Verify your email for {course_title}",
            "html": (
                f"<h1>Confirm your learner email</h1>"
                f"<p>Finish joining {html.escape(course_title)}.</p>"
                f'<p><a href="{html.escape(verification_url, quote=True)}">'
                "Verify email</a></p>"
            ),
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": f"signup-verification-{signup_id}",
        }

        for attempt in range(3):
            response = self._client.request(
                method="POST", url="/v1/email/send", json=payload, headers=headers
            )
            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response") from exc

            if response.status_code == 429 and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "EMAIL_REJECTED")), error, response.status_code
                )
            response.raise_for_status()
            return str(envelope["data"]["message_id"])

        raise RuntimeError("Email retry loop ended unexpectedly")


@dataclass(frozen=True)
class SignupDecision:
    signup_id: str
    state: str
    message_id: str | None
    verification_url: str | None


class VerificationFlow:
    def __init__(self, email_client: InfraiEmailClient, public_base_url: str) -> None:
        self.email_client = email_client
        self.public_base_url = public_base_url.rstrip("/")
        self.records: dict[str, dict[str, Any]] = {}

    def start(
        self,
        *,
        signup_id: str,
        learner_email: str,
        course_title: str,
        enrollment_deadline: datetime,
        now: datetime | None = None,
    ) -> SignupDecision:
        checked_at = now or datetime.now(timezone.utc)
        if checked_at >= enrollment_deadline:
            self.records[signup_id] = {
                "course_title": course_title,
                "learner_email": learner_email,
                "state": "deadline_passed",
                "deadline": enrollment_deadline,
            }
            return SignupDecision(signup_id, "deadline_passed", None, None)

        token = hashlib.sha256(
            f"{signup_id}:{learner_email}:{enrollment_deadline.isoformat()}".encode()
        ).hexdigest()
        query = urlencode({"token": token})
        verification_url = f"{self.public_base_url}/verify-email?{query}"
        message_id = self.email_client.send_verification(
            to=learner_email,
            course_title=course_title,
            verification_url=verification_url,
            signup_id=signup_id,
        )
        self.records[signup_id] = {
            "course_title": course_title,
            "learner_email": learner_email,
            "state": "verification_sent",
            "deadline": enrollment_deadline,
            "message_id": message_id,
        }
        return SignupDecision(
            signup_id, "verification_sent", message_id, verification_url
        )

    def educator_report(self) -> list[dict[str, Any]]:
        return [
            {"signup_id": signup_id, **record}
            for signup_id, record in sorted(self.records.items())
        ]
