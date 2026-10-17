# Router v10 → v12: route comparison on the eval suite

Run on the VPS, 17 Oct 2026. Every turn of the 143 eval cases (156 messages) was sent through the live router: once with v10 (before), then three times with v12 using fresh cache keys to measure the router's own run-to-run variation. Only the route is compared (intent, case topic, models, services); answers were not regenerated. Script: the per-turn loop in this file's notes (main.route_message with the previous user turns as history).

| Comparison | Same route | Different turns |
|---|---|---|
| v10 vs v12 | 152/156 | A12.1, M02.3, C14.1, I09.1 |
| v10 vs v12-n1 | 151/156 | A12.1, I08.1, I09.1, K04.1, K03.1 |
| v10 vs v12-n2 | 152/156 | A06.1, A12.1, I08.1, I09.1 |
| v12 vs v12-n1 | 151/156 | M02.3, C14.1, I08.1, K03.1, K04.1 |
| v12 vs v12-n2 | 152/156 | A06.1, M02.3, C14.1, I08.1 |
| v12-n1 vs v12-n2 | 153/156 | A06.1, K03.1, K04.1 |

Turns that differ between v10 and every v12 run: A12.1 (ambiguous → price; the answer lists screen prices by model and still meets the case's check "รุ่น"/"17") and I09.1 (an unrelated photo; answered by image triage before the router, so the reply is unchanged). M02.3, C14.1, A06.1, I08.1, K03.1 and K04.1 also flip between v12 runs, so they are run-to-run variation.

Multi-turn flow on the live chat (owner of PLM-00049, one conversation): 7/7 after v12; message 7 "แล้วแบตล่ะ" now answers the iPhone 14 battery price (1,490 บาท) instead of an unrelated reply.

Not re-run after v12: the full answer eval (qa/run_eval.py, 143 cases).
