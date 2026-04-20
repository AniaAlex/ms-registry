# Access Certificate Flows
**Date:** 2026-04-14

---

## What is an Access Certificate (WRPAC)?

A **Wallet Relying Party Access Certificate (WRPAC)** is an X.509 digital certificate
issued to registered entities (Relying Parties, PID Providers, EAA Providers). It serves
as both **digital identity** and **regulatory authorisation proof** — combining
cryptographic trust (chain to an EC-compiled CA Trusted List) with legal trust (verified
presence in a national registry). Without a valid WRPAC a Wallet Unit cannot interact
with the entity.

---

## Flow 1 — Simplified (ms-registry as cnf provider)

In this flow ms-registry does **not** act as a CA. It provides a signed confirmation
(`cnf`) of the entity's registry data. The entity (or their own CA) uses that data to
build and sign the certificate, then uploads it back to ms-registry for storage.

```
ENTITY / CA                         MS-REGISTRY
  │                                      │
  │  1. GET /certificates/cnf/{id}/      │
  │ ───────────────────────────────────▶ │ look up RegisteredEntity
  │                                      │ assemble confirmed registry data
  │                                      │ sign JWT with ECDSA P-256 private key
  │ ◀─────────────────────────────────── │
  │     signed JWT (cnf):                │
  │     {                                │
  │       "iss": "https://ms-registry",  │
  │       "sub": "<entity_id>",          │
  │       "exp": <timestamp>,            │
  │       "cnf": {                       │
  │         "name": "Example GmbH",      │
  │         "country": "DE",             │
  │         "org_identifier": "NTR...",  │
  │         "role": "relying_party",     │
  │         "entitlements": [...],       │
  │         "registration_status":"valid"│
  │       }                              │
  │     }                                │
  │                                      │
  │  2. Verify JWT signature             │
  │     GET /.well-known/jwks.json       │
  │ ───────────────────────────────────▶ │ return ms-registry public key (JWKS)
  │ ◀─────────────────────────────────── │
  │                                      │
  │  3. Build X.509 certificate          │
  │     using cnf data as subject DN     │
  │     and extension fields             │
  │     Sign with entity's own key       │
  │                                      │
  │  4. POST /certificates/upload/       │
  │     { entity_id, certificate_pem }   │
  │ ───────────────────────────────────▶ │ parse cert
  │                                      │ verify cert fields match registry data
  │                                      │ store in EntityAccessCertificate
  │ ◀─────────────────────────────────── │
  │     { certificate_id, status }       │
```

### ms-registry responsibilities

| Step | Action |
|------|--------|
| cnf endpoint | Verify entity `registration_status = valid`, sign JWT with ECDSA P-256 |
| JWKS endpoint | Expose public key at `/.well-known/jwks.json` for signature verification |
| Upload endpoint | Parse PEM, verify subject DN fields match registry, store record |

### cnf JWT payload

```json
{
  "iss": "https://ms-registry.example.eu",
  "sub": "<entity_id>",
  "iat": 1713000000,
  "exp": 1713086400,
  "cnf": {
    "name": "Example GmbH",
    "country": "DE",
    "org_identifier": "NTRDEU-HRB12345",
    "role": "relying_party",
    "entitlements": ["Service_Provider"],
    "registration_status": "valid"
  }
}
```

Signed with `ES256` (ECDSA P-256). ms-registry's private key is stored in the
environment variable `REGISTRY_SIGNING_KEY_PEM`. The corresponding public key is
published at `/.well-known/jwks.json`.

### What the model stores (EntityAccessCertificate)

- `certificate_pem` — full PEM
- `certificate_serial`, `certificate_fingerprint_sha256`
- `issuer_dn`, `subject_dn`
- `not_before`, `not_after`
- `is_current` — only one current cert per entity
- CT log fields (`ct_log_id`, `ct_sct`) — left null in simplified flow

---

## Flow 2 — Full Flow (including external Access CA)

In the full flow an external **Access Certificate Authority (Access CA)** issues the
certificate after independently verifying the entity's registration in the national
registry. The Wallet Unit performs dual validation on the resulting certificate.

