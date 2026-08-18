# FAQ

## Does STRATHEX call the STRATHMARK API?

By default it calls STRATHMARK 2 directly in Python so an event laptop remains offline-capable. The demo can explicitly use FastAPI `POST /calculate` by setting `STRATHMARK_TRANSPORT=http` and `STRATHMARK_API_URL`. HTTP mode is version-checked and never silently falls back.

## Why did marks change from v6?

V7 accepts STRATHMARK 2's prior-only evidence and joint optimizer. It no longer pushes a locally selected prediction through the manual-override channel. This is a deliberate breaking semantic change.

## Does wood quality change the prediction?

No. It is compatibility context and a numeric no-op in v2.

## Do heat results get 97% weight in semis and finals?

No. The field is recalculated under the original exclusive cutoff. Same-day results are not prediction evidence.

## Is there still an LLM or XGBoost predictor?

Not in live numeric calculation. Historical modules and reports remain for audit context. STRATHMARK's v2 core is the authority.

## What is the difference between interval and standard deviation?

The interval is forecast uncertainty about predicted time. Performance standard deviation is expected race-to-race spread and is used in simulation.

## Are Excel and ResultStore writes atomic together?

No. Excel is canonical and is written first. ResultStore is a best-effort second write.

## Is the public calculation API authenticated?

No. It is stateless and public. Bind the demo to loopback. Remote use needs a deliberate HTTPS and access-control boundary.

## Why are some historical rows excluded?

Undated, same-day, future, and invalid rows cannot be prior-only evidence under the fixed cutoff.
