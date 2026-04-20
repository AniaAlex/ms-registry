# MS Registry

A national **Member State Registry** for the EUDI Wallet ecosystem, implementing the
Wallet Relying Party registration infrastructure defined in
[ETSI TS 119 475](https://www.etsi.org/deliver/etsi_ts/119400_119499/119475/01.01.01_60/ts_119475v010101p.pdf)
and the
[TS5 Common Formats and API for RP Registration](https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts5-common-formats-and-api-for-rp-registration-information.md).

---

## What is ms-registry?

ms-registry is the national registry component in a Member State's EUDI Wallet trust
infrastructure. It is the authoritative source of truth for which entities are legally
authorised to interact with EUDI Wallet Units — Relying Parties (verifiers), PID
Providers, and Attestation Providers.

Its core responsibilities:

| Responsibility | Description |
|---|---|
| Entity registration | Onboard Relying Parties, PID Providers, and EAA Providers with legal entity data, entitlements, and intended use declarations |
| TS5 WRP API | Expose registered entities per the TS5 specification (`GET/POST/PUT/DELETE /wrp/`) |
| Access certificate support | Issue signed `cnf` JWTs; store uploaded Access Certificates (`EntityAccessCertificate`) |
| LoTE export | Publish the national List of Trusted Entities (`GET /registry/lote-se/`) consumed by the tsl-tool for signing and distribution |
| Intended use check | `GET /wrp/check-intended-use/` — signed check whether an entity has a registered intended use matching given criteria |

---

## Summary

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                     MS REGISTRY                          │
                    │                                                          │
                    │  RegisteredEntity ──► LegalEntity                       │
                    │       │                                                  │
                    │       ├── EntityEntitlement (Service_Provider, ...)      │
                    │       ├── EntitySupportURI                               │
                    │       ├── IntendedUse → Credential → Claim               │
                    │       ├── EntityAccessCertificate (WRPAC PEM)            │
                    │       └── SupervisoryAuthority                           │
                    │                                                          │
                    │  Endpoints                                               │
                    │  ├── /registry/wrp/            TS5 WRP API               │
                    │  ├── /registry/lote-se/         LoTE JSON export         │
                    │  ├── /certificates/cnf/{id}/    signed cnf JWT           │
                    │  ├── /certificates/upload/{id}/ cert upload              │
                    │  └── /.well-known/jwks.json     registry public key      │
                    └──────────────────────────────────────────────────────────┘
```

The registry signs responses with an ECDSA P-256 key (`REGISTRY_SIGNING_KEY_PEM`).
The corresponding public key is published at `/.well-known/jwks.json` for verification.

---

## How to launch

### Prerequisites

- Docker and Docker Compose
- A `.env` file at the project root (copy from `.env.example` if present)

### Start

```bash
make run
# or directly:
docker-compose up -d
```

### Migrate and create admin user

```bash
make migrate
make createsuperuser email=you@example.com
```

### Run tests

```bash
make pytest
# specific path:
make pytest test-path=registry/tests/
```

### Other commands

```bash
make lint        # flake8
make black       # black formatter
make isort       # import ordering
make migrations  # create new migrations
```

---

## ms-registry and Access Certificate CA

An **Access Certificate (WRPAC)** is an X.509 certificate issued to registered entities.
It acts as both cryptographic identity and regulatory authorisation proof — a Wallet Unit
cannot interact with an entity that does not hold a valid WRPAC chaining to a trusted
Access CA.

ms-registry supports simplified flow depending on the deployment stage.

---

### Simplified flow (ms-registry as cnf provider)

Used for **development and testing**. ms-registry does not act as a CA — it provides a
signed `cnf` JWT confirming the entity's registry data. The entity (or their own CA) uses
that data to build and self-sign a certificate, then uploads it back.

```
ENTITY / CA                         MS-REGISTRY
  │                                      │
  │  1. GET /certificates/cnf/{id}/      │
  │ ───────────────────────────────────▶ │ look up RegisteredEntity
  │                                      │ assemble confirmed registry data
  │                                      │ sign JWT (ES256, ECDSA P-256)
  │ ◀─────────────────────────────────── │
  │     signed cnf JWT                   │
  │                                      │
  │  2. Verify JWT signature             │
  │     GET /.well-known/jwks.json       │
  │ ───────────────────────────────────▶ │ return ms-registry public key (JWKS)
  │ ◀─────────────────────────────────── │
  │                                      │
  │  3. Build X.509 certificate          │
  │     using cnf data as subject DN     │
  │     Sign with entity's own key       │
  │                                      │
  │  4. POST /certificates/upload/{id}/  │
  │ ───────────────────────────────────▶ │ parse cert, verify fields
  │                                      │ store in EntityAccessCertificate
  │ ◀─────────────────────────────────── │
  │     { certificate_id, status }       │
```

---

### Full flow (external Access CA)
### Not implemented 
Used for **production** EUDI Wallet deployments. An external Access CA issues the
certificate after independently verifying registry status. Wallet Units perform dual
validation: certificate chain to the Access CA on the EC Trusted List **and** a live
registry status check.

```
ENTITY              MS-REGISTRY             ACCESS CA           WALLET UNIT
  │                      │                      │                     │
  │  Register entity     │                      │                     │
  │ ──────────────────▶  │ status = valid        │                     │
  │                      │                      │                     │
  │  Submit CSR          │                      │                     │
  │ ──────────────────▶  │                      │                     │
  │                      │── Notify Access CA ─▶│                     │
  │                      │                      │── Query registry    │
  │                      │                      │── Issue X.509 cert  │
  │                      │                      │   (policy OID,      │
  │                      │                      │    entitlements,    │
  │                      │                      │    CT log SCT)      │
  │                      │◀── cert PEM + SCT ───│                     │
  │                      │   store in           │                     │
  │                      │   EntityAccessCert   │                     │
  │ ◀──────────────────  │                      │                     │
  │                      │                      │                     │
  │  Present WRPAC ──────────────────────────────────────────────────▶│
  │                      │                      │  1. Chain → Access  │
  │                      │                      │     CA in EC TL     │
  │                      │◀─────────────────────────────────────────  │
  │                      │  2. GET /registry/   │                     │
  │                      │     wrp/{id}/        │                     │
  │                      │     status = valid?  │                     │
  │                      │─────────────────────────────────────────▶  │
  │                      │                      │  Trust established  │
```

| Aspect | Simplified | Full |
|--------|-----------|------|
| Who signs the cert | Entity (self-signed) | External Access CA |
| ms-registry role | Signs cnf JWT; stores cert | Notifies CA; stores cert |
| Wallet trust | Dev/test only | Fully compliant (ETSI TS 119 411-8) |
| CT logging | Not required | Required (RFC 9162) |

---

### Downloading the cnf and generating a certificate (dev)

**Step 1 — Download the cnf JWT**

```bash
curl https://<registry-host>/certificates/cnf/<entity_id>/
```

The response is a signed JWT. The `cnf` claim contains the entity's confirmed registry
data (name, country, org identifier, role, entitlements).

**Step 2 — Generate a self-signed certificate from the cnf**

Use the built-in dev management command (`make gen-access-cert`):

```bash
make gen-access-cert token=<jwt_from_step_1>
```

This calls
[`core/management/commands/generate_access_certificates_help_function.py`](ms_registry/core/management/commands/generate_access_certificates_help_function.py)
which:

- Decodes the cnf JWT (without signature verification — dev only)
- Maps registry data to X.509 Subject DN per ETSI EN 319 412-1/2/3
- Assigns the correct certificate policy OID (NCP-l-eudiwrp / NCP-n-eudiwrp)
- Encodes entitlement OIDs in the Subject Alternative Name
- Generates a fresh EC P-256 key pair and produces a self-signed certificate

Output: **private key PEM** (keep secret) + **certificate PEM** (upload to registry).

**Step 3 — Upload the certificate**

```bash
curl -X POST https://<registry-host>/certificates/upload/<entity_id>/ \
  -H "Content-Type: application/json" \
  -d '{"certificate_pem": "<PEM>"}'
```

Or use the upload UI at `/certificates/upload/<entity_id>/view/`.

> **Note:** The private key never leaves the entity. ms-registry stores only the
> certificate PEM in `EntityAccessCertificate`.

---

## Deployed example

| Resource | URL |
|---|---|
| API root | https://trust-dev-1.iam.sunet.se/api/ |
| API docs (Swagger) | https://trust-dev-1.iam.sunet.se/api/docs/#/registry/registry_lote_se_retrieve |
| Admin panel | https://trust-dev-1.iam.sunet.se/api/admin/ |

---

## Key API endpoints

| Endpoint | Description |
|---|---|
| `GET /registry/wrp/` | List all registered Wallet Relying Parties |
| `POST /registry/wrp/` | Register a new WRP |
| `GET /registry/wrp/{id}/` | Retrieve a single WRP |
| `GET /registry/wrp/check-intended-use/` | Check if a WRP has a registered intended use (JWS-signed) |
| `GET /registry/lote-se/` | LoTE JSON document (ETSI TS 119 602) |
| `GET /certificates/cnf/{id}/` | Download signed cnf JWT for an entity |
| `POST /certificates/upload/{id}/` | Upload an Access Certificate PEM |
| `GET /.well-known/jwks.json` | Registry public signing key (JWKS) |
