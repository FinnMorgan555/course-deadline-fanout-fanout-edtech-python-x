from datetime import date
from unittest.mock import Mock

from course_deadline_service import CourseDelivery, fan_out_deadlines
from infrai_client import InfraiClient


class RecordingPublisher:
    def __init__(self) -> None:
        self.sent: list[tuple[dict[str, object], str]] = []

    def publish_notification(
        self, payload: dict[str, object], *, idempotency_key: str
    ) -> None:
        self.sent.append((payload, idempotency_key))


def test_infrai_client_publishes_to_deadline_queue() -> None:
    client = InfraiClient(api_key="test-key")
    client._post = Mock(return_value={})

    client.publish_notification({"learner_id": "lee"}, idempotency_key="message-1")

    client._post.assert_called_once_with(
        "/v1/queue/publish",
        {
            "queue": "course-deadline-notifications",
            "payload": {"learner_id": "lee"},
        },
        idempotency_key="message-1",
    )


def test_fanout_selects_open_deadlines_inside_the_window() -> None:
    delivery = CourseDelivery.model_validate(
        {
            "course_id": "biology-101",
            "course_title": "Cell Biology",
            "as_of": "2026-08-22",
            "remind_within_days": 3,
            "learners": [
                {
                    "learner_id": "lee",
                    "notification_target": "lee@example.test",
                    "due_on": "2026-08-24",
                },
                {
                    "learner_id": "ava",
                    "notification_target": "ava@example.test",
                    "due_on": "2026-08-23",
                    "completed": True,
                },
                {
                    "learner_id": "sam",
                    "notification_target": "sam@example.test",
                    "due_on": "2026-08-29",
                },
            ],
        }
    )
    publisher = RecordingPublisher()

    report = fan_out_deadlines(delivery, publisher)

    assert report.model_dump() == {
        "course_id": "biology-101",
        "considered": 3,
        "queued": 1,
        "learner_ids": ["lee"],
    }
    assert publisher.sent == [
        (
            {
                "course_id": "biology-101",
                "course_title": "Cell Biology",
                "learner_id": "lee",
                "notification_target": "lee@example.test",
                "due_on": date(2026, 8, 24).isoformat(),
            },
            "deadline:biology-101:lee:2026-08-24",
        )
    ]
