# WRPRC App - Wallet Relying Party Registration Certificate

**Standard**: ETSI TS 119 475  
**Date**: 2026-03-19

---

## WRPAC vs WRPRC — Two Different Certificates

Per **ETSI TS 119 475**, Relying Parties hold TWO distinct credentials:

| | WRPAC | WRPRC |
|---|---|---|
| **Full name** | Wallet Relying Party **Access** Certificate | Wallet Relying Party **Registration** Certificate |
| **Format** | X.509 | JWT (`rc-wrp+jwt`) |
| **Purpose** | RP **authenticates itself** to Wallet | RP **proves entitlements** to Wallet user |
| **Issued by** | TSP/QTSP (external CA) | Registry (ms-registry) |
| **RP has private key?** | ✅ Yes | ❌ No |
| **Shown to** | Wallet (TLS/connection layer) | Wallet user (consent screen) |
| **Multiple per RP?** | Yes (one per deployment) | One per RP (or per intended use) |
| **Standard section** | ETSI TS 119 475 §4.3 / §5.1 | ETSI TS 119 475 §4.4 / §5.2 |

### WRPAC (Access Certificate)

```
TSP/QTSP (e.g., Telia CA)
    │
    └── Issues X.509 certificate TO the RP
          │
          └── RP holds private key
                │
                └── RP uses cert to authenticate to Wallet
```

- **What it proves**: "I am who I claim to be" (identity)
- **Model in ms-registry**: `certificates.EntityAccessCertificate` (tracks certs issued by external CA)

### WRPRC (Registration Certificate)

```
ms-registry
    │
    └── Signs JWT ABOUT the RP
          │
          └── JWT contains RP's registration info + entitlements
                │
                └── RP presents JWT to Wallet
                      │
                      └── Wallet shows info to user before consent
```

- **What it proves**: "I am registered and authorized to request these credentials" (entitlements)
- **Model in ms-registry**: `wrprc.IssuedWRPRC` ← **this app**

### How They Work Together

```
RP connects to Wallet:
    │
    ├── 1. TLS handshake with WRPAC (X.509)
    │      └── Wallet verifies: "Is this really Bank AB?"
    │
    └── 2. Presents WRPRC (JWT) in protocol
           └── Wallet shows user: "Bank AB wants your name and age"
           └── User sees entitlements before consenting
```

---

## Overview

This app handles issuance and management of **WRPRCs** (Wallet Relying Party Registration Certificates) — signed JWTs that RPs present to Wallets to prove their registration and entitlements.

---

## Trust Model: X.509/TSL (Not OpenID Federation)

The WRPRC follows the **X.509/TSL** trust model:

```
ms-registry signs WRPRC
    │
    └── JWT header contains x5c (certificate chain)
          │
          └── Wallet verifies:
                1. JWT signature valid
                2. x5c[0] cert → chains to TSL-listed CA
                3. TSL → signed by national authority (PTS)
                4. National authority → listed in EC LOTL
```

### X.509/TSL vs OpenID Federation

| Aspect | WRPRC (X.509/TSL) | OpenID Federation |
|--------|-------------------|-------------------|
| **Trust anchor** | TSL → LOTL | Federation Trust Anchor |
| **Key discovery** | `x5c` header + TSL | `/.well-known/openid-federation` |
| **Signature format** | JWT with `x5c` (cert chain) | JWT signed by federation key |
| **Trust verification** | Verify cert chain → TSL | Verify ES chain → Trust Anchor |
| **Standard** | ETSI TS 119 475 | OpenID Federation 1.0 |

---

## WRPRC JWT Structure

### Header

```json
{
  "typ": "rc-wrp+jwt",
  "alg": "ES256",
  "kid": "wrprc-signing-key-2026",
  "x5c": ["MIIBxTC...base64-cert..."]
}
```

### Payload

```json
{
  "jti": "550e8400-e29b-41d4-a716-446655440000",
  "iat": 1683000000,
  "exp": 1714536000,
  "name": "Example Bank AB",
  "sub": {
    "legal_name": "Example Bank AB",
    "id": "LEI-529900T8BM49AURSDO55"
  },
  "country": "SE",
  "purpose": [
    {"lang": "en-US", "value": "Required for KYC verification"},
    {"lang": "sv-SE", "value": "Krävs för KYC-verifiering"}
  ],
  "privacy_policy": "https://bank.se/privacy",
  "credentials": [
    {
      "format": "dc+sd-jwt",
      "meta": {"vct_values": ["https://credentials.example/pid"]},
      "claims": [{"path": ["given_name"]}, {"path": ["family_name"]}]
    }
  ],
  "entitlements": [
    "https://uri.etsi.org/19475/Entitlement/Service_Provider"
  ],
  "public_body": false,
  "status": {
    "status_list": {
      "idx": 42,
      "uri": "https://ms-registry.se/api/wrprc/status/wrprc-abc123"
    }
  }
}
```

