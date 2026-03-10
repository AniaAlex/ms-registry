# CA Role and Certificate Types — Breakdown
**Date**: 2026-03-10
**Context**: UC4 in CA_usecases_20260310.md — PID Provider certificate issuance

---

## What a CA Normally Does

In X.509 PKI, a CA signs a certificate that says:
> "I, the CA, attest that this public key belongs to this entity, and this entity is who they claim to be."

The certificate is trusted because you trust the CA that signed it.

---

## The PID Provider Case Is Different

A PID Provider issues **Personal Identification Data** — the most sensitive credential
in the EUDI wallet (name, DOB, nationality). The question is: *who vouches that a
given organisation is a legitimate PID Provider?*

Per ETSI TS 119 412-6 + IT-Wallet Issue #1055: **not a national CA, but the OpenID
Federation Trust Anchor**.

### Why

1. The Federation Trust Anchor already knows which entities are authorised PID Providers
   — it controls the OpenID Federation and has issued Entity Statements to each PID
   Provider as part of federation onboarding.
2. There is no separate PKI profile for a "PID Issuer CA" — the standards body
   decided not to create one.
3. The Trust Anchor's signature on an Entity Statement *is* the authorisation —
   adding a separate X.509 CA on top would be redundant.

---

## Two Trust Models Side by Side

### Standard X.509 PKI (used for WRPAC/WRPRC — UC2, UC3)
```
National CA (TSP)
└── signs X.509 certificate → Relying Party
    └── Certificate contains: public key, Subject DN, Key Usage, Policy OID
    └── Verified by: Wallet Unit checking X.509 chain
```

### OpenID Federation (used for PID Provider — UC4)
```
Federation Trust Anchor (e.g. EC or national authority)
└── signs Entity Statement (JWT) → PID Provider
    └── Entity Statement contains:
          - PID Provider's public key
          - metadata (endpoints, supported credentials)
          - id-etsi-qct-pid QCStatement assertion (OID: 0.4.0.194126.1.1)
    └── Verified by: Wallet Unit resolving federation trust chain
```

The `id-etsi-qct-pid` OID still appears — but it is embedded in the Entity Statement
JWT, not in an X.509 certificate signed by a separate CA.

---

## Impact on ms-registry Implementation

| UC | Certificate type | Issued by | API client needed |
|---|---|---|---|
| UC1 | X.509 signing cert (registry) | National CA | CA API client |
| UC2 | WRPAC (X.509) | National CA (TSP) | CA API client |
| UC3 | WRPRC (X.509, per IntendedUse) | National CA (TSP) | CA API client |
| **UC4** | **Entity Statement with id-etsi-qct-pid** | **Federation Trust Anchor** | **Federation TA API client (separate)** |
| UC5 | Qualified seal (X.509) | QTSP | QTSP API client |
| UC6 | X.509 with QcPSB | National CA | CA API client |

The "CA API client" for PID Providers does **not** talk to a national CA.
It talks to the Federation Trust Anchor — different endpoint, different protocol
(OpenID Federation Entity Statement submission), different trust model.

---

## References

- **ETSI TS 119 412-6** — QCStatements in EU certificates (id-etsi-qct-pid, id-etsi-qct-wal)
- **IT-Wallet Issue #1055** — QCStatement profiles for PID/QEAA/PSB: https://github.com/italia/eid-wallet-it-docs/issues/1055
- **OpenID Federation 1.0** — Entity Statements and Trust Anchor role
- `CA_usecases_20260310.md` — UC4 flow and missing implementation items
