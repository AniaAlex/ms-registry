# Access Certificates in the ARF
**Date**: 2026-05-12  
**Source**: EUDI Architecture and Reference Framework (ARF) v2.8.0

---

## Overview

Access Certificates are X.509 digital certificates issued to all registered entities in the EUDI Wallet ecosystem. They enable authentication during interactions with Wallet Units.

---

## Access Certificate Authorities (ARF Section 3.18)

> "Access Certificate Authorities issue an access certificate to all PID Providers, QEAA Providers, PuB-EAA Providers, and non-qualified EAA Providers in the EUDI Wallet ecosystem. In addition, each Relying Party in the ecosystem also receives one or more access certificates, one for each of its Relying Party Instances."

### Key Characteristics

| Aspect | Details |
|--------|---------|
| **Recipients** | ALL registered entities: PID Providers, Attestation Providers, Relying Parties (per-instance) |
| **Purpose** | Prove authenticity and validity when interacting with Wallet Units |
| **Prerequisite** | Entity must be registered by a Registrar |
| **Notification** | Access CAs are notified by Member State to EC |
| **Trust Anchor Publication** | Trust anchors included in a List of Trusted Entities (LoTE) |
| **CT Logging** | Access CAs log all certificates in Certificate Transparency logs (RFC 9162) |

### Notification and Trust Infrastructure

> "Access Certificate Authorities are notified by a Member State to the Commission. As part of the notification process, the trust anchors of the Access CA are included in a List of Trusted Entities (LoTE) by a Trusted List or LoTE Provider."

Wallet Units need these trust anchors to verify signatures over access certificates presented to them.

---

## Wallet Unit Verification Flow (ARF Section 6.6.3.2)

When a Wallet Unit receives an access certificate from a Relying Party Instance:

```
Relying Party Instance                    Wallet Unit
        │                                      │
        │  1. Prepare request + include        │
        │     access certificate               │
        │ ──────────────────────────────────▶  │
        │                                      │
        │  2. Sign request with private key    │
        │ ──────────────────────────────────▶  │
        │                                      │
        │                                      │ 3. Verify signature using
        │                                      │    public key in cert
        │                                      │
        │                                      │ 4. Validate cert chain to
        │                                      │    trust anchor from LoTE
        │                                      │
        │                                      │ 5. Check revocation status
        │                                      │    (OCSP/CRL)
        │                                      │
        │                                      │ 6. Request User approval
        │                                      │
        │  ◀────────────────────────────────── │ 7. Return approved attributes
```

### Validation Steps

1. **Signature verification** — Using public key in access certificate
2. **Certificate chain validation** — To trust anchor from Access CA LoTE
3. **Revocation checking** — For all certificates in chain including trust anchor

---

## Relationship with Registrars (ARF Section 3.17)

> "When a PID Provider or Attestation Provider is registered by a Member State, an Access Certificate Authority associated with the Registrar issues an access certificate to the PID Provider or to the Attestation Provider."

### Registration Flow

```
Entity                  Registrar              Access CA              LoTE Provider
   │                        │                      │                       │
   │  1. Register           │                      │                       │
   │ ────────────────────▶  │                      │                       │
   │                        │                      │                       │
   │                        │  2. Notify Access CA │                       │
   │                        │ ───────────────────▶ │                       │
   │                        │                      │                       │
   │                        │                      │  3. Verify against    │
   │                        │                      │     National Register │
   │                        │                      │                       │
   │                        │                      │  4. Issue Access Cert │
   │                        │ ◀─────────────────── │                       │
   │                        │                      │                       │
   │  5. Receive cert       │                      │                       │
   │ ◀────────────────────  │                      │                       │
```

---

## Access Certificate vs Registration Certificate

| Certificate Type | Issued By | Mandatory | Purpose |
|------------------|-----------|-----------|---------|
| **Access Certificate** | Access CA | **Yes** | Authentication during interactions with Wallet Units |
| **Registration Certificate** | Provider of Registration Certificates | No (per MS policy) | Contains registered data (attributes, intended use, scope) |

### Access Certificate Content

- Does **not** indicate entity type (PID Provider, QEAA Provider, etc.)
- Does **not** contain registered attestation types
- Contains: identity information, certificate policies, trust chain

### Registration Certificate Content (if issued)

- Contains (subset of) data registered for entity
- Attestation types entity may issue
- Intended use descriptions for Relying Parties
- Privacy policy URLs

> "A PID Provider access certificate does not indicate that its subject is a PID Provider. Similarly, an Attestation Provider access certificate does not indicate that its subject is a QEAA Provider, a PuB-EAA Provider, or a non-qualified EAA Provider."

---

## Certificate Issuance Models (ETSI TS 119 475 Annex D)

| Model | Description | Registrar/CA Relationship |
|-------|-------------|---------------------------|
| **D.1 Integrated Model** | Registration and certificate issuance simultaneous | Same entity |
| **D.2 Registrar-Initiated** | Registrar initiates certificate request to separate CA | Separate entities |
| **D.3 RP-Initiated Post-Registration** | Entity requests certificate from CA after registration | Separate entities |

### Integrated Model Implications

If a service acts as both Registrar AND Access CA:

1. **Two EC notifications required**:
   - Notify as `WRPRegistrar` (with `register`, `registerURI`)
   - Notify as `WRPAccCertProvider` (with CA certificates, policies)

2. **Appears on two trusted lists**:
   - Registrar list
   - Access CA LoTE

3. **Must meet requirements for both roles**:
   - Registrar operational requirements
   - TSP (Trust Service Provider) requirements for CA

---

## Revocation and Lifecycle (ARF Section 6.4.3)

> "Suspension or cancellation involves revocation of all valid access certificates of the Relying Party by the relevant Access CA, such that the Relying Party is no longer able to interact with Wallet Units."

### Status Changes

| Event | Action |
|-------|--------|
| `registration_status → SUSPENDED` | Access CA revokes certificate (`certificateHold`) |
| `registration_status → CANCELLED` | Access CA permanently revokes certificate |
| Entity re-activated | New certificate must be issued |

---

## References

- **ARF Section 3.17** — Registrars
- **ARF Section 3.18** — Access Certificate Authorities
- **ARF Section 3.19** — Providers of Registration Certificates
- **ARF Section 6.4.2** — Relying Party Registration
- **ARF Section 6.6.3.2** — Wallet Unit authenticates the Relying Party Instance
- **ETSI TS 119 475** — Wallet-Relying Party (WRP) Certificates
- **CIR 2025/848** — Registration of Wallet Relying Parties