---

## Components

| File | Purpose |
|------|---------|
| `models.py` | `StatusList`, `IssuedWRPRC`, `SigningKey` |
| `issuer.py` | `WRPRCIssuer` — builds payload from registry data |
| `signing.py` | `LocalSigner`, `KMSSigner`, `HSMSigner` backends |
| `views.py` | API endpoints |
| `urls.py` | URL routing |
| `admin.py` | Django admin |
| `serializers.py` | DRF serializers |

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/wrprc/issue/` | POST | Issue new WRPRC |
| `/api/wrprc/entity/<id>/` | GET | List WRPRCs for entity |
| `/api/wrprc/<jti>/` | GET | Get WRPRC details |
| `/api/wrprc/<jti>/revoke/` | POST | Revoke WRPRC |
| `/api/wrprc/status/<list_id>/` | GET | Status list for verification |
| `/api/wrprc/keys/` | GET | WRPRC signing keys |

Global endpoint (in `registry`):
| `/.well-known/jwks.json` | GET | Aggregated JWKS (registry + WRPRC keys) |

---

## Revocation: Status List

WRPRCs use bitstring-based revocation (like SD-JWT Status List):

```
StatusList (bitstring)
├── Bit 0: WRPRC #0 status (0=valid, 1=revoked)
├── Bit 1: WRPRC #1 status
├── Bit 2: WRPRC #2 status
└── ...

WRPRC contains:
  "status": {
    "status_list": {
      "idx": 42,           ← position in bitstring
      "uri": "https://..."  ← where to fetch status list
    }
  }
```

Wallet verifies by:
1. Fetch status list from `uri`
2. Check bit at position `idx`
3. If bit = 1 → WRPRC revoked → reject

---

## Key Management

### Options

| Backend | Security | Use Case |
|---------|----------|----------|
| `LocalSigner` | ❌ Low | Development only |
| `KMSSigner` | ✅ High | Production (AWS) |
| `HSMSigner` | ✅✅ Highest | High-security |

### Why Isolated Key Management?

WRPRC signing key is **high-value** — compromise means attackers can issue fake registration certificates.

```
If WRPRC signing key compromised:
    └── Attacker issues fake WRPRCs
          └── Impersonate any RP to any Wallet
                └── Steal credentials from citizens
```

**Key should never be accessible to application code** — use KMS or HSM.

---

## Relationship to OpenID Federation

This app implements the **X.509/TSL path** for RPs. OpenID Federation is a **separate, parallel** trust model:

| Entity Type | Trust Path | Credential |
|-------------|------------|------------|
| **Relying Parties** | X.509/TSL | WRPRC (this app) |
| **PID/EAA Providers** | OpenID Federation | Entity Statement + Trust Marks |

For federation support, a separate `federation/` app would be needed with:
- `/.well-known/openid-federation` — Entity Configuration
- `/federation/fetch?sub=<entity>` — Subordinate Entity Statements
- `/federation/list` — List subordinates

---

## JWKS Integration

WRPRC signing keys are included in the global `/.well-known/jwks.json`:

```json
{
  "keys": [
    { "kid": "ms-registry-signing-key-v1", ... },  // Registry key
    { "kid": "wrprc-signing-key-2026", ... }       // WRPRC key (from this app)
  ]
}
```

Primary consumers:
- **Wallets** — verify WRPRC before showing consent screen
- **Other registries** — cross-border verification
- **Audit systems** — signature validation

---

## Configuration

```python
# settings.py

# Signer type: 'local', 'kms', or 'hsm'
WRPRC_SIGNER_TYPE = 'local'  # Use 'kms' in production

# For LocalSigner (dev only)
WRPRC_PRIVATE_KEY_PATH = '/path/to/private-key.pem'

# For KMSSigner (production)
WRPRC_KMS_KEY_ID = 'arn:aws:kms:eu-north-1:123456789:key/abc-123'

# Base URL for status list URIs
WRPRC_BASE_URL = 'https://ms-registry.se'
```

---

## References

- **ETSI TS 119 475** — WRP certificate profiles (WRPAC, WRPRC)
- **RFC 7517** — JSON Web Key (JWK)
- **RFC 7519** — JSON Web Token (JWT)
- **SD-JWT Status List** — Bitstring revocation mechanism
- **EUDI ARF** — Architecture Reference Framework
