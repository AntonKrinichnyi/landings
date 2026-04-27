# Leads Landing Platform

A modern FastAPI-based lead management system with support for multiple landing pages and affiliate tracking. The platform consists of two microservices: a landing page API for lead submission and a core API for lead analytics.

## Table of Contents

- [Quick Start with Docker Compose](#quick-start-with-docker-compose)
- [Installation from GitHub](#installation-from-github)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Architecture Overview](#architecture-overview)
- [API Documentation](#api-documentation)

## Quick Start with Docker Compose

### Prerequisites

- Docker
- Docker Compose

### Running the Application

1. **Start all services:**

```bash
docker-compose up --build
```

This command will:
- Start PostgreSQL database (port 5432)
- Start Redis cache (port 6379)
- Build and start Landings API (port 8001)
- Build and start Core API (port 8002)
- Run database migrations automatically

2. **Verify services are running:**

```bash
docker-compose ps
```

3. **View logs:**

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f core
docker-compose logs -f landings
```

4. **Stop services:**

```bash
docker-compose down

# Stop and remove volumes (WARNING: deletes database)
docker-compose down -v
```

## Installation from GitHub

### Clone the Repository

```bash
git clone <repository-url>
cd landings
```

### Local Development Setup

1. **Create Python virtual environment:**

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**

Create `.env` files for each app:

**core_app/.env:**
```
DB_USER=app
DB_PASS=app
DB_HOST=localhost
DB_PORT=5432
DB_NAME=leads_db
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
REDIS_URL=redis://localhost:6379/0
```

**landings_app/.env:**
```
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
REDIS_URL=redis://localhost:6379/0
```

4. **Run services locally:**

Start PostgreSQL and Redis separately, then run:

```bash
# Core App (requires database)
uvicorn core_app.main:app --reload --port 8002

# Landings App (in another terminal)
uvicorn landings_app.main:app --reload --port 8001
```

## Project Structure

```
landings/
├── core_app/                      # Analytics and lead retrieval API
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Settings and configuration
│   ├── models.py                  # SQLAlchemy ORM models
│   ├── schemas.py                 # Pydantic request/response schemas
│   ├── services.py                # Authentication and utilities
│   ├── routers.py                 # API endpoints
│   ├── worker.py                  # Async lead processing worker
│   ├── Dockerfile                 # Docker container configuration
│   ├── db/
│   │   ├── connection.py          # Database connection setup
│   │   ├── alembic.ini            # Alembic migration config
│   │   └── migrations/            # Database migration scripts
│   └── tests/                     # Test suite
│
├── landings_app/                  # Lead submission API
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Settings and configuration
│   ├── schemas.py                 # Request/response schemas
│   ├── services.py                # Authentication and utilities
│   ├── routers.py                 # API endpoints
│   ├── Dockerfile                 # Docker container configuration
│   └── tests/                     # Test suite
│
├── docker-compose.yml             # Docker Compose orchestration
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Database Schema

### ER Diagram

```
┌──────────────┐         ┌──────────────┐
│  Affiliate   │         │    Offer     │
├──────────────┤         ├──────────────┤
│ id (UUID) PK │         │ id (UUID) PK │
│ name (str)   │         │ name (str)   │
└──────────────┘         └──────────────┘
       ▲                         ▲
       │                         │
       │ 1:N                 1:N │
       │                         │
       └─────────┬───────────────┘
                 │
                 │
         ┌───────▼────────┐
         │     Lead       │
         ├────────────────┤
         │ id (UUID) PK   │
         │ name (str)     │
         │ phone (str)    │
         │ country (str)  │
         │ created_at     │
         │ affiliate_id   │ FK
         │ offer_id       │ FK
         └────────────────┘
```

### Table Definitions

#### affiliates
- **id** (UUID): Primary key, auto-generated
- **name** (VARCHAR(255)): Affiliate name, not null
- **Relationships**: One-to-many with leads

#### offers
- **id** (UUID): Primary key, auto-generated
- **name** (VARCHAR(255)): Offer name, not null
- **Relationships**: One-to-many with leads

#### leads
- **id** (UUID): Primary key, auto-generated
- **name** (VARCHAR(255)): Lead name, not null
- **phone** (VARCHAR(20)): Phone number, not null
- **country** (VARCHAR(2)): 2-letter country code, not null
- **created_at** (TIMESTAMP): Record creation timestamp, defaults to UTC now
- **affiliate_id** (UUID): Foreign key to affiliates table
- **offer_id** (UUID): Foreign key to offers table
- **Relationships**: Many-to-one with affiliates and offers

## Architecture Overview

### Two-Tier Microservice Architecture

**Landings API (Port 8001)**
- Accepts lead submissions via POST /lead
- Validates affiliate credentials via JWT
- Pushes leads to Redis queue for async processing
- Stateless, horizontally scalable

**Core API (Port 8002)**
- Retrieves processed leads via GET /leads
- Provides lead analytics and grouping
- Requires JWT authentication
- Integrates with PostgreSQL for persistence

**Async Worker (Integrated with Core)**
- Polls Redis queue continuously
- Performs lead deduplication using Redis
- Persists unique leads to PostgreSQL
- Handles failures with exponential backoff

### Data Flow

```
Lead Submission → Landings API → Redis Queue → Worker → PostgreSQL
                      ↓
                   JWT Auth
                      ↓
                   Validation
```

## API Documentation

### Authentication

All endpoints require JWT Bearer token in Authorization header:

```bash
Authorization: Bearer <your-jwt-token>
```

### Landings API Endpoints

**POST /lead** - Submit a new lead

Request body:
```json
{
  "name": "John Doe",
  "phone": "+1234567890",
  "country": "US",
  "offer_id": "550e8400-e29b-41d4-a716-446655440000",
  "affiliate_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

Response:
```json
{
  "status": "queued"
}
```

### Core API Endpoints

**GET /leads** - Retrieve leads for authenticated affiliate

Query parameters:
- `date_from` (required): Start date (YYYY-MM-DD)
- `date_to` (required): End date (YYYY-MM-DD)
- `group` (required): Grouping criteria ('date' or 'offer')

Example:
```bash
GET /leads?date_from=2024-01-01&date_to=2024-01-31&group=date
```

Response (grouped by date):
```json
[
  {
    "date": "2024-01-01",
    "count": 5,
    "leads": [
      {
        "id": "...",
        "name": "John Doe",
        "phone": "+1234567890",
        "country": "US",
        "offer_id": "...",
        "affiliate_id": "...",
        "created_at": "2024-01-01T12:00:00"
      }
    ]
  }
]
```

## Environment Variables

### Core App (core_app/.env)
- `DB_USER`: PostgreSQL username
- `DB_PASS`: PostgreSQL password
- `DB_HOST`: PostgreSQL host
- `DB_PORT`: PostgreSQL port
- `DB_NAME`: Database name
- `JWT_SECRET`: Secret key for JWT signing
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `REDIS_URL`: Redis connection URL

### Landings App (landings_app/.env)
- `JWT_SECRET`: Secret key for JWT verification
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `REDIS_URL`: Redis connection URL

## Development

### Running Tests

```bash
# Core app tests
pytest core_app/tests/

# Landings app tests
pytest landings_app/tests/
```

### Database Migrations

Migrations are handled automatically on Core App startup using Alembic. To create a new migration:

```bash
alembic revision --autogenerate -m "Your migration message"
```

## Support

For issues, feature requests, or contributions, please open an issue or pull request on GitHub.