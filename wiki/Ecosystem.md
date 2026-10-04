# Related projects

| Project | Responsibility |
| --- | --- |
| STRATHEX | Judge-facing event setup, fields, schedules, review, results, advancement, payouts, saves and exports. |
| [STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK) | Predictions, calibration, mark optimization, history and signed competition evidence. |
| MNEMEX | Portable competitor identity and finalized history. |
| Missoula Pro-Am Manager | Its own live/provisional event results and operator workflow. |

## Race-day operation

STRATHEX uses local data and its selected STRATHMARK runtime. MNEMEX must not become
a race-day network requirement: event laptops use pinned local snapshots and reconcile
afterward.

V2 direct Python, the public V2 HTTP demo, local Linux V3 and the V7 service are
different integrations. Optional Missoula shadow integration uses a separate trusted
contract; it is not STRATHEX's public stateless calculation route.

## Keep ownership clear

Live and provisional results belong to the event application. Portable finalized
history belongs to MNEMEX. Prediction and settlement receipts belong to STRATHMARK.
An integration must not silently take over another project's authority.

See [Architecture](Architecture) for STRATHEX's active connections.
