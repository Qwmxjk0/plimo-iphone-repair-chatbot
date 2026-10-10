# Member / admin verification — 10 Oct 2026

Command: `docker compose exec -T api python -m unittest test_chat test_ingest test_membership -v`

10 tests passed in 2.418 seconds. Coverage includes ownership of conversations and cases, refusal of another member's conversation ID, user/admin separation, role injection rejected at registration, logout invalidates session, cross-origin writes rejected, allowed case transitions and audit/count updates, and durable owned chat history after Redis cache is cleared. AI/Redis are mocked for the chat contracts; SQLite uses isolated temporary databases.

Real local UI: registration succeeded, member RAG chat created a saved conversation, demo_user login shows the eight seeded example cases and history. Login tab text colors corrected after the reported white-on-white button bug.

Seeded messages and cases are labeled examples and are not live AI test outputs. See member-demo.md for demo credentials and new flow.
