
## 2024-11-20 - Offloading synchronous I/O in FastAPI
**Learning:** In a FastAPI app, calling synchronous functions that perform slow I/O (like network requests or querying the Gemini Data Agent) inside an `async def` endpoint blocks the single-threaded asyncio event loop. This causes the entire server to freeze and reject other incoming requests while waiting for the operation to complete.
**Action:** Always wrap synchronous blocking calls in `await run_in_threadpool()` (from `starlette.concurrency`) inside an `async` endpoint to push the execution to a separate thread, keeping the event loop responsive.
