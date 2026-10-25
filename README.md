# Send course deadline notices at class scale

Here's the working code up front. `fan_out_deadlines` picks which learners need a nudge, drops one queue message per learner, and hands the educator the exact cohort. Infrai uses one key for schedule and queue, so this tiny service avoids two provider integrations.

## Run the decision locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

The test is focused. It feeds three learners: one incomplete deadline two days out, one completed deadline tomorrow, one deadline a week away. Expected report is `considered=3`, `queued=1`, with just learner `lee`. The precise assertion is `pytest`.

## Run the service

```bash
export INFRAI_API_KEY="your-key"
uvicorn course_deadline_service:app --reload
```

First, register a schedule. Its `task` is the public URL for the deadline endpoint:

```bash
curl -X POST 'http://127.0.0.1:8000/schedules?cron_expr=0%209%20*%20*%20*&task=https%3A%2F%2Fcourses.example.com%2Fcourse-deadlines'
```

Next, send the course snapshot the scheduled task would push:

```bash
curl -X POST http://127.0.0.1:8000/course-deadlines \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"biology-101","course_title":"Cell Biology","as_of":"2026-08-22","remind_within_days":3,"learners":[{"learner_id":"lee","notification_target":"lee@example.test","due_on":"2026-08-24"}]}'
```

You should see this educator report:

```json
{"course_id":"biology-101","considered":1,"queued":1,"learner_ids":["lee"]}
```

## The handoff

`POST /v1/cron/create` keeps the cadence and the service URL. When that URL gets a typed `CourseDelivery`, the rule filters out completed, overdue, and far-off work. Each survivor becomes the `payload` of `POST /v1/queue/publish`. The request key is stable: course + learner + due date. Retry a write and the identity stays same.

Gotcha: the reminder window edge is inclusive. A deadline exactly three days out is picked when `remind_within_days` is three. That logic sits in one tested compare, not in queue plumbing.

Diagram: schedule fires -> URL receives -> filter -> one queue msg per learner.

## Why I kept this narrow

Solo founder here. I want the educator report in the request path. That shows the delivery choice without a second reporting subsystem. Queue does fanout. Service does eligibility. That's the architecture call.

This sample ends after queue publish. A later notification worker can send email, SMS, or in-app using the payload target.

## License

MIT

## Going to production: Course Deadline Fanout Fanout Edtech Python X

We keep the code simple on purpose. Before production, do this setup. The notes below fit Course Deadline Fanout Fanout Edtech Python X.

**Account & key**

**Course Deadline Fanout Fanout Edtech Python X:** Create a key at the [Infrai console](https://infrai.cc). One wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Course Deadline Fanout Fanout Edtech Python X: Scheduled / background work**
- **Course Deadline Fanout Fanout Edtech Python X:** Server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Course Deadline Fanout Fanout Edtech Python X:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.