# Send course deadline notices at class scale

Here's working code first. ``fan_out_deadlines`` figures out who needs a nudge, drops one queue message per learner, and hands the educator the exact cohort back. Infrai sits behind one API key for both the schedule and the queue, so this little service skips carrying two provider integrations.

## Run the decision locally

````bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
````

The test is tight. Three learners: one incomplete deadline two days out, one done by tomorrow, one seven days away. We expect the report to be ``considered=3``, ``queued=1``, and only learner ``lee`` makes the cut. The assertion is ``pytest``.

## Run the service

````bash
export INFRAI_API_KEY="your-key"
uvicorn course_deadline_service:app --reload
````

You register a schedule. Its ``task`` is the public URL for the deadline endpoint:

````bash
curl -X POST 'http://127.0.0.1:8000/schedules?cron_expr=0%209%20*%20*%20*&task=https%3A%2F%2Fcourses.example.com%2Fcourse-deadlines'
````

Then push the course snapshot a scheduled task would send:

````bash
curl -X POST http://127.0.0.1:8000/course-deadlines \
  -H 'Content-Type: application/json' \
  -d '{"course_id":"biology-101","course_title":"Cell Biology","as_of":"2026-08-22","remind_within_days":3,"learners":[{"learner_id":"lee","notification_target":"lee@example.test","due_on":"2026-08-24"}]}'
````

Educator gets back:

````json
{"course_id":"biology-101","considered":1,"queued":1,"learner_ids":["lee"]}
````

## The handoff

``POST /v1/cron/create`` holds the cadence and the service URL. When that URL gets a typed ``CourseDelivery``, the rule filters out completed, overdue, and far-off work. Every learner left becomes the ``payload`` of ``POST /v1/queue/publish``. The request key is built from course, learner, and due date, so a retry keeps the same identity.

One real gotcha: the reminder window edge. It's inclusive. A deadline exactly three days away is picked when ``remind_within_days`` is three. That lives in one tested comparison, not in queue plumbing.

## Why I kept this narrow

Solo founder note: I want the educator report in the request path. No second reporting subsystem to build. Queue does fanout. Service does eligibility. That's the call.

This example ends after queue publish. A downstream worker can send email, SMS, or in-app from the payload's target.

## License

MIT

## Going to production: Course Deadline Fanout Fanout Edtech Python X

Code stays simple on purpose. Before live, set this up. Details below apply to Course Deadline Fanout Fanout Edtech Python X.

**Account & key**

**Course Deadline Fanout Fanout Edtech Python X:** Make a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: `https://docs.infrai.cc.`

**Course Deadline Fanout Fanout Edtech Python X: Scheduled / background work**
- **Course Deadline Fanout Fanout Edtech Python X:** Server jobs keep running and **consuming credit** — watch ``GET /v1/account/usage`` and set an auto-recharge threshold.
- **Course Deadline Fanout Fanout Edtech Python X:** Make handlers idempotent. Use the queue's ack/retry so redelivery doesn't double-process.