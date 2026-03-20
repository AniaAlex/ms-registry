# OpenID Federation Summary for ms-registry
**Date**: 2026-03-13
**Context**: How ms-registry fits into the OpenID Federation model

---

## OpenID Federation Levels

```
Trust Anchor (TA)           ← iss == sub, self-signed Entity Configuration
    │
    ▼
Intermediate                ← Issues Subordinate Entity Statements about entities below
    │
    ▼
Leaf Entity                 ← End entities (RPs, Issuers) with Entity Configurations
```

---

## ms-registry Options in the Federation Hierarchy

### Option 1: Intermediate (Most Likely)

ms-registry acts as an **Intermediate** — it issues **Subordinate Entity Statements** about registered entities (PID Providers, QEAA Providers, RPs).

```json
{
  "iss": "https://ms-registry.se",           // ms-registry
  "sub": "https://pid-provider.skatteverket.se",  // registered entity
  "jwks": { /* entity's public keys */ },
  "metadata": {
    "openid_credential_issuer": { ... }
  },
  "trust_marks": [
    { "id": "http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer" }
  ]
}
```

**Trust Chain:**
```
National/EU Trust Anchor
    └── Subordinate ES about ms-registry (as Intermediate)
          └── ms-registry issues Subordinate ES about:
                ├── PID Providers
                ├── QEAA Providers
                └── Relying Parties (for federation path)
```

### Option 2: Trust Anchor (Less Likely)

ms-registry itself is the **National Federation Trust Anchor** — `iss == sub`.

```json
{
  "iss": "https://ms-registry.se",
  "sub": "https://ms-registry.se",
  "metadata": {
    "federation_entity": {
      "federation_fetch_endpoint": "https://ms-registry.se/api/federation/fetch",
      "federation_list_endpoint": "https://ms-registry.se/api/federation/list"
    }
  }
}
```

This would require ms-registry to be **trusted out-of-band** (like the EC LOTL signing cert is trusted via the Official Journal).

---

## Key Federation Endpoints ms-registry Would Need

| Endpoint | Purpose |
|----------|---------|
| `/.well-known/openid-federation` | Entity Configuration (self-signed) |
| `/federation/fetch?sub=<entity>` | Return Subordinate ES for a registered entity |
| `/federation/list` | List all subordinate entities |
| `/federation/resolve?sub=<entity>` | Resolve full trust chain |

---

## Recommended Architecture

```
EU Federation Trust Anchor (EC-level)
    └── PTS as National Federation Trust Anchor
          └── ms-registry as Intermediate
                └── Subordinate ES about registered entities
```

This mirrors the X.509/TSL hierarchy where PTS signs the TSL and ms-registry generates the content.

---

## Trust Mark vs Intermediate

| Concept | What it is | What it does |
|---------|-----------|--------------|
| **Intermediate** | An **entity role** in the hierarchy | Issues Subordinate Entity Statements, forms part of the trust chain |
| **Trust Mark** | A **signed assertion** (JWT) | Certifies a specific property/status about an entity |

---

## Trust Mark Structure

A Trust Mark is a JWT issued by a **Trust Mark Issuer** (which could be a TA, Intermediate, or dedicated issuer):

```json
{
  "iss": "https://trust-mark-issuer.eu",      // who issued the mark
  "sub": "https://pid-provider.skatteverket.se", // who receives it
  "id": "http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer",  // what it certifies
  "iat": 1773405121,
  "exp": 1804941121
}
```

---

## How Trust Marks and Intermediates Relate

```
Trust Anchor
    │
    ├── Issues Subordinate ES about Intermediate (trust chain)
    │
    └── Issues Trust Marks (certifications)
          │
          ▼
Intermediate (e.g., ms-registry)
    │
    ├── Issues Subordinate ES about Leaf Entities (trust chain)
    │
    └── MAY issue Trust Marks (if authorized as Trust Mark Issuer)
          │
          ▼
Leaf Entity (e.g., PID Provider)
    │
    └── Entity Configuration includes received Trust Marks
```

---

## Example: PID Provider's Entity Configuration

```json
{
  "iss": "https://pid-provider.skatteverket.se",
  "sub": "https://pid-provider.skatteverket.se",
  "jwks": { ... },
  "trust_marks": [
    {
      "id": "http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer",
      "trust_mark": "eyJhbGciOiJFUzI1NiIs..."  // JWT signed by Trust Mark Issuer
    }
  ]
}
```

---

## Key Distinction: Subordinate Entity Statement vs Trust Mark

| | Subordinate Entity Statement | Trust Mark |
|---|---|---|
| Purpose | Establishes **hierarchy** (who vouches for whom) | Asserts **certification** (what status/property) |
| Required for trust chain? | Yes | No (supplementary) |
| Who can issue? | Only TAs and Intermediates | Authorized Trust Mark Issuers |
| Content | Entity's keys, metadata, policies | Just the certification assertion |

