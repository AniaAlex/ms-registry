# Docker MS Registry

Containerized deployment for the MS Registry service.

## Quick Start

```bash
# Build and run
make run

# Check status
make status

# View logs
make logs

# Stop service
make stop
```

## Services

- **docker-ms-registry**: Django application (ports 8000, 3030)
- **db**: PostgreSQL 14 database
- **redis**: Redis 6.2 cache

## Configuration

Environment variables can be set in a `.env` file or passed via Jenkins/CI:

```bash
ENV=PRODUCTION
DEBUG=False
SECRET_KEY=your-secret-key
DB_PASSWORD=your-db-password
REDIS_URL=redis://redis:6379/0
```

## Endpoints

- API: http://localhost:8000/api/
- Static files: http://localhost:8000/static/

## Development

```bash
# Run migrations
make migrate

# Collect static files
make collectstatic

# Access shell
make shell

# Run tests
make test
```
