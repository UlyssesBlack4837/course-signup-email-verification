from datetime import datetime, timedelta, timezone

from edtech_verification.verification_flow import VerificationFlow


class RecordingEmailClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def send_verification(self, **request: str) -> str:
        self.calls.append(request)
        return "msg_course_42"


def test_deadline_blocks_delivery_and_appears_in_educator_report() -> None:
    client = RecordingEmailClient()
    flow = VerificationFlow(client, "https://learn.example")  # type: ignore[arg-type]
    now = datetime(2026, 8, 13, 12, tzinfo=timezone.utc)

    decision = flow.start(
        signup_id="signup-42",
        learner_email="learner@example.com",
        course_title="Python 101",
        enrollment_deadline=now - timedelta(minutes=1),
        now=now,
    )

    assert decision.state == "deadline_passed"
    assert decision.message_id is None
    assert client.calls == []
    assert flow.educator_report()[0]["state"] == "deadline_passed"


def test_open_enrollment_sends_a_course_specific_link() -> None:
    client = RecordingEmailClient()
    flow = VerificationFlow(client, "https://learn.example")  # type: ignore[arg-type]
    now = datetime(2026, 8, 13, 12, tzinfo=timezone.utc)

    decision = flow.start(
        signup_id="signup-43",
        learner_email="learner@example.com",
        course_title="Python 101",
        enrollment_deadline=now + timedelta(days=1),
        now=now,
    )

    assert decision.state == "verification_sent"
    assert decision.message_id == "msg_course_42"
    assert decision.verification_url == client.calls[0]["verification_url"]
    assert decision.verification_url.startswith(
        "https://learn.example/verify-email?token="
    )

