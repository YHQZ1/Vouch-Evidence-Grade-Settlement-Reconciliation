# Run Vouch with Docker Compose

This guide runs the Vouch React review interface and FastAPI service as two
containers. Nginx serves the built frontend and proxies the browser's same-origin
`/api`, `/healthz`, and `/openapi.json` requests to the backend container.

## Prerequisites

- Docker Desktop (or Docker Engine) with the Compose v2 plugin
- Ports `5173` and `8000` available on the host

Check the installation:

```bash
docker --version
docker compose version
```

## Start the application

From the repository root:

```bash
docker compose up --build
```

Then open [http://localhost:5173](http://localhost:5173). The API health check is
available at [http://localhost:8000/healthz](http://localhost:8000/healthz).

The first build downloads the pinned backend and frontend dependencies. Later
starts reuse the image layers unless a dependency, source file, or Dockerfile
changes.

## Run in the background

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f backend frontend
```

The frontend is ready only after the backend health check passes. If the backend
fails its health check, Compose will not start the frontend dependency chain.

## Stop and rebuild

Stop and remove the Compose containers and network:

```bash
docker compose down
```

Rebuild after dependency or image changes:

```bash
docker compose build --no-cache
docker compose up
```

Containerized batches remain process-local, just like the direct local run. A
backend container restart removes batches and uploaded source bytes. There is no
volume or database in this Compose setup by design.

## Optional configuration

The defaults are suitable for local development. Override them inline or in a
root `.env` file (do not commit secrets):

| Variable | Default | Purpose |
| --- | --- | --- |
| `VOUCH_WEB_PORT` | `5173` | Host port for the frontend |
| `VOUCH_API_PORT` | `8000` | Host port for direct API/health access |
| `VOUCH_ENVIRONMENT` | `development` | Backend environment label |
| `VOUCH_LOG_LEVEL` | `INFO` | Backend log level |
| `VOUCH_MAX_UPLOAD_BYTES` | `10485760` | Maximum bytes per source upload |
| `VOUCH_MAX_PAGE_SIZE` | `100` | Maximum API page size |

For example:

```bash
VOUCH_WEB_PORT=8080 VOUCH_API_PORT=8100 docker compose up --build
```

Then open [http://localhost:8080](http://localhost:8080).

## What the containers contain

- `backend`: Python 3.12-slim, the runtime `app` package, and Uvicorn on port
  8000. Test fixtures, evaluation code, synthetic-data generators, and local
  virtual environments are excluded from the image.
- `frontend`: a Node build stage followed by Nginx serving the static Vite
  bundle. The browser uses same-origin paths; the internal Compose hostname
  `backend` is never placed in a browser URL.

This is a reproducible local/demo boundary, not a production deployment. Before
using real financial data, add durable persistence, authentication,
authorization, tenant isolation, secret management, TLS, queues, observability,
and an explicit deployment architecture decision.
