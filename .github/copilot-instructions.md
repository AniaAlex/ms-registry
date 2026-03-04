# MS-Registry Copilot Instructions

## Project Overview

This is a **Django REST Framework** application implementing the **EUDI Wallet Member State Registry** for the EU Digital Identity Wallet ecosystem. It manages registration of:

- **Relying Parties (verifiers)** - Service providers requesting wallet attributes
- **PID Providers** - Issuers of Person Identification Data  
- **Attestation Providers** - Issuers of qualified/non-qualified EAA credentials
- **QTSPs** - Qualified Trust Service Providers

The codebase follows the **TS5/TS6 technical specifications** and **ETSI TS 119612** for Trust Status Lists.

## Architecture

### Django Apps (in `ms_registry/`)

| App | Purpose |
|-----|---------|
| `core` | Abstract base models (`UUIDModel`, `TimestampedModel`, `BaseModel`), enums (`EntitlementType`, `EntityRole`, `RegistrationStatus`) |
| `legal_entities` | `LegalEntity`, `LegalPerson`, `NaturalPerson`, `PhysicalAddress` models |
| `registry` | `RegisteredEntity` (TS5 WalletRelyingParty), `SupervisoryAuthority`, entitlements, intermediary relationships |
| `credentials` | `Credential`, `Claim`, `IntendedUse` models for attestation formats (SD-JWT, mDL) |
| `tsl_generator` | ETSI TS 119612 Trust Status List XML generation |
| `certificates` | Certificate management |
| `rp_registration` | **Legacy app** - being migrated to modular structure, do not add new code here |

### Key Model Relationships

```
LegalEntity (1) ─── (1) RegisteredEntity ─── (*) EntityEntitlement
     │                      │
     └── LegalPerson        └── SupervisoryAuthority
     └── NaturalPerson      └── EntitySupportURI
     └── PhysicalAddress    └── IntendedUse → Credential → Claim
```

### API Structure

- `/api/registry/wrp/` - TS5 WalletRelyingParty endpoints (main external API)
- `/api/registry/entities/` - Internal entity management
- `/api/registry/supervisory-authorities/` - DPA records
- `/api/legal-entities/` - Legal entity CRUD
- `/api/tsl/` - Trust Status List generation

## Development Commands

```bash
# Start all services (Django + PostgreSQL + Redis)
make run

# Run tests (uses settings_test.py with SQLite)
make test

# Run specific test file
make test test-path=registry/tests/test_endoints.py

# Code formatting
make black && make isort

# Linting
make lint

# Database migrations
make migrations  # Create new migrations
make migrate     # Apply migrations

# Create admin user
make createsuperuser email=admin@example.com
```

## Coding Conventions

### Models

- **Always inherit from `core.models.BaseModel`** (provides UUID pk + timestamps)
- Use `models.TextChoices` for enums, define them in `core/models.py`
- Add `db_table` explicitly in Meta class
- Validation logic goes in `clean()` method

```python
from core.models import BaseModel, EntitlementType

class MyModel(BaseModel):
    entitlement = models.CharField(max_length=50, choices=EntitlementType.choices)
    
    class Meta:
        db_table = "app_my_model"
```

### Serializers

- Create separate serializers for list/create/detail operations
- Use `Serializer` (not `ModelSerializer`) for complex create operations with nested objects
- Reference: [registry/serializers.py](ms_registry/registry/serializers.py)

### Views

- Use DRF generic views (`ListCreateAPIView`, `RetrieveUpdateDestroyAPIView`)
- Support both JSON and HTML rendering via `TemplateHTMLRenderer`
- Views handle form rendering in `get()` for HTML requests

### Tests

- Test file: `registry/tests/test_endoints.py` (note: filename typo is intentional)
- Use `APITestCase` for API tests, `TestCase` for model tests
- Test settings in `ms_registry/settings_test.py` (uses SQLite, eager Celery)

## Important Specifications

This codebase implements EU Digital Identity Wallet standards:

- **TS5**: Common Formats and API for RP Registration Information
- **TS6**: Common Set of Information to be Registered
- **ARF Topic 27**: Registration of PID/Attestation Providers and RPs
- **ETSI TS 119612**: Trust Status Lists XML format

**Official JSON Schema**: [ts5-json-common-rp-data-model.json](https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/api/ts5-json-common-rp-data-model.json) - defines `WalletRelyingParty`, `Credential`, `Claim`, `IntendedUse`, `Identifier`, `SupervisoryAuthority` structures. The `/api/registry/wrp/` endpoint returns responses conforming to this schema.

The `RegisteredEntity` model is named differently from TS5's `WalletRelyingParty` but serves the same purpose - it covers ALL entity types (verifiers, issuers, QTSPs), not just relying parties.

## Authentication

Authentication is planned but not yet implemented. Views currently use `permission_classes = []`. When adding auth:
- Configure `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` in [ms_registry/settings.py](ms_registry/ms_registry/settings.py)
- Configure `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']` in settings
- Update individual view `permission_classes` as needed
- Store auth-related code (custom backends, permissions) in a new `ms_registry/authentication/` app

## ETSI TS 119612 Trust Status List Compliance

The `tsl_generator` app generates XML compliant with ETSI TS 119612 standard.

### Required Namespaces
All TSL XML must include these namespaces (see [tsl_generator/xml_generator.py](ms_registry/tsl_generator/xml_generator.py)):
```python
NS_TSL = "http://uri.etsi.org/02231/v2#"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_ADDTYPES = "http://uri.etsi.org/02231/v2/additionaltypes#"
NS_XADES = "http://uri.etsi.org/01903/v1.3.2#"
```

### Service Type URIs (eIDAS 2.0)
Key service types for EUDI Wallet ecosystem in [tsl_generator/models.py](ms_registry/tsl_generator/models.py):
- `http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer` - PID Issuer
- `http://uri.etsi.org/TrstSvc/Svctype/QEAA_Provider` - Qualified EAA Provider
- `http://uri.etsi.org/TrstSvc/Svctype/PUB_EAA_Provider` - Public Body EAA
- `http://uri.etsi.org/TrstSvc/Svctype/WalletProvider` - Wallet Provider

### TSL Structure
- `TSLScheme` → root scheme with version, sequence number, territory
- `TrustServiceProvider` → TSP information with multilingual names
- `TrustService` → individual services with status, certificates
- Multilingual support via `MultiLangName` and `MultiLangURI` abstract models

## CI/CD (GitHub Actions)

Workflow in `.github/workflows/tests.yml` runs on push/PR to `main`, `master`, `develop`:

| Job | Purpose |
|-----|---------|
| `test` | Run Django tests with PostgreSQL + Redis services |
| `lint` | flake8, black --check, isort --check-only |
| `coverage` | Generate coverage report, upload to Codecov |

**CI Environment**: Python 3.13, PostgreSQL 14, Redis 6.2

To match CI locally:
```bash
# Format before committing
make black && make isort

# Check linting
make lint

# Run tests
make test
```

## Docker Environment

- PostgreSQL on port `5433` (localhost), `5432` (container)
- Redis for caching/Celery
- Django dev server on port `8000`
- Code mounted at `/app` for hot-reload

Environment variables via `.env` file (see `docker-compose.yaml` for defaults).
