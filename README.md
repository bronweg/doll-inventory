# Dolls Inventory

A home self-hosted web application to track dolls storage locations (Home vs Bags).

## Purpose

This application helps manage and track the storage locations of dolls in a home environment, providing an easy-to-use interface for inventory management.

## Stack

### Backend
- Python 3.11+
- FastAPI
- SQLite
- SQLAlchemy (planned)
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
2. Copy `.env.example` to `.env` and adjust if needed
3. Run with Docker Compose:

```bash
docker compose -f docker/docker-compose.local.yml up --build
```

## Testing

Once running, you can access:

- **Backend API Health**: http://localhost:8000/api/health
- **Frontend**: http://localhost:3000

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

**Current Phase**: Step 1 - Project Skeleton
- ✅ Basic project structure
- ✅ Docker setup for local development
- ✅ Health check endpoint
- ✅ Basic frontend scaffold

**Next Steps**:
- Database models and migrations
- API endpoints for doll management
- Frontend UI implementation
- Authentication integration
- Traefik deployment configuration

