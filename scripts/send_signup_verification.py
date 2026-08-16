from datetime import datetime, timedelta, timezone
import os

from edtech_verification.verification_flow import InfraiEmailClient, VerificationFlow


recipient = os.environ.get("DEMO_LEARNER_EMAIL")
if not recipient:
    raise RuntimeError("DEMO_LEARNER_EMAIL is required")

flow = VerificationFlow(
    InfraiEmailClient(), os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000")
)
result = flow.start(
    signup_id="python-101-demo",
    learner_email=recipient,
    course_title="Python 101",
    enrollment_deadline=datetime.now(timezone.utc) + timedelta(days=2),
)
print(result)