---

## What "id" Certifies in a Trust Mark

The **Trust Mark ID** (`id`) is a URI that identifies **what property or status** the Trust Mark asserts about the entity.

When a Trust Mark Issuer signs a Trust Mark with a specific `id`, they're making a **formal assertion**:

> "I, the Trust Mark Issuer, certify that the entity (`sub`) has the status/property identified by this `id`."

### Example Breakdown

```json
{
  "iss": "https://ms-registry.se",                          // Issuer says:
  "sub": "https://pid-provider.skatteverket.se",            // "This entity..."
  "id": "http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer"   // "...is a PID Issuer"
}
```

**Translation**: "ms-registry certifies that Skatteverket's PID Provider is an authorized PID Issuer."

---

## Common Trust Mark IDs for EUDI

| Trust Mark ID | What it certifies |
|---------------|-------------------|
| `http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer` | Entity is authorized to issue PIDs |
| `http://uri.etsi.org/TrstSvc/Svctype/QEAA_Provider` | Entity is a Qualified EAA Provider |
| `http://uri.etsi.org/TrstSvc/Svctype/PUB_EAA_Provider` | Entity is a Public Body EAA Provider |
| `http://uri.etsi.org/TrstSvc/Svctype/WalletProvider` | Entity is an authorized Wallet Provider |

These URIs are the **same service type identifiers** used in the TSL (ETSI TS 119 612).

---

## Analogy: Trust Marks as Real-World Certifications

| Real world | OpenID Federation |
|------------|-------------------|
| ISO 27001 certificate | Trust Mark with `id: "...ISO27001"` |
| Medical license | Trust Mark with `id: "...MedicalPractitioner"` |
| PID Issuer authorization | Trust Mark with `id: "...PID_Issuer"` |

The `id` is **what** is being certified. The signature proves **who** certified it and **when**.

---

## Why URIs for Trust Mark IDs?

URIs are used because:
1. **Globally unique** — no collisions
2. **Dereferenceable** — can point to a spec defining the certification criteria
3. **Namespace control** — `http://uri.etsi.org/...` means ETSI defines what it means to be a `PID_Issuer`

So when ms-registry issues a Trust Mark with `id: "http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer"`, it's asserting the entity meets ETSI's definition of a PID Issuer — not some arbitrary interpretation.

---

## For ms-registry Implementation

ms-registry could be:
1. **Intermediate** — issues Subordinate ES about registered entities
2. **Trust Mark Issuer** — issues Trust Marks certifying entities as `PID_Provider`, `QEAA_Provider`, etc.
3. **Both** — common pattern where the registry does both

The entitlements in ms-registry (`Service_Provider`, `PID_Provider`, etc.) map naturally to **Trust Mark IDs**.

---

## Example: eduGAIN OIDF Pilot Trust Anchor

Reference Entity Configuration from the eduGAIN pilot:

```json
{
  "exp": 1773491521,
  "iat": 1773405121,
  "iss": "https://ta.oidf-pilot.edugain.org",
  "jwks": {
    "keys": [
      {
        "alg": "ES256",
        "crv": "P-256",
        "kid": "xcXdyJ2_7cOd05QIqfpdrb3j5-mYFw8dqdcqzEh0lUw",
        "kty": "EC",
        "use": "sig",
        "x": "hh5u_VrRXLaXNAdZX2CQWNAXFqgDCYhYGY1y1qbx9Q8",
        "y": "qNPeoZOuVv-I6e-oUt9imwV6TSt-ymTaaW2Mrlgo0JQ"
      }
    ]
  },
  "metadata": {
    "federation_entity": {
      "contacts": ["support@edugain.org"],
      "display_name": "eduGAIN OIDF Pilot Trust Anchor",
      "federation_enroll_endpoint": "https://ta.oidf-pilot.edugain.org/enroll",
      "federation_fetch_endpoint": "https://ta.oidf-pilot.edugain.org/fetch",
      "federation_list_endpoint": "https://ta.oidf-pilot.edugain.org/list",
      "federation_resolve_endpoint": "https://ta.oidf-pilot.edugain.org/resolve",
      "organization_name": "eduGAIN",
      "organization_uri": "https://edugain.org"
    }
  },
  "sub": "https://ta.oidf-pilot.edugain.org"
}
```

Note: `iss == sub` indicates this is a **Trust Anchor** (self-signed Entity Configuration).

---

## References

- **OpenID Federation 1.0** — https://openid.net/specs/openid-federation-1_0.html
- **ETSI TS 119 612** — Trust Status List format (service type URIs)
- **EUDI ARF** — Architecture Reference Framework
- **tsl_signing_certificate_20260310.md** — Trust chain breakdown for ms-registry
