# Certificates Module

The `certificates` Django app handles the full lifecycle of **Wallet Relying Party Access Certificates (WRPAC)** for the ms-registry simplified flow.

---

## Overview

In the simplified flow ms-registry does not act as a CA. Instead it:

1. Signs a **cnf JWT** confirming the entity's registry data.
2. Accepts the entity's finished **X.509 certificate** back for upload.
3. **Validates** the certificate against the registry data (ETSI TS 119 411-8).
4. Creates a **CT log entry** (RFC 9162 simplified) signed with the registry key.
5. Stores the certificate record in `EntityAccessCertificate`.

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET`  | `/certificates/cnf/<entity_id>/` | Return a signed cnf JWT for an active entity |
| `GET`  | `/certificates/cnf/<entity_id>/view/` | HTML page rendering the cnf result |
| `POST` | `/certificates/upload/<entity_id>/` | Upload and validate an access certificate (JSON) |
| `GET`  | `/certificates/upload/<entity_id>/view/` | HTML upload form |
| `POST` | `/certificates/upload/<entity_id>/view/` | HTML upload form submit |

---

## CNF JWT  (`GET /certificates/cnf/<entity_id>/`)

Returns an ES256-signed JWT with the confirmed registry data used to build the X.509 certificate.

**Eligibility**: entity `registration_status` must be `active` → 409 CONFLICT otherwise.

**JWT payload:**

```json
{
  "iss": "https://ms-registry.example.eu",
  "sub": "<entity_uuid>",
  "iat": 1713000000,
  "exp": 1713086400,
  "cnf": {
    "name": "Example GmbH",
    "country": "DE",
    "org_identifier": "NTRDEU-HRB12345",
    "org_identifier_type": "NATIONAL_BUSINESS_REG",
    "role": "relying_party",
    "entitlements": ["Service_Provider"],
    "registration_status": "active"
  }
}
```

- Algorithm: `ES256` (ECDSA P-256)
- Key ID: `ms-registry-signing-key-v1`
- Validity: 24 hours
- Signing key: `REGISTRY_SIGNING_KEY_PEM` environment variable

---

## Certificate Upload  (`POST /certificates/upload/<entity_id>/`)

### Request

```json
{ "certificate_pem": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----" }
```

### Response (201)

```json
{
  "id": "<uuid>",
  "certificate_serial": "3A4F...",
  "certificate_fingerprint_sha256": "a1b2c3...",
  "subject_dn": "CN=Example GmbH,O=Example GmbH,C=DE",
  "issuer_dn": "...",
  "not_before": "2025-01-15T00:00:00+00:00",
  "not_after": "2027-01-15T00:00:00+00:00",
  "ct_log_id": "1.3.6.1.4.1.<PEN>.1",
  "ct_log_timestamp": "2025-01-15T10:00:00+00:00"
}
```

### Error responses

| Status | Reason |
|--------|--------|
| 400 | Certificate validation failed (details in body) |
| 404 | Entity not found |
| 409 | Entity is not active |

---

## Certificate Validation  (`certificates/serializers.py`)

`AccessCertificateUploadSerializer` validates the uploaded PEM against the entity's registered data.

### Checks (ETSI TS 119 411-8)

| # | Check | Standard ref |
|---|-------|-------------|
| 1 | Valid PEM-encoded X.509 certificate | RFC 5280 |
| 2 | Validity period: `not_before ≤ now ≤ not_after` | RFC 5280 §4.1.2.5 |
| 3 | Subject `C` matches entity's country | EN 319 412-1 |
| 4 | Subject `O` matches entity's display name | EN 319 412-1 |
| 5 | Subject `organizationIdentifier` matches formatted primary identifier | EN 319 412-1 §5.1.4 |
| 6 | `KeyUsage`: `digitalSignature`, **critical** | TS 119 411-8 §6 |
| 7 | `ExtendedKeyUsage`: `id-kp-clientAuth` | TS 119 411-8 §6 |
| 8 | `CertificatePolicies`: at least one eudiwrp OID | TS 119 411-8 §5.1 |
| 9 | SAN `RegisteredID` OIDs cover all registered entitlements | TS 119 475 |

### eudiwrp policy OIDs

| OID | Policy |
|-----|--------|
| `0.4.0.194118.1.1` | NCP-n-eudiwrp (natural person) |
| `0.4.0.194118.1.2` | NCP-l-eudiwrp (legal person) |
| `0.4.0.194118.1.3` | QCP-n-eudiwrp (qualified, natural person) |
| `0.4.0.194118.1.4` | QCP-l-eudiwrp (qualified, legal person) |

### organizationIdentifier format (EN 319 412-1)

`{PREFIX}{COUNTRY}-{VALUE}` — e.g. `NTRSE-5568002755`

| Identifier type | Prefix |
|----------------|--------|
| EUID | EUID |
| VAT_NUMBER | VAT |
| LEI | LEI |
| EORI | EORI |
| NATIONAL_BUSINESS_REG | NTR |
| NATIONAL_TAX_REG | TAX |
| SERIAL_NUMBER | PAS |
| OTHER | OTH |

### Entitlement OIDs (TS 119 475)

| Entitlement | OID |
|-------------|-----|
| Service_Provider | `0.4.0.19475.1.1` |
| QEAA_Provider | `0.4.0.19475.1.2` |
| Non_Q_EAA_Provider | `0.4.0.19475.1.3` |
| PUB_EAA_Provider | `0.4.0.19475.1.4` |
| PID_Provider | `0.4.0.19475.1.5` |

---

## CT Log Entry  (`certificates/ct_log.py`)

In the simplified flow ms-registry acts as the CT log, using its own ECDSA P-256 signing key.  See [ct_log.md](ct_log.md) for full details including how to obtain an IANA-allocated OID.

### SCT wire format (stored in `EntityAccessCertificate.ct_sct`)

TLS-encoded `TransItemList` (RFC 9162 §4.5) containing a single `x509_sct_v2` `TransItem`:

```
TransItemList
└── TransItem
    ├── type   uint16 = 1  (x509_sct_v2)
    └── data   SignedCertificateTimestampDataV2
        ├── log_id      1-byte len + OID DER value bytes  (RFC 9162 §4.4)
        ├── timestamp   uint64 ms since epoch
        ├── extensions  uint16 len = 0
        └── signature   SignatureScheme(0x0403) + uint16 len + ECDSA-P256 bytes
```

| Field | RFC 9162 reference | Value |
|-------|--------------------|-------|
| `log_id` | §4.4 — OID from IANA CT Log Parameters registry | `CT_LOG_OID` env var (DER-encoded OID value) |
| `timestamp` | §4.8 — milliseconds since epoch | time of upload |
| `signature` | §4.8 — ecdsa_secp256r1_sha256 (0x0403) | ECDSA-P256 over signed content |

> **Note**: This is a simplified local log — not a full RFC 9162 Merkle-tree log. CT log fields (`ct_log_id`, `ct_log_timestamp`, `ct_sct`) are `null` in the full flow, where an external Access CA handles CT logging.

---

## Data Model  (`EntityAccessCertificate`)

| Field | Type | Description |
|-------|------|-------------|
| `registered_entity` | FK → RegisteredEntity | Owner entity |
| `certificate_serial` | CharField | Hex serial number |
| `certificate_fingerprint_sha256` | CharField | SHA-256 of DER |
| `issuer_dn` | CharField | Issuer distinguished name |
| `subject_dn` | CharField | Subject distinguished name |
| `not_before` / `not_after` | DateTimeField | Validity window |
| `ct_log_id` | CharField | RFC 9162 §4.4 log identifier |
| `ct_log_timestamp` | DateTimeField | Time of CT log entry |
| `ct_sct` | BinaryField | JSON-encoded SCT record |
| `is_current` | BooleanField | Only one `True` per entity at a time |
| `revoked_at` / `revocation_reason` | DateTimeField / CharField | Revocation info |
| `certificate_pem` | TextField | Full PEM-encoded certificate |

Only one certificate per entity has `is_current=True`. On every successful upload the previous current certificate is set to `is_current=False`.

---

## Normative References

- ETSI TS 119 411-8 v1.1.1 — Access Certificate Policy for EUDI Wallet Relying Parties
- ETSI EN 319 412-1 — Certificate Profiles: Overview and common data structures
- ETSI TS 119 475 — Relying party attributes supporting EUDI Wallet user's authorization decisions
- RFC 9162 — Certificate Transparency Version 2.0
- RFC 5280 — Internet X.509 Public Key Infrastructure Certificate and CRL Profile
- CIR (EU) 2025/848 — Registration of wallet-relying parties
