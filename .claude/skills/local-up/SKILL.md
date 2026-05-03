---
name: local-up
description: Start the local Docker Compose stack (backend + frontend) for development. Use when the user wants to spin the app up locally, test a feature in a browser, or bring the stack back after changes.
---

# Start the local dev stack

The local stack is defined in `docker/docker-compose.local.yml`. It already sets `AUTH_MODE=none` and `ALLOW_INSECURE_LOCAL=true` on the backend, so no extra env vars are needed.

## Steps

1. Check whether containers are already running:

   ```bash
   docker compose -f docker/docker-compose.local.yml ps
   ```

2. If nothing is up, start the stack in the background:

   ```bash
   docker compose -f docker/docker-compose.local.yml up -d --build
   ```

   Use `--build` so code changes since the last run are picked up. Omit it if the user explicitly wants a fast restart without rebuilding.

3. After `up` returns, confirm both services are healthy:

   ```bash
   docker compose -f docker/docker-compose.local.yml ps
   ```

4. Print the URLs:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Backend docs (FastAPI Swagger): http://localhost:8000/docs

5. If the user wants live logs, tail them:

   ```bash
   docker compose -f docker/docker-compose.local.yml logs -f
   ```

## Troubleshooting

- **Port 3000 or 8000 already in use**: identify the holder with `lsof -i :3000` / `lsof -i :8000` and ask the user before killing anything.
- **Backend can't write to `/data/db`**: the named volume `dolls_db` is docker-managed — no host path needed. Don't propose bind-mounts unless the user asks.
- **Frontend hot reload not working**: `Dockerfile.dev` runs `vite` with `host: 0.0.0.0`; confirm the container has the source mounted if someone customized the compose file.
- **Auth errors despite `AUTH_MODE=none`**: `ALLOW_INSECURE_LOCAL=true` must also be set — the backend refuses `none` without it. Both are already in `docker-compose.local.yml`; if missing, the file was edited.

## Shutting down

```bash
docker compose -f docker/docker-compose.local.yml down
```

Add `-v` only if the user explicitly wants to wipe the SQLite DB and uploaded photos.
