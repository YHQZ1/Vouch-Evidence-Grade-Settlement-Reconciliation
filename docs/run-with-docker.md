# Run Vouch with Docker Compose

This guide runs the Vouch React review interface and FastAPI service as two
containers, with Ollama running locally on the host. Nginx serves the built
frontend and proxies the browser's same-origin `/api`, `/healthz`, and
`/openapi.json` requests to the backend container. The backend reaches Ollama
through Docker's explicit host-gateway alias; model traffic stays local.

## Prerequisites

- Docker Desktop (or Docker Engine) with the Compose v2 plugin
- [Ollama](https://ollama.com/download) installed on the host
- Ports `5173`, `8000`, and `11434` available on the host

Check the installation:

```bash
docker --version
docker compose version
```

## Prepare Ollama

Ollama binds to loopback by default, so configure it once to accept connections
from Docker. Use the flow that matches how Ollama runs on your machine.

### macOS application

```bash
launchctl setenv OLLAMA_HOST "0.0.0.0:11434"
```

Quit and reopen the Ollama application, then pull the model:

```bash
ollama pull llama3.2:3b
```

### Manually started server

Start the configured server first:

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

Keep that terminal running. In another terminal, pull the model:

```bash
ollama pull llama3.2:3b
```

### Linux systemd service

Run `sudo systemctl edit ollama.service`, add the following override, then reload
and restart the service:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
ollama pull llama3.2:3b
```

These host-binding steps follow the
[official Ollama FAQ](https://docs.ollama.com/faq).
The bind is intended only for a trusted local development machine; do not expose
port `11434` on a public network. Confirm Ollama and the model are available:

```bash
curl http://127.0.0.1:11434/api/tags
```

## Start the application

In a second terminal, from the repository root:

```bash
docker compose up --build
```

Then open [http://localhost:5173](http://localhost:5173). The API health check is
available at [http://localhost:8000/healthz](http://localhost:8000/healthz).

The first build downloads the pinned backend and frontend dependencies. Later
starts reuse the image layers unless a dependency, source file, or Dockerfile
changes. Compose enables the bounded Ollama investigation adapter by default;
normal reconciliation remains deterministic and does not invoke the model.

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
| `VOUCH_AI_ENABLED` | `true` | Enable optional investigations in Compose |
| `VOUCH_AI_PROVIDER` | `ollama` | Local model provider |
| `VOUCH_AI_MODEL` | `llama3.2:3b` | Installed Ollama model tag |
| `VOUCH_AI_ENDPOINT` | `http://host.docker.internal:11434` | Docker-to-host Ollama URL |
| `VOUCH_AI_ALLOW_DOCKER_HOST_GATEWAY` | `true` | Authorize only the Docker host alias |
| `VOUCH_AI_MAX_TOTAL_TIME_MS` | `60000` | Absolute investigation deadline |

For example:

```bash
VOUCH_WEB_PORT=8080 VOUCH_API_PORT=8100 docker compose up --build
```

Then open [http://localhost:8080](http://localhost:8080). To run without
model-assisted investigations, set `VOUCH_AI_ENABLED=false`; deterministic
reconciliation and review continue to work.

## Verify the container can reach Ollama

```bash
docker compose exec backend python -c "from urllib.request import urlopen; print(urlopen('http://host.docker.internal:11434/api/tags', timeout=3).status)"
```

A `200` response confirms connectivity. If it fails, verify that Ollama is running,
the model is pulled, and Ollama is listening on `0.0.0.0:11434`. The backend
records an explicit provider-unavailable outcome rather than changing any
settlement when Ollama cannot be reached.

## What the containers contain

- `backend`: Python 3.12-slim, the runtime `app` package, and Uvicorn on port
  8000. Test fixtures, evaluation code, synthetic-data generators, and local
  virtual environments are excluded from the image.
- `frontend`: a Node build stage followed by Nginx serving the static Vite
  bundle. The browser uses same-origin paths; the internal Compose hostname
  `backend` is never placed in a browser URL.
- Ollama and its model stay on the host; Compose does not bake a multi-gigabyte
  model into either Vouch image.

This is a reproducible local/demo boundary, not a production deployment. Before
using real financial data, add durable persistence, authentication,
authorization, tenant isolation, secret management, TLS, queues, observability,
and an explicit deployment architecture decision.
