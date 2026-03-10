# CA Integration Use Cases
**Date**: 2026-03-10
**Sources**:
- ETSI TS 119 475 v1.1.1: https://www.etsi.org/deliver/etsi_ts/119400_119499/119475/01.01.01_60/ts_119475v010101p.pdf
- IT-Wallet Docs Issue #1055: https://github.com/italia/eid-wallet-it-docs/issues/1055
- Existing: `CA_usecase.md` (Use Case 1 — Registry Operator signing)
- Gap analysis: `summary_CA_gaps_20260309.md`

---

## Context

The ms-registry manages certificates at two distinct levels:

| Level | What | Who holds cert |
|---|---|---|
| **Registry level** | Registry signs its own API responses | Registry Operator |
| **Entity level** | Registered entities (WRPs, PID providers, etc.) hold certificates proving their role | Each registered entity |

Use Case 1 (Registry Operator signing) is documented in `CA_usecase.md`. This file covers **entity-level certificate issuance** (Use Cases 2–7) which are currently missing from the implementation.

---

## Certificate Types per Entity Role (from Issue #1055 + ETSI TS 119 475)

| Entity Role | Certificate Type | Required QCStatement OID | Standard |
|---|---|---|---|
| Wallet Relying Party | WRPAC / WRPRC | — (no QcType, policy-based) | ETSI TS 119 475 |
| PID Provider | End-entity sign/seal | `id-etsi-qct-pid` (0.4.0.194126.1.1) | ETSI TS 119 412-6 |
| Wallet Provider | End-entity | `id-etsi-qct-wal` (0.4.0.194126.1.2) | ETSI TS 119 412-6 |
| QEAA Provider | Qualified seal | `id-etsi-qct-eseal` (0.4.0.1862.1.6.2) | EN 319 412-5 |
| PSB EAA Provider | End-entity | `QcPSB` (country + auth source + legislation) | eIDAS 2.0 |
| EAA Provider (non-Q) | Standard seal | No specific QcType | EN 319 412-2/3 |

