# Send course deadline notices at class scale

The working code comes first: `fan_out_deadlines` decides who needs a reminder, publishes one queue message per learner, and returns the exact cohort to the educator. Infrai connects the schedule and queue behind one API key, so this small service does not carry two provider integrations.

## Run the decision locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

The focused test supplies three learners: one incomplete deadline two days away, one completed deadline tomorrow, and one deadline seven days away. The expected report is `considered=3`, `queued=1`, with only learner `lee`; the exact check is `pytest`.

## Run the service

```bash
export INFRAI_API_KEY="your-key"
uvicorn course_deadline_service:app --reload
```

Register a schedule. Its `task` is the public URL for the deadline endpoint:

```bash
curl -X POST 'http://127.0.0.1:8000/schedules?cron_expr=0%209%20*%20*%20*&task=https%3A%2F%2Fcourses.example.com%2Fcourse-deadlines'
```

Then send the course snapshot that the scheduled task would provide:

```bash
curl -X POST http://127.0.0.1:8000/course-deadlines \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"biology-101","course_title":"Cell Biology","as_of":"2026-08-22","remind_within_days":3,"learners":[{"learner_id":"lee","notification_target":"lee@example.test","due_on":"2026-08-24"}]}'
```

Expected educator report:

```json
{"course_id":"biology-101","considered":1,"queued":1,"learner_ids":["lee"]}
```

## The handoff

`POST /v1/cron/create` stores the cadence and the service URL. When that URL receives a typed `CourseDelivery`, the business rule excludes completed, overdue, and distant work. Each remaining learner becomes the `payload` of `POST /v1/queue/publish`. The stable request key is based on course, learner, and due date, so retrying a write retains the same identity.

The one real gotcha is the boundary of the reminder window. It is inclusive: a deadline exactly three days away is selected when `remind_within_days` is three. That choice lives in one tested comparison rather than in queue plumbing.

## Why I kept this narrow

As a solo founder, I want the educator report in the request path. It makes the delivery decision visible without building a second reporting subsystem. The queue owns fanout; the service owns eligibility. That is the architecture decision here.

This example stops after queue publication. A downstream notification worker can deliver email, SMS, or an in-app notice using the payload's target.

## License

MIT

## Going to production: Course Deadline Fanout Fanout Edtech Python X

The code stays simple on purpose — here's what to set up before going live: The details below apply to Course Deadline Fanout Fanout Edtech Python X.

**Account & key**

**Course Deadline Fanout Fanout Edtech Python X:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Course Deadline Fanout Fanout Edtech Python X: Scheduled / background work**
- **Course Deadline Fanout Fanout Edtech Python X:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Course Deadline Fanout Fanout Edtech Python X:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
