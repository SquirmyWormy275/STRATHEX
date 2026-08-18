# Prediction Methods

STRATHEX 7 has one live numeric model authority: STRATHMARK 2's prior-only hierarchical core.

## Authority order

1. An explicit manual override, when supplied.
2. The v2 hierarchical core.
3. A promoted residual only if STRATHMARK activates one.
4. A broad prior/degraded fallback when compatible artifacts are unavailable.

The former numeric Ollama LLM, local XGBoost model, independent baseline comparison, and expected-error selector are retired from live calculation.

## Evidence

Each field sends stable competitor IDs and dated history under one exclusive cutoff. Valid observations before the cutoff can contribute. Undated, same-day, future, and invalid observations are excluded.

Wood quality and same-tournament fields remain accepted compatibility context but are numeric no-ops in v2. The response identifies ignored factors.

## Output

A prediction is more than one number. STRATHEX preserves predicted time, confidence, explanation, forecast interval, performance standard deviation, engine/model/calibration versions, cutoff, optimizer evidence, warnings, degraded state, provenance, and ignored factors.

The direct and HTTP transports are required to match on all release-critical fields.
