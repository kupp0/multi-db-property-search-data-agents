
## 2024-05-28 - Spanner Connection Pooling Anti-Pattern
**Learning:** In Python backend services, instantiating the Google Cloud Spanner `database` object (via `instance.database()`) on every request degrades performance significantly because it spins up a new session pool instead of reusing connections.
**Action:** Globally cache the Spanner `database` object rather than redundantly instantiating it on every request.
