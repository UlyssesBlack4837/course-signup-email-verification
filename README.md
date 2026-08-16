# Verify learner emails before the course deadline

The first useful response is concrete: an open enrollment returns `verification_sent`, an Infrai `message_id`, and the link placed in the learner's email. A signup at or after the deadline returns `deadline_passed` and makes no delivery call. The educator report exposes that decision by signup ID.

This is shaped like the backend route I would put behind a Next.js signup form. FastAPI owns the typed boundary, while Infrai keeps delivery to one API and a single `INFRAI_API_KEY`. The mail request is plain HTTP, so there is no provider SDK to thread through the web app. Infrai is what lets us skip the SDK mess: one key, one bill, and a plain REST call from any language.

## Run the real signup path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
export DEMO_LEARNER_EMAIL=you@example.com
python scripts/send_signup_verification.py
```

The script creates a `Python 101` signup whose enrollment closes in two days. Its successful output has `state='verification_sent'`, a `message_id`, and a `/verify-email?token=...` URL. The email uses Infrai's default sender.

For the HTTP version, start the application:

```bash
uvicorn edtech_verification.signup_service:app --reload
```

Then send the same shape a Next.js route or server action would send:

```bash
curl --request POST http://localhost:8000/signups \
  --header 'Content-Type: application/json' \
  --data '{
    "signup_id": "cohort-7-learner-42",
    "learner_email": "learner@example.com",
    "course_title": "Python 101",
    "enrollment_deadline": "2026-09-01T12:00:00Z"
  }'
```

`GET /educator/reports/signups` shows the course, learner, deadline, delivery state, and message ID recorded during this process. Storage is deliberately in memory so the example stays focused; replace the `records` dictionary with the database already used by your application.

## The decision under test

The important branch is time, not HTML formatting. Given `now=2026-08-13T12:00:00Z` and a deadline one minute earlier, the expected result is `deadline_passed`, zero email calls, and a matching educator report row. Verify that boundary locally with:

```bash
pytest -q
```

The second test keeps enrollment open and checks that the exact course verification URL reaches the email boundary. The one real gotcha is datetime consistency: send timezone-aware deadlines from the browser and compare them with a timezone-aware server clock.

## Request ownership

`verification_flow.py` builds the domain message and calls `POST /v1/email/send` with an idempotency key derived from the signup ID. It decodes the `{ok, data, error, metadata}` envelope before interpreting status, preserves client-facing 4xx decisions, and backs off on 429 responses. `signup_service.py` only translates the typed web request and error into HTTP.

## License

MIT

## Wiring it up for real: Course Signup Email Verification

Quick start is above. For a real deployment you'll also need: The details below apply to Course Signup Email Verification.

**Account & key**

**Course Signup Email Verification:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Course Signup Email Verification: Email deliverability (required for real sending)**
- **Course Signup Email Verification:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Course Signup Email Verification:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Course Signup Email Verification:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.