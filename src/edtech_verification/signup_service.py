from __future__ import annotations

import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from .verification_flow import InfraiEmailClient, InfraiError, VerificationFlow


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signup_id: str
    learner_email: str
    course_title: str
    enrollment_deadline: datetime


class SignupResponse(BaseModel):
    signup_id: str
    state: str
    message_id: str | None
    verification_url: str | None


def create_app(flow: VerificationFlow | None = None) -> FastAPI:
    app = FastAPI(title="Course email verification")
    workflow = flow or VerificationFlow(
        InfraiEmailClient(),
        os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000"),
    )

    @app.post("/signups", response_model=SignupResponse)
    def create_signup(request: SignupRequest) -> SignupResponse:
        try:
            decision = workflow.start(**request.model_dump())
        except InfraiError as exc:
            caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
            raise HTTPException(
                status_code=caller_status,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        return SignupResponse(**decision.__dict__)

    @app.get("/educator/reports/signups")
    def educator_signup_report() -> list[dict[str, object]]:
        return workflow.educator_report()

    return app


app = create_app()

