# Dolls Inventory

A home self-hosted web application to track dolls storage locations (Home vs Bags).

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
- Current: `AUTH_MODE=none` (no authentication, always admin)
- Future: `AUTH_MODE=forwardauth` (Traefik forward auth headers)

## How to Run Locally

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

**Current Phase**: Step 2 - Backend Implementation
- ✅ Basic project structure
- ✅ Docker setup for local development
- ✅ Health check endpoint
- ✅ Basic frontend scaffold
- ✅ SQLAlchemy database models (Doll, Event)
- ✅ Authentication adapter (AUTH_MODE=none and AUTH_MODE=forwardauth)
- ✅ API endpoints for doll management (CRUD)
- ✅ Event logging system
- ✅ Automatic database initialization

**Next Steps**:
- Frontend UI implementation
- Photo upload and serving
- Traefik deployment configuration
- Database migrations (Alembic)

