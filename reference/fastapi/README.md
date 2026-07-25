# FastAPI (+ uvicorn) — Story Engine reference note

> Web framework + ASGI server for Story Engine's inbound API adapter: FastAPI defines app/routes/DTOs,
> uvicorn serves the ASGI app.

- **Version pin (ours):** `fastapi>=0.115`, `uvicorn[standard]>=0.30`
- **Latest stable (verified):** FastAPI 0.139.2 (2026-07-16), uvicorn 0.51.0 (2026-07-08) — checked 2026-07.
- **Upstream `llms.txt`:** none — `fastapi.tiangolo.com/llms.txt` is 404 (tiangolo family publishes none). Use the docs site.
- **Docs home:** FastAPI → https://fastapi.tiangolo.com/ · uvicorn → https://www.uvicorn.org/

## How Story Engine uses it
- Inbound (driving) adapter only: `api/app.py` is an app factory; routes live in `api/routers/`.
- Routes call application services from `bootstrap.build_container()` — the API layer never instantiates adapters itself.
- `api/schemas.py` holds request/response DTOs kept SEPARATE from domain models; domain models never carry API concerns.
- `api/errors.py` maps domain errors to HTTP responses (exception handlers / status codes).
- CORS configured from `Settings.all_cors_origins` via `CORSMiddleware`.
- uvicorn runs the ASGI app; an E2E boot smoke test drives it with `httpx` + FastAPI `TestClient`.

## Read this for… (task → doc link)
- Split routes across `api/routers/` with `APIRouter` (bigger-applications) → https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Map domain errors to HTTP (`HTTPException`, `@app.exception_handler`) for `api/errors.py` → https://fastapi.tiangolo.com/tutorial/handling-errors/
- Configure CORS from Settings (`CORSMiddleware`, `allow_origins`) → https://fastapi.tiangolo.com/tutorial/cors/
- App factory + startup/shutdown via `lifespan` → https://fastapi.tiangolo.com/advanced/events/
- E2E boot smoke test with `TestClient` (httpx-based) → https://fastapi.tiangolo.com/tutorial/testing/
- Request/response DTOs with Pydantic (`response_model`) → https://fastapi.tiangolo.com/tutorial/response-model/
- Serve/deploy with uvicorn (`uvicorn app:app` or `uvicorn.run`) → https://www.uvicorn.org/ · https://fastapi.tiangolo.com/deployment/manually/

## Gotchas that bite us
- Keep `api/schemas.py` DTOs strictly separate from `domain/` models — never annotate a route with a domain model or let API fields leak inward; validate at the boundary and translate.
- Don't wire adapters in routers — routes depend only on services from `build_container()`; instantiating an adapter in a route breaks the composition-root rule.
- No vendorable `llms.txt` — the tiangolo family (FastAPI/Starlette/uvicorn) publishes none, so this note points at the docs site.
- **`uvicorn[standard]` pulls extras** (uvloop where available, httptools, websockets, watchfiles for `--reload`); bare `uvicorn` omits them — keep the `[standard]` marker or reload/perf features silently disappear.

_Sources: pypi.org/project/fastapi, pypi.org/project/uvicorn, fastapi.tiangolo.com, uvicorn.org. Verified 2026-07-24._