```
ENTITY              MS-REGISTRY             ACCESS CA           WALLET UNIT
  │                      │                      │                     │
  │  Register entity     │                      │                     │
  │ ──────────────────▶  │                      │                     │
  │                      │ registration_status  │                     │
  │                      │ = valid              │                     │
  │                      │                      │                     │
  │  Request cert        │                      │                     │
  │  (submit CSR)        │                      │                     │
  │ ──────────────────▶  │                      │                     │
  │                      │  Notify Access CA    │                     │
  │                      │  entity registered   │                     │
  │                      │ ───────────────────▶ │                     │
  │                      │                      │ Query National      │
  │                      │                      │ Register API        │
  │                      │                      │ ─────────────────▶  │
  │                      │  ◀ ─ ─ ─ ─ ─ ─ ─ ─  │                     │
  │                      │  entity valid ✓      │                     │
  │                      │                      │ Issue X.509 cert    │
  │                      │                      │ (subject DN from    │
  │                      │                      │  registry data,     │
  │                      │                      │  policy OID,        │
  │                      │                      │  entitlements)      │
  │                      │                      │ Log to CT (RFC 9162)│
  │                      │                      │                     │
  │                      │  ◀─────────────────  │                     │
  │                      │  cert PEM + SCT      │                     │
  │                      │  Store in            │                     │
  │                      │  EntityAccessCert    │                     │
  │  ◀─────────────────  │                      │                     │
  │  cert issued ✓       │                      │                     │
  │                      │                      │                     │
  │  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ▶  │
  │  Present WRPAC during interaction with Wallet Unit                │
  │                      │                      │                     │
  │                      │                      │   1. Cert validation│
  │                      │                      │   chain → Access CA │
  │                      │                      │   in EC Trusted List│
  │                      │                      │                     │
  │                      │  ◀ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─  │
  │                      │  2. Registry query   │                     │
  │                      │  GET /entities/{id}/ │                     │
  │                      │  status = valid? ──▶ │                     │
  │                      │  entitlements match? │                     │
  │                      │ ─────────────────────────────────────────▶ │
  │                      │                      │   Trust established │
  │                      │                      │   interaction ✓     │
```

### Wallet Unit dual validation

When a Wallet Unit receives a WRPAC it performs **both** checks before trusting the entity:

| Check | What is verified |
|-------|-----------------|
| Certificate validation | Chain to an Access CA on the EC-compiled Access CA Trusted List (via LoTL discovery); OCSP/CRL status is `granted` |
| Registry validation | Extract `organizationIdentifier` from subject DN; query National Register API; verify `registration_status = valid` and entitlements match what was requested |

Both must pass. Either alone is insufficient.

### Certificate content (X.509 v3)

| Field | Value |
|-------|-------|
| Subject DN | C, O, organizationIdentifier (NTR prefix), CN |
| Subject Alternative Name | Support URI, email, phone |
| Certificate Policy OID | NCP-l-eudiwrp `0.4.0.194118.1.2` (or qualified variant) |
| Key Usage | digitalSignature (critical) |
| Extended Key Usage | id-kp-clientAuth |
| qcStatements | Entitlement OID (e.g. Service_Provider `0.4.0.19475.1.1`) |
| Validity | 1–2 years |

### Policy OIDs by entity type

| Entity | Policy | OID |
|--------|--------|-----|
| Relying Party (legal person) | NCP-l-eudiwrp | 0.4.0.194118.1.2 |
| Relying Party (natural person) | NCP-n-eudiwrp | 0.4.0.194118.1.1 |
| PID Provider | NCP-l-eudiwrp | 0.4.0.194118.1.2 |
| QEAA Provider | QCP-l-eudiwrp | 0.4.0.194118.1.4 |
| Non-Q EAA Provider | NCP-l-eudiwrp | 0.4.0.194118.1.2 |

### Lifecycle

| Event | Action |
|-------|--------|
| `registration_status → SUSPENDED` | Revoke cert at CA (`certificateHold`); set `revoked_at` |
| `registration_status → REVOKED` | Revoke cert at CA (`cessationOfOperation`); set `revoked_at` |
| Cert expiry T-30 days | Trigger renewal flow (new CSR → Access CA → new cert stored) |
| New cert issued | Set `is_current = True`; previous cert `is_current = False` |

---

## Comparison

| Aspect | Simplified Flow | Full Flow |
|--------|----------------|-----------|
| Who issues the cert | Entity / entity's own CA | External Access CA |
| ms-registry role | Signs cnf JWT; stores uploaded cert | Notifies Access CA; stores issued cert |
| CA trust anchor | Not in EC Trusted List | Must be in EC-compiled Access CA Trusted List |
| CT logging | Optional / null | Required per RFC 9162 |
| Wallet trust | Not standards-compliant | Fully compliant (ETSI TS 119 411-8, Reg. 2025/848) |
| Use case | Development / testing | Production EUDI Wallet deployments |

---

## References

- ETSI TS 119 411-8 — Access Certificate Policy for EUDI Wallet Relying Parties
- Regulation (EU) 2025/848 — Articles 7, 8, Annex IV, Annex V
- RFC 9162 — Certificate Transparency Version 2.0
- ARF (Architecture Reference Framework) — EUDI Wallet trust model
