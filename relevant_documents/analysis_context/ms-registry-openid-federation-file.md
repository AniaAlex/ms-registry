# ms-registry: OpenID Federation vs DID-based Registries
**Date**: 2026-03-19
**Context**: Comparison of ms-registry (OpenID Federation) and IDunion (DID-based) approaches

---

## Two Parallel Approaches to Trust Registries

| | IDunion | ms-registry (ours) |
|---|---|---|
| **Identity format** | `did:web:...` | `https://...` (URL) |
| **Trust model** | DID + Verifiable Credentials | OpenID Federation + TSL |
| **Metadata** | DID Document (JSON-LD) | Entity Configuration (JWT) |
| **Discovery** | `/.well-known/did.json` | `/.well-known/openid-federation` |
| **Trust chain** | Governance framework + VCs | Trust Anchor → Subordinate ES |
| **Certifications** | Verifiable Credentials | Trust Marks |
| **Standard** | W3C DID/VC | OpenID Foundation + ETSI |

---

## Architecture Comparison

```
IDunion (DID-based):                    ms-registry (Federation-based):

IDunion Governance                      EU/National Trust Anchor
       │                                        │
       ▼                                        ▼
Trust List API                          ms-registry (Intermediate)
       │                                        │
       ▼                                        ▼
DID Documents                           Subordinate Entity Statements
       │                                        │
       ▼                                        ▼
Entities (did:web:...)                  Entities (https://...)
```

---

## IDunion Example: DID Document

```json
{
  "@context": [
    "https://www.w3.org/ns/did/v1",
    "https://w3id.org/security/suites/jws-2020/v1"
  ],
  "id": "did:web:tl-api.dev.idunion.info:api:v1:OT60PCYh:8f1vr",
  "controller": ["did:web:tl-api.dev.idunion.info:api:v1:OT60PCYh:8f1vr"],
  "verificationMethod": [{
    "id": "did:web:tl-api.dev.idunion.info:api:v1:OT60PCYh:8f1vr#",
    "type": "JsonWebKey2020",
    "controller": "did:web:tl-api.dev.idunion.info:api:v1:OT60PCYh:8f1vr",
    "publicKeyJwk": {
      "crv": "P-256",
      "kty": "EC",
      "x": "-8YxSGeEgjDMWUh2OJtyiX4A94kStp9zxr3oiaL-0iI",
      "y": "o4yDteR-OZtnGI0D0_H6Z3xr2EY7tG3FMmJ8ZLrOVr8"
    }
  }],
  "assertionMethod": ["did:web:tl-api.dev.idunion.info:api:v1:OT60PCYh:8f1vr#"],
  "service": [{
    "id": "did:web:...#urn:uuid:55e616d5-...",
    "type": "LinkedVerifiablePresentation",
    "serviceEndpoint": "https://tl-api.dev.idunion.info/api/v1/..."
  }]
}
```

---

## ms-registry as OpenID Federation Intermediate

```
National Trust Anchor (e.g., PTS)
    │
    └── Subordinate ES about ms-registry
          │
          └── ms-registry issues:
                ├── Subordinate ES about PID Providers
                ├── Subordinate ES about QEAA Providers
                ├── Subordinate ES about Relying Parties
                │
                └── Trust Marks:
                      ├── "http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer"
                      ├── "http://uri.etsi.org/TrstSvc/Svctype/QEAA_Provider"
                      └── "http://uri.etsi.org/TrstSvc/Svctype/Service_Provider"
```

---

## What ms-registry Needs for Federation Support

| Component | Endpoint | Purpose |
|-----------|----------|---------|
| Entity Configuration | `/.well-known/openid-federation` | Self-signed JWT describing ms-registry |
| Fetch endpoint | `/federation/fetch?sub=<entity>` | Return Subordinate ES for registered entities |
| List endpoint | `/federation/list` | List all subordinate entities |
| Resolve endpoint | `/federation/resolve?sub=<entity>` | Resolve full trust chain |
| Signing key management | Internal | Keys for signing ES and Trust Marks |
| Trust Mark issuance | Internal | Certify entitlements |

---

## Example: ms-registry Entity Configuration

```json
{
  "iss": "https://ms-registry.se",
  "sub": "https://ms-registry.se",
  "iat": 1773405121,
  "exp": 1773491521,
  "jwks": {
    "keys": [{
      "kty": "EC",
      "crv": "P-256",
      "kid": "ms-registry-signing-key-2026",
      "x": "...",
      "y": "..."
    }]
  },
  "metadata": {
    "federation_entity": {
      "organization_name": "Swedish Member State Registry",
      "contacts": ["registry@pts.se"],
      "federation_fetch_endpoint": "https://ms-registry.se/federation/fetch",
      "federation_list_endpoint": "https://ms-registry.se/federation/list",
      "federation_resolve_endpoint": "https://ms-registry.se/federation/resolve"
    }
  },
  "authority_hints": ["https://trust-anchor.pts.se"]
}
```

