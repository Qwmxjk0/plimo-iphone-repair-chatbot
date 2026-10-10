# Shop tone + preliminary estimates — 10 October 2026

- Prompt: thai-shop-estimate-v4; KB: plimo-estimate-v3, fresh rag-data-estimate-v3 volume. Previous index and member history preserved.
- LightRAG: 17 processed documents, zero failed.
- 27 automated tests passed: memberships, revised quote approval and stale decisions, ingestion labels, real Redis cache TTL/rate/locks (AI mocked in unit/integration suite).
- Live OpenAI + LightRAG: 6 requests passed transport/RAG/no-demo checks. iPhone 13 estimate 3,200 THB; repeated answer hit Redis in 1 ms backend; extra-parts answer requires new approval; Pro Max not assigned normal-model price; warranty not invented. Full actual responses: shop-tone-live.json.
- Browser: signed-in demo member asked price + extra parts in a new conversation; received actual grounded answer; estimate notice and source labels visible.
- Catalog prices originally illustrative, authorized by owner on this date as preliminary estimates, never final totals. Historical seeded examples retain provenance labels.
- Payment, confirmed warranty/parts brands, full image quality evaluation and VPS deployment remain outside this validation.
- Workflow supports revised quotes before repair starts. Additional costs discovered after repair begins need a separate pause/reapproval workflow before that use case is enabled; current backend prevents changing the approved price while repairing/ready.
