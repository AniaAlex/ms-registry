# CA Integration Gaps — ETSI TS 119 475 Analysis
**Date**: 2026-03-09
**Standard**: ETSI TS 119 475 v1.1.1 — Wallet-Relying Party (WRP) Certificates
**Link**: https://www.etsi.org/deliver/etsi_ts/119400_119499/119475/01.01.01_60/ts_119475v010101p.pdf

---

## Standard Overview

ETSI TS 119 475 defines certificate profiles and policy requirements for **Wallet-Relying Parties (WRPs)** within the EU digital identity ecosystem (eIDAS/EUDIW framework). It specifies how Trust Service Providers (TSPs) issue and manage certificates used by relying parties that interact with **EU Digital Identity Wallets**.

### Key Certificate Types
| Acronym | Full Name | Purpose |
|---|---|---|
| **WRPC** | Wallet-Relying Party Certificate | General certificate for WRPs |
| **WRPAC** | WRP Access Certificate | Used when accessing wallet data |
| **WRPRC** | WRP Registration Certificate | Used during relying party registration |

### Certificate Issuance Models (Annex D)
1. **Integrated model** — WRP and registration occur simultaneously
2. **Registrar-initiated** — Third-party registration services initiate certificate requests
3. **RP-initiated post-registration** — Relying parties request certificates after prior registration

---

## Gap Analysis: Standard vs Current Implementation

### What's Well Covered ✓

| Standard Requirement | Implementation |
|---|---|
| WRP identification (legal/natural person) | `legal_entities/models.py` — `LegalPerson`, `NaturalPerson`, `Identifier` |
| WRP entitlement tracking | `registry/models.py` — `EntityEntitlement` with URI-based entitlement types |
| Certificate storage (PEM, metadata) | `certificates/models.py` — `EntityAccessCertificate`, `EntityRegistrationCertificate` |
| Certificate Transparency (CT logs) | `EntityAccessCertificate` has `ct_log_id`, `ct_sct` per RFC 9162 |
| Certificate status lifecycle | PENDING → ACTIVE → SUSPENDED → REVOKED in `RegistrationStatus` |
| TSL publication (ETSI TS 119612) | `tsl_generator/` — full XML generation |
| JWKS well-known endpoint | `/.well-known/jwks.json` — exists but placeholder key |

---

### Critical Gaps — CA Integration

The standard defines three issuance models (Annex D). **None are implemented.**

#### 1. CSR Generation (missing entirely)
The standard requires WRPs to submit a Certificate Signing Request. No CSR generation endpoint or flow exists. Needed:
```
POST /api/registry/wrp/{id}/certificate/request
→ generate keypair or accept CSR
→ forward to CA
→ store issued certificate
```

#### 2. CA Connectivity (missing entirely)
`CA_usecase.md` documents the intent but nothing is wired up. The `EntityAccessCertificate` model has all the right fields (`certificate_pem`, `issuer_dn`, `ct_sct`) but no code populates them via a real CA. Needed:
- CA API client (ACME, EST, or proprietary CA REST API)
- Certificate chain validation
- Automated renewal before expiry

#### 3. Certificate Revocation / Status Checking (missing)
The standard mandates revocation infrastructure. The `revoked_at` / `revocation_reason` fields exist in the DB but:
- No OCSP responder integration
- No CRL publication endpoint
- No automated revocation on entity status change (e.g., when entity → SUSPENDED, cert should be revoked at CA)

#### 4. JWS Response Signing (placeholder only)
`registry/views.py` — `JWKSView` uses a hardcoded placeholder key. The standard requires the registry to sign its responses with a real key so wallet units can verify them. The `REGISTRY_SIGNING_KEY` env var is referenced but never loaded.

---

### Other Missing Pieces (per TS 119 475)

| Standard Requirement | Gap |
|---|---|
| **JWT/CWT certificate payloads** | Only X.509 PEM stored; no JWT/CWT wrapping of certificate claims |
| **WRPAC issuance flow** | Model exists, no issuance workflow |
| **WRPRC issuance** | Linked to `IntendedUse` but no issuance logic |
| **Identity proofing** before cert issuance | No workflow to verify WRP identity before issuing cert |
| **API authentication** (mTLS or OAuth2) | No auth on registry endpoints |
| **OpenID Connect discovery** | `/.well-known/openid-configuration` missing |
| **Notification on status changes** | `ms-registry-notification-system.md` documents it, not implemented |

---

## Recommended Priority Order

1. **Real JWS signing** — load `REGISTRY_SIGNING_KEY` and sign API responses (quick win, unblocks wallet integration)
2. **CA integration** — pick a CA (e.g., self-hosted EJBCA, or cloud CA), implement issuance client in `certificates/`
3. **CSR/certificate request endpoint** — wire up the issuance flow end-to-end
4. **Revocation sync** — when entity status → SUSPENDED/REVOKED, call CA revocation API
5. **API authentication** — mTLS or OAuth2 before exposing to external parties

---

## Related Files in This Repo

| File | Relevance |
|---|---|
| `CA_usecase.md` | Documents JWS signing and certificate use cases (intent, not implemented) |
| `ms_registry/certificates/models.py` | `EntityAccessCertificate`, `EntityRegistrationCertificate`, `AuditLog` |
| `ms_registry/registry/views.py` | `JWKSView` — placeholder signing key |
| `ms_registry/tsl_generator/` | ETSI TS 119612 TSL XML generation |
| `ms_registry/tsl_generator/management/commands/generate_pid_cert.py` | Self-signed X.509 cert generation (test only) |