---

## Example: Subordinate Entity Statement (for a PID Provider)

```json
{
  "iss": "https://ms-registry.se",
  "sub": "https://pid-provider.skatteverket.se",
  "iat": 1773405121,
  "exp": 1773491521,
  "jwks": {
    "keys": [{ /* PID Provider's public key */ }]
  },
  "metadata": {
    "openid_credential_issuer": {
      "credential_issuer": "https://pid-provider.skatteverket.se",
      "credential_configurations_supported": {}
    }
  },
  "trust_marks": [{
    "id": "http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer",
    "trust_mark": "eyJhbGciOiJFUzI1NiIs..."
  }]
}
```

---

## DID vs OpenID Federation: Key Differences

| Aspect | DID | OpenID Federation |
|--------|-----|-------------------|
| **Trust establishment** | Resolve DID → trust the document | Verify JWT signature → trace to Trust Anchor |
| **Hierarchical trust** | ❌ Not built-in | ✅ Core feature (TA → Intermediate → Leaf) |
| **Self-signed** | ✅ DID Document can be plain JSON | ✅ Only Trust Anchors (`iss == sub`) |
| **Subordinate statements** | ❌ Not a concept | ✅ Core feature (TA vouches for entities) |
| **Trust Marks** | ❌ Uses VCs instead | ✅ Built-in certification mechanism |
| **Signature required** | ❌ Optional | ✅ Always (JWT) |

---

## `did:web` is NOT Decentralized

Despite the name "Decentralized Identifier," `did:web` relies on:
- **DNS** (centralized, ICANN-controlled)
- **HTTPS** (requires CA-issued certificate)
- **Web server** (single point of control)

| DID Method | Decentralized? |
|------------|----------------|
| `did:btcr`, `did:ethr`, `did:ion` | ✅ Yes (blockchain) |
| `did:key`, `did:peer` | ✅ Yes (self-contained) |
| `did:web` | ❌ No (DNS/HTTPS) |
| `did:ebsi` | ⚠️ Permissioned (EU blockchain) |

---

## Both Valid for EUDI

| Approach | Status |
|----------|--------|
| OpenID Federation (ms-registry) | ✅ EUDI ARF preferred |
| DID-based (IDunion) | ✅ Valid, may need bridging |
| X.509/TSL | ✅ Required for certificate validation |

---

## JSON-LD Context (DID Schema)

The `@context` in DID Documents defines the vocabulary:

```json
{
  "@context": {
    "verificationMethod": {
      "@id": "https://w3id.org/security#verificationMethod",
      "@type": "@id"
    },
    "assertionMethod": {
      "@id": "https://w3id.org/security#assertionMethod",
      "@type": "@id",
      "@container": "@set"
    },
    "service": {
      "@id": "https://www.w3.org/ns/did#service",
      "@type": "@id"
    }
  }
}
```

| Term | Maps To | Meaning |
|------|---------|---------|
| `verificationMethod` | `https://w3id.org/security#verificationMethod` | Cryptographic keys |
| `assertionMethod` | `https://w3id.org/security#assertionMethod` | Keys for signing |
| `service` | `https://www.w3.org/ns/did#service` | Service endpoints |

---

## Learning Resources

| Topic | URL |
|-------|-----|
| DID Core | https://www.w3.org/TR/did-core/ |
| DID:web Method | https://w3c-ccg.github.io/did-method-web/ |
| JSON-LD | https://www.w3.org/TR/json-ld11/ |
| Verifiable Credentials | https://www.w3.org/TR/vc-data-model-2.0/ |
| OpenID Federation | https://openid.net/specs/openid-federation-1_0.html |
| JSON-LD Playground | https://json-ld.org/playground/ |

---

## Summary

```
IDunion = DID-based registry       ← W3C standards (did:web, VCs)
ms-registry = Federation-based     ← OpenID Foundation + ETSI standards
              + TSL generation        (EUDI ARF aligned)
```

Both serve similar purposes with different technical approaches. ms-registry aligns with EUDI ARF specifications by using OpenID Federation + ETSI TSL.

---

## References

- **W3C DID Core** — https://www.w3.org/TR/did-core/
- **OpenID Federation 1.0** — https://openid.net/specs/openid-federation-1_0.html
- **ETSI TS 119 612** — Trust Status List format
- **EUDI ARF** — Architecture Reference Framework
- **IDunion** — https://idunion.org/
