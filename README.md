# Dolls Inventory

A home self-hosted web application to track dolls storage locations (Home vs Bags).

> **⚠️ Disclaimer**: This project is 100% vibe-coded. I didn’t write (and honestly didn’t even read 🤦) a single line of the application code myself — everything was produced by LLM agents based on my prompts and iterative feedback. Treat this repo as a practical experiment and a fun family tool, not as an example of “how to engineer software properly”.

## Purpose

This application helps manage and track the storage locations of dolls in a home environment, providing an easy-to-use interface for inventory management.

## Stack

### Backend
- Python 3.11+
- FastAPI
- SQLite
- SQLAlchemy 2.x
- Uvicorn
- Docker

### Frontend
- React
- TypeScript
- Vite
- i18n support (Hebrew/English/Russian)
- Mobile-first UI
- Docker

### Storage
- SQLite database: `/data/db/app.sqlite`
- Photos: `/data/photos/`

### Authentication
- Mode controlled by `AUTH_MODE` environment variable
- `AUTH_MODE=none`: No authentication, always admin (local development only)
- `AUTH_MODE=forwardauth`: SSO via Traefik ForwardAuth headers (production)

### CI/CD
- Docker images are automatically built and published to GitHub Container Registry (GHCR) on:
  - Pushes to `main` branch (tagged as `latest` + git SHA)
  - Version tags (e.g., `v1.0.0`)
- Images:
  - `ghcr.io/bronweg/doll-inventory-backend:latest`
  - `ghcr.io/bronweg/doll-inventory-frontend:latest`
- Pull requests trigger builds but do not push images

## Quick Start (No Build Required)

Use prebuilt images from GitHub Container Registry:

```bash
# Set your GitHub username (or use default: bronweg)
export REPO_OWNER=bronweg

# Pull and run
docker compose -f docker/docker-compose.pull.yml up -d
```

**Note**: If images are private, authenticate with GHCR first:
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

Access the application:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000


## How to Run Locally (Development)

For local development with live builds:

1. Clone the repository
2. (Optional) Copy `.env.example` to `.env` and adjust if needed:
   - `VITE_API_BASE_URL`: Leave empty for automatic detection (recommended), or set to a specific backend URL
   - `VITE_BAGS_COUNT`: Number of bags for doll storage (default: 3)
3. Run with Docker Compose:

```bash
docker compose -f docker/docker-compose.local.yml up --build
```

**Network Access**: The frontend automatically detects the backend URL based on the hostname you use to access it. For example:
- Access via `http://localhost:3000` → Backend at `http://localhost:8000`
- Access via `http://192.168.1.100:3000` → Backend at `http://192.168.1.100:8000`

This means you can access the app from any device on your network without additional configuration!

## SSO via Traefik (ForwardAuth) - Production Deployment

For production deployment with SSO authentication via Traefik ForwardAuth.

### Prerequisites

