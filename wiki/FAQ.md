# FAQ

## Does STRATHEX call the STRATHMARK API?

For a V2-selected scope, STRATHEX calls STRATHMARK 2 directly in Python by default so an event laptop remains offline-capable. The demo can explicitly use FastAPI `POST /calculate`. A V3-selected scope uses its separate authenticated loopback lifecycle API. Neither transport nor engine silently falls back.

## Where do I choose V2 or V3?

A single event chooses once during setup. A multi-event tournament chooses once at creation, and every child event and round inherits it. There is no default and no per-event tournament override.

## Why does V3 show a prediction but no mark before heats exist?

That is intentional. The signed pre-field forecast is for seeding and must not contain a mark. V3 can calculate field-relative marks only after exact heat membership and stand assignments exist.

## Why did marks change from v6?

V7 accepts STRATHMARK 2's prior-only evidence and joint optimizer. It no longer pushes a locally selected prediction through the manual-override channel. This is a deliberate breaking semantic change.

## Does wood quality change the prediction?

No. It is compatibility context and a numeric no-op in v2.

## Do heat results get 97% weight in semis and finals?

No. The field is recalculated under the original exclusive cutoff. Same-day results are not prediction evidence.

## Is there still an LLM or XGBoost predictor?

Not as a hidden STRATHEX-side selector. Historical modules and reports remain for audit context. The deliberately selected STRATHMARK engine is authoritative for the competition.

## What is the difference between interval and standard deviation?

The interval is forecast uncertainty about predicted time. Performance standard deviation is expected race-to-race spread and is used in simulation.

## Are Excel and ResultStore writes atomic together?

No. Excel is canonical and is written first. ResultStore is a best-effort second write.

## Is the public calculation API authenticated?

The V2 `POST /calculate` demo route is stateless and unauthenticated. Bind it to loopback. The separate V3 lifecycle requires an externally supplied credential and accepts loopback only in this demo.

## Why are some historical rows excluded?

Undated, same-day, future, and invalid rows cannot be prior-only evidence under the fixed cutoff.
