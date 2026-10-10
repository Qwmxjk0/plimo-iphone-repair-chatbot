# Offline contract results

Date: 10 Oct 2026. Command: `docker compose exec -T api python -m unittest test_chat -v`

| Case | Observed |
|---|---|
| Image analysis before retrieval + session isolation | PASS |
| Invalid image rejected before provider call | PASS |
| Missing retrieval context skips answer model | PASS |
| Missing key does not claim real RAG | PASS |
| Text retrieval → generation → repeat answer cache hit | PASS |

5 tests passed in 0.059 seconds. Redis, LightRAG and OpenAI are mocked in these tests. This duration is test execution time, not chatbot response latency.

Separate runtime checks: Redis PING returned PONG; three default Docker containers running. No live OpenAI or LightRAG answer was produced. The 20 live cases are blocked, not passed.