1. **Traefik** running with:
   - External network named `traefik`
   - HTTPS/TLS configured (e.g., Let's Encrypt)
   - An SSO ForwardAuth middleware configured (e.g., Authelia, Authentik, or custom SSO)

2. **Domain** pointing to your Traefik instance (e.g., `dolls.mydomain.com`)

3. **SSO ForwardAuth Middleware** that injects identity headers:
   - `X-Forwarded-Email` (or `X-Auth-Request-Email`)
   - `X-Forwarded-User` (or `X-Auth-Request-User`)
   - `X-Forwarded-Groups` (or `X-Auth-Request-Groups`)

### Environment Variables

Create a `.env` file or export these variables:

```bash
# Required
export DOLLS_HOST=dolls.mydomain.com
export REPO_OWNER=bronweg  # Your GitHub username for GHCR images

# Optional - SSO Configuration
export SSO_MIDDLEWARE=sso-forwardauth@file  # Name of your Traefik ForwardAuth middleware
export ADMIN_GROUP=dolls_admin              # Admin group name (all permissions)
export EDITOR_GROUP=dolls_editor            # Editor group name (no delete)
export KID_GROUP=dolls_kid                  # Kid group name (read/move only)

# Optional - Custom Header Names (if your SSO uses different headers)
export AUTH_HEADER_EMAIL=X-Forwarded-Email
export AUTH_HEADER_USER=X-Forwarded-User
export AUTH_HEADER_GROUPS=X-Forwarded-Groups

# Optional - Debugging
export DEBUG_EXPOSE_BACKEND=true  # Expose backend on port 8000 for debugging
```

### Run with Traefik

```bash
docker compose -f docker/docker-compose.traefik.yml up -d
```

### How It Works

1. **User accesses** `https://dolls.mydomain.com`
2. **Traefik** intercepts the request and applies the ForwardAuth middleware
3. **SSO** authenticates the user (redirects to login if needed)
4. **SSO** injects identity headers (`X-Forwarded-Email`, `X-Forwarded-User`, `X-Forwarded-Groups`)
5. **Backend** reads headers and computes permissions based on groups:
   - **Admin group** (`dolls_admin`): All permissions (create, rename, move, delete, photos, events)
   - **Editor group** (`dolls_editor`): All except delete (create, rename, move, photos, events)
   - **Kid/Default**: Limited permissions (read, move, add photos, view events)
6. **Frontend** calls `/api/me` to get user info and permissions, then shows/hides UI accordingly

### Permission Groups

| Group | Permissions |
|-------|-------------|
| `dolls_admin` | ✅ All (read, create, rename, move, delete, photos, events) |
| `dolls_editor` | ✅ Create, rename, move, photos, events<br>❌ Delete |
| `dolls_kid` (default) | ✅ Read, move, add photos, view events<br>❌ Create, rename, delete |

### Routing

The Traefik configuration routes requests as follows:

- **Frontend**: `https://dolls.mydomain.com/` → Frontend container (port 3000)
- **Backend API**: `https://dolls.mydomain.com/api/*` → Backend container (port 8000)
- **Media**: `https://dolls.mydomain.com/media/*` → Backend container (port 8000)

All requests go through the same domain, so the frontend uses same-origin requests (no CORS issues).

### Customizing Header Names

If your SSO uses different header names (e.g., `X-Auth-Request-*` instead of `X-Forwarded-*`), configure them:

```bash
export AUTH_HEADER_EMAIL=X-Auth-Request-Email
export AUTH_HEADER_USER=X-Auth-Request-User
export AUTH_HEADER_GROUPS=X-Auth-Request-Groups
```

### Group Delimiter Support

The backend supports multiple group delimiters:
- Comma: `dolls_admin,dolls_editor`
- Semicolon: `dolls_admin;dolls_editor`
- Space: `dolls_admin dolls_editor`
- Mixed: `dolls_admin, dolls_editor; dolls_kid`

### Testing ForwardAuth Without SSO

To test the backend's ForwardAuth parsing without a full SSO setup:

1. **Temporarily expose backend** (set `DEBUG_EXPOSE_BACKEND=true`)
2. **Send requests with headers**:

```bash
# Test as Kid (default permissions)
curl -i http://localhost:8000/api/me \
  -H "X-Forwarded-Email: kid@example.com" \
  -H "X-Forwarded-User: Kid" \
  -H "X-Forwarded-Groups: dolls_kid"

# Test as Editor (no delete)
curl -i http://localhost:8000/api/me \
  -H "X-Forwarded-Email: editor@example.com" \
  -H "X-Forwarded-User: Editor" \
  -H "X-Forwarded-Groups: dolls_editor"

# Test as Admin (all permissions)
curl -i http://localhost:8000/api/me \
  -H "X-Forwarded-Email: admin@example.com" \
  -H "X-Forwarded-User: Admin" \
  -H "X-Forwarded-Groups: dolls_admin"

# Test delete permission (should fail for editor/kid, succeed for admin)
curl -X DELETE http://localhost:8000/api/dolls/1 \
  -H "X-Forwarded-Email: editor@example.com" \
  -H "X-Forwarded-User: Editor" \
  -H "X-Forwarded-Groups: dolls_editor"
# Expected: 403 Forbidden

curl -X DELETE http://localhost:8000/api/dolls/1 \
  -H "X-Forwarded-Email: admin@example.com" \
  -H "X-Forwarded-User: Admin" \
  -H "X-Forwarded-Groups: dolls_admin"
# Expected: 204 No Content (success)
```

### Troubleshooting

#### Issue: Getting 401 Unauthorized

**Cause**: Headers not being forwarded from SSO to backend.

**Solutions**:
1. Check that your Traefik ForwardAuth middleware is configured to forward headers
2. Verify header names match (check `AUTH_HEADER_*` environment variables)
3. Check Traefik logs: `docker logs traefik`
4. Test with curl (see "Testing ForwardAuth Without SSO" above)

#### Issue: Everyone has Kid permissions

**Cause**: Groups header not being parsed correctly.

**Solutions**:
1. Check the groups header value in your SSO (should be comma/semicolon/space separated)
2. Verify `AUTH_HEADER_GROUPS` matches your SSO's header name
3. Check backend logs for group parsing: `docker logs dolls-inventory-backend-traefik`
4. Ensure group names match exactly (case-sensitive): `dolls_admin`, `dolls_editor`, `dolls_kid`

#### Issue: Admin UI not visible

**Cause**: User doesn't have required permissions.

**Solutions**:
1. Check `/api/me` response to see current user's permissions
2. Verify user is in the correct group in your SSO
3. Check `ADMIN_GROUP` and `EDITOR_GROUP` environment variables match your SSO groups

#### Issue: CORS errors

**Cause**: Frontend and backend on different domains.

**Solutions**:
1. Ensure both frontend and backend are served from the same domain (via Traefik routing)
2. Check that `VITE_API_BASE_URL` is empty (for same-origin requests)
3. Verify Traefik routing rules are correct

## Testing

Once running, you can access:

- **Backend API Health**: http://localhost:8000/api/health
- **Backend API Docs**: http://localhost:8000/docs (Swagger UI)
- **Frontend**: http://localhost:3000

### API Testing Examples

Here are some curl commands to test the API:

```bash
# Health check
curl http://localhost:8000/api/health

# Create a doll (admin only, auto-admin in AUTH_MODE=none)
curl -X POST http://localhost:8000/api/dolls \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Barbie Dreamhouse",
    "location": "HOME"
  }'

# Create a doll in a bag
curl -X POST http://localhost:8000/api/dolls \
  -H "Content-Type: application/json" \
  -d '{
    "name": "LOL Surprise",
    "location": "BAG",
    "bag_number": 1
  }'

# List all dolls
curl http://localhost:8000/api/dolls

# Search dolls by name
curl "http://localhost:8000/api/dolls?q=barbie"

# Filter dolls by location
curl "http://localhost:8000/api/dolls?location=HOME"

# Filter dolls by bag number
curl "http://localhost:8000/api/dolls?bag=1"

# Get a specific doll (replace {id} with actual ID)
curl http://localhost:8000/api/dolls/1

# Move a doll to a bag (user or admin)
curl -X PATCH http://localhost:8000/api/dolls/1 \
  -H "Content-Type: application/json" \
  -d '{
    "location": "BAG",
    "bag_number": 2
  }'

# Move a doll home
curl -X PATCH http://localhost:8000/api/dolls/1 \
  -H "Content-Type: application/json" \
  -d '{
    "location": "HOME"
  }'

# Rename a doll (admin only)
curl -X PATCH http://localhost:8000/api/dolls/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Barbie Dreamhouse Deluxe"
  }'

# Get events for a doll
curl http://localhost:8000/api/dolls/1/events

# List all events
curl http://localhost:8000/api/events
```

## Project Structure

```
dolls-inventory/
├── README.md
├── .env.example
├── docker/
│   └── docker-compose.local.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   └── config.py
│   │   └── api/
│   │       └── health.py
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   └── i18n/
    │       ├── en.json
    │       ├── he.json
    │       └── ru.json
    └── Dockerfile
```

## Development Status

**Current Phase**: Step 6 - Production Ready ✅

### Completed Features

- ✅ **Backend**
  - FastAPI with SQLAlchemy 2.x
  - SQLite database with automatic initialization
  - Doll management (CRUD with soft delete)
  - Photo upload and serving
  - Event logging system
  - Permission-based access control (8 permissions)
  - Two authentication modes:
    - `AUTH_MODE=none` (local development)
    - `AUTH_MODE=forwardauth` (SSO via Traefik)
  - Configurable ForwardAuth headers
  - Group-based permission mapping (admin/editor/kid)

- ✅ **Frontend**
  - React + TypeScript + Vite
  - Mobile-first responsive design
  - i18n support (English/Hebrew/Russian)
  - RTL support for Hebrew
  - Kids UI (Home/Bags/All views)
  - Admin UI (Create/Manage/Events)
  - Search with autocomplete and thumbnails
  - Photo upload with drag-and-drop
  - Delete with type-to-confirm UX
  - Permission-based UI gating

- ✅ **Deployment**
  - Docker images published to GHCR
  - CI/CD via GitHub Actions
  - Local development mode (docker-compose.local.yml)
  - Pull-and-run mode (docker-compose.pull.yml)
  - Traefik + SSO mode (docker-compose.traefik.yml)

- ✅ **Documentation**
  - Comprehensive README
  - API testing examples
  - SSO setup guide
  - Troubleshooting section