> **Important (from Issue #1055):** ETSI TS 119 412-6 defines end-entity sign/seal certificates only. There is no dedicated PID Issuer CA profile — the CA role is fulfilled by the **Federation Trust Anchor**.

---

## Use Case 2: WRPAC Issuance (Wallet Relying Party Access Certificate)

### What
A Wallet Relying Party (RP) registered in ms-registry requests a **WRP Access Certificate (WRPAC)** that allows it to present authenticated requests to Wallet Units.

### Actors
| Actor | Role |
|---|---|
| Registered Relying Party | Applicant — already registered in ms-registry with status ACTIVE |
| Registry Operator / TSP | Validates registration, initiates certificate request |
| National CA (Trust Service Provider) | Issues the WRPAC |
| Wallet Unit | Verifies WRPAC during presentation request |

### Preconditions
- RP entity exists in `RegisteredEntity` with `registration_status = ACTIVE`
- RP has at least one valid `EntityEntitlement` (e.g. `Service_Provider`)
- RP identity has been proofed (via `LegalEntity` and `Identifier` records)

### Flow (Registrar-Initiated — ETSI TS 119 475 Annex D model 2)
```
Relying Party                ms-registry              National CA (TSP)
     │                            │                          │
     │── POST /wrp/{id}/cert ────►│                          │
     │   request (or CSR upload)  │                          │
     │                            │── Validate ACTIVE status │
     │                            │── Validate entitlements  │
     │                            │── Build/verify CSR       │
     │                            │── POST issuance request ►│
     │                            │                          │── Issue WRPAC
     │                            │◄── Return certificate ───│
     │                            │                          │
     │                            │── Store in EntityAccessCertificate
     │                            │── Record CT log info
     │◄── 201 certificate_pem ────│
```

### Missing Implementation
- [ ] `POST /api/registry/wrp/{id}/certificate/request` endpoint
- [ ] CSR generation (using `cryptography` library, EC P-256)
- [ ] CA API client in `certificates/` app
- [ ] Auto-store result in `EntityAccessCertificate` with `is_current=True`
- [ ] CT log recording (`ct_log_id`, `ct_sct`)

### Certificate Content (WRPAC per ETSI TS 119 475)

X.509 v3 certificate (RFC 5280), signed by the National CA (TSP).

**Legal Person RP** (`entity_type = LEGAL_PERSON`):
```
Subject DN: CN=<trade_name>, O=<legal_name>, C=<country_code>
            serialNumber=<organisationsnummer / EUID>
```

**Natural Person RP** (`entity_type = NATURAL_PERSON`):
```
Subject DN: CN=<given_name> <family_name>, C=<country_code>
            serialNumber=<personnummer / eIDAS SERIAL_NUMBER>
```

**Common extensions (both entity types)**:
```
Key Usage:            digitalSignature  (critical)
Extended Key Usage:   id-kp-WRPAccess (TBD per TS 119 475 profile)
Policy OID:           links to WRP entitlement type (Service_Provider, PID_Provider, etc.)
Subject Alt Name:     URI = registry_uri of the registered entity
Basic Constraints:    CA:FALSE  (critical)
Validity:             as defined by TSP policy (typically 1–2 years)
```

> Source fields in ms-registry:
> - `trade_name` / `legal_name` → `RegisteredEntity.trade_name` / `LegalPerson.legal_name`
> - `serialNumber` → `Identifier.identifier_value` (primary identifier)
> - `country_code` → `PhysicalAddress.country_code`
> - `registry_uri` → `RegisteredEntity.registry_uri`

---

## Use Case 3: WRPRC Issuance (WRP Registration Certificate per IntendedUse)

### What
A WRPRC is issued **per data request use case** (per `IntendedUse`). It attests that a specific RP is authorized to request specific credentials (e.g. "Example Bank may request PID + driving licence for KYC").

### Actors
Same as Use Case 2 plus: the `IntendedUse` record defining what credentials may be requested.

### Preconditions
- `IntendedUse` record exists and is valid (`validity_start` ≤ today ≤ `validity_end`)
- Linked `IntendedUseCredential` records define the credential types and claims
- RP has corresponding `EntityEntitlement`

### Flow
```
ms-registry                              CA
     │                                    │
     │── Resolve IntendedUse.credentials ─┤
     │── Build WRPRC attributes           │
     │──── intended_use_identifier       │
     │──── claim paths (JSON pointers)   │
     │──── credential formats            │
     │── Submit CSR with policy info ───►│
     │◄── Receive WRPRC ─────────────────│
     │── Store in EntityRegistrationCertificate (OneToOne with IntendedUse)
```

### Missing Implementation
- [ ] `POST /api/registry/wrp/{id}/intended-use/{iu_id}/certificate` endpoint
- [ ] Mapping of `IntendedUseCredential` claims → certificate policy extensions
- [ ] Store in `EntityRegistrationCertificate` (model exists, no issuance logic)

---

## Use Case 4: PID Provider Certificate (QCStatement id-etsi-qct-pid)

### What
An entity registered with `entity_role = PID_PROVIDER` must hold an end-entity certificate with the `id-etsi-qct-pid` QCStatement, per ETSI TS 119 412-6.

### Key Requirement (from Issue #1055)
> The CA role for PID Providers is fulfilled by the **Federation Trust Anchor** — there is no separate PID Issuer CA profile.

### QCStatement Extension Required
```asn1
QcStatements ::= SEQUENCE OF QcStatement

QcStatement ::= SEQUENCE {
  statementId   OBJECT IDENTIFIER,  -- 0.4.0.194126.1.1 (id-etsi-qct-pid)
  statementInfo ANY DEFINED BY statementId OPTIONAL
}
```

### Flow
```
PID Provider                ms-registry          Federation Trust Anchor
     │                           │                         │
     │── Register as PID_PROVIDER►                         │
     │                           │── Validate role          │
     │                           │── Generate CSR with      │
     │                           │   QCStatement OID embedded│
     │                           │─────────────────────────►│
     │                           │◄── id-etsi-qct-pid cert ─│
     │                           │── Store certificate       │
     │◄── 201 certificate ───────│                          │
```

### Missing Implementation
- [ ] CSR builder that injects `id-etsi-qct-pid` OID into certificate extensions
- [ ] Mapping `EntityRole.PID_PROVIDER` → correct QCStatement OID
- [ ] Federation Trust Anchor API client (distinct from national CA)

---

## Use Case 5: QEAA Provider Certificate (Qualified Seal)

### What
An entity registered with `entitlement_type = QEAA_Provider` needs a **qualified electronic seal** certificate per EN 319 412-5.

### QCStatement
```
QcType OID: 0.4.0.1862.1.6.2 (id-etsi-qct-eseal)
```

### Notes
- Issued by a Qualified Trust Service Provider (QTSP), not a plain CA
- Must appear in the national TSL (already generated by `tsl_generator/`)
- Certificate must be linked to the TSP entry in `TrustServiceProvider` model

### Missing Implementation
- [ ] Distinguish QTSP vs plain CA in CA client
- [ ] Link issued certificate to `TSPCertificate` and `ServiceCertificate` in TSL
- [ ] OID injection for `id-etsi-qct-eseal` in CSR

---

## Use Case 6: PSB EAA Provider Certificate (QcPSB)

### What
A public sector body (`is_psb = True`) providing EAA attestations requires a certificate with the `QcPSB` extension.

### QcPSB Structure (from Issue #1055)
```asn1
QcPSB ::= SEQUENCE {
  countryOfLegislation    PrintableString (SIZE (2)),  -- e.g. "SE"
  authSourceIdentification UTF8String,                 -- authority identifier
  legislationIdentification UTF8String                 -- legal act reference
}
```

### Source Fields in ms-registry
| QcPSB Field | ms-registry Source |
|---|---|
| `countryOfLegislation` | `SupervisoryAuthority.country_code` |
| `authSourceIdentification` | `SupervisoryAuthority.authority_name` |
| `legislationIdentification` | `Law.law_uri` or `Law.law_name` |

### Missing Implementation
- [ ] `QcPSB` ASN.1 encoder in CSR builder
- [ ] Populate from `RegisteredEntity.is_psb`, `supervisory_authority`, linked `Law` records
- [ ] Validate `is_psb = True` before requesting PSB certificate

---

## Use Case 7: Certificate Revocation on Status Change

### What
When a `RegisteredEntity.registration_status` changes to `SUSPENDED` or `REVOKED`, the corresponding certificate(s) must be revoked at the CA and the status updated in `EntityAccessCertificate`.

### Flow
```
Admin / DPA action
     │
     │── PATCH /wrp/{id}/ {registration_status: "REVOKED"}
     │
     ▼
registry/views.py (signal or override save())
     │
     │── Find EntityAccessCertificate where is_current=True
     │── Call CA revocation API (OCSP/CRL or proprietary)
     │──── Pass: certificate_serial, revocation_reason
     │── On success:
     │──── Set EntityAccessCertificate.revoked_at = now()
     │──── Set EntityAccessCertificate.revocation_reason
     │──── Set EntityAccessCertificate.is_current = False
     │── Write to AuditLog
```

### Revocation Reasons (X.509 standard)
| Reason | When |
|---|---|
| `unspecified` (0) | Default |
| `keyCompromise` (1) | Private key leaked |
| `affiliationChanged` (3) | Entity details changed significantly |
| `superseded` (4) | Certificate renewed/replaced |
| `cessationOfOperation` (5) | Entity deregistered |
| `certificateHold` (6) | SUSPENDED (hold, reversible) |

### Missing Implementation
- [ ] Django signal or `save()` override on `RegisteredEntity` status change
- [ ] CA revocation API call (OCSP `revoke` or CA REST endpoint)
- [ ] `SUSPENDED` → `certificateHold`, `REVOKED` → `cessationOfOperation` mapping
- [ ] `GET /api/registry/wrp/{id}/certificate/status` endpoint for external status check

---

## Use Case 8: Certificate Renewal / Rotation

### What
Before a certificate expires (`not_after`), the registry automatically renews it.

### Flow
```
Celery Beat (scheduled task)
     │
     │── Query EntityAccessCertificate WHERE
     │   is_current=True AND not_after < NOW() + 30 days
     │
     │── For each expiring cert:
     │──── Generate new CSR (same key or re-keyed)
     │──── Submit to CA
     │──── Store new certificate (is_current=True)
     │──── Mark old cert is_current=False
     │──── Log to AuditLog
```

### Missing Implementation
- [ ] Celery periodic task for expiry check (Celery is in `requirements.txt` but unused for this)
- [ ] Re-key vs renewal policy decision
- [ ] Notify entity on renewal (hooks into notification system)

---

## Implementation Roadmap

```
Phase 1 — Foundation (unblocks all other use cases)
├── CA API client (generic, configurable per CA type)
├── CSR builder (EC P-256, extensible for QCStatements)
└── Real JWS signing (CA_usecase.md Use Case 1)

Phase 2 — Entity Certificate Issuance
├── UC2: WRPAC issuance endpoint
├── UC3: WRPRC issuance per IntendedUse
└── UC4: PID Provider cert with id-etsi-qct-pid

Phase 3 — Advanced Certificate Types
├── UC5: QEAA Provider (QTSP + qualified seal)
└── UC6: PSB EAA Provider (QcPSB extension)

Phase 4 — Lifecycle Management
├── UC7: Revocation on status change
└── UC8: Automated renewal (Celery)
```

---

## QCStatement OID Reference

| OID | Name | Used for |
|---|---|---|
| `0.4.0.194126.1.1` | id-etsi-qct-pid | PID Provider certificates |
| `0.4.0.194126.1.2` | id-etsi-qct-wal | Wallet Provider certificates |
| `0.4.0.1862.1.6.1` | id-etsi-qct-esign | Electronic signature certs |
| `0.4.0.1862.1.6.2` | id-etsi-qct-eseal | Electronic seal certs (QEAA) |
| `0.4.0.1862.1.6.3` | id-etsi-qct-web | Website authentication certs |

---

## References

- **ETSI TS 119 475 v1.1.1** — WRP Certificate Profiles: https://www.etsi.org/deliver/etsi_ts/119400_119499/119475/01.01.01_60/ts_119475v010101p.pdf
- **IT-Wallet Issue #1055** — QCStatement profiles for PID/QEAA/PSB: https://github.com/italia/eid-wallet-it-docs/issues/1055
- **ETSI TS 119 412-6** — QCStatements in EU certs (id-etsi-qct-pid, id-etsi-qct-wal)
- **EN 319 412-5** — Qualified certificate profile (QcType OIDs)
- **RFC 5280** — X.509 certificate and CRL profile
- **RFC 7515** — JSON Web Signature (JWS)
- **RFC 9162** — Certificate Transparency v2
- `CA_usecase.md` — Use Case 1: Registry Operator signing (existing)
- `summary_CA_gaps_20260309.md` — Full gap analysis vs ETSI TS 119 475
