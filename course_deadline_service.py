"""Course deadline fanout with a compact educator-facing report."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Protocol

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from infrai_client import InfraiClient, InfraiError


class LearnerDeadline(BaseModel):
    learner_id: str
    notification_target: str
    due_on: date
    completed: bool = False


class CourseDelivery(BaseModel):
    course_id: str
    course_title: str
    as_of: date
    remind_within_days: Annotated[int, Field(ge=0, le=30)] = 3
    learners: list[LearnerDeadline]


class EducatorReport(BaseModel):
    course_id: str
    considered: int
    queued: int
    learner_ids: list[str]


class NotificationPublisher(Protocol):
    def publish_notification(
        self, payload: dict[str, object], *, idempotency_key: str
    ) -> None:
        """Publish one learner notification with a stable request identity."""


def fan_out_deadlines(
    delivery: CourseDelivery, publisher: NotificationPublisher
) -> EducatorReport:
    selected = sorted(
        (
            learner
            for learner in delivery.learners
            if not learner.completed
            and 0 <= (learner.due_on - delivery.as_of).days <= delivery.remind_within_days
        ),
        key=lambda learner: learner.learner_id,
    )
    for learner in selected:
        publisher.publish_notification(
            {
                "course_id": delivery.course_id,
                "course_title": delivery.course_title,
                "learner_id": learner.learner_id,
                "notification_target": learner.notification_target,
                "due_on": learner.due_on.isoformat(),
            },
            idempotency_key=(
                f"deadline:{delivery.course_id}:{learner.learner_id}:{learner.due_on}"
            ),
        )
    return EducatorReport(
        course_id=delivery.course_id,
        considered=len(delivery.learners),
        queued=len(selected),
        learner_ids=[learner.learner_id for learner in selected],
    )


def get_client() -> InfraiClient:
    return InfraiClient()


app = FastAPI(title="Course deadline fanout")


@app.exception_handler(InfraiError)
async def infrai_error_response(_request: Request, error: InfraiError) -> JSONResponse:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return JSONResponse(status_code=status, content={"error": error.detail})


@app.post("/course-deadlines", response_model=EducatorReport)
def deliver_course_deadlines(
    delivery: CourseDelivery, client: InfraiClient = Depends(get_client)
) -> EducatorReport:
    return fan_out_deadlines(delivery, client)


@app.post("/schedules", response_model=dict[str, str])
def create_schedule(
    cron_expr: str,
    task: str,
    client: InfraiClient = Depends(get_client),
) -> dict[str, str]:
    return {"job_id": client.schedule_deadline_delivery(cron_expr, task)}
