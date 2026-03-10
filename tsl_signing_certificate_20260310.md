# TSL Signing Certificate — Trust Chain Breakdown
**Date**: 2026-03-10
**Context**: Who signs the Swedish TSL and how it chains to the EU LOTL

---

## The Full Trust Chain

```
EU Official Journal
└── lists: EC root cert (LOTL signing cert)
    └── EC signs LOTL (List of Trusted Lists)
        └── LOTL entry for Sweden:
              - TSL location URL
              - Swedish TSL signing cert (fingerprint)
                └── PTS signs Swedish TSL with this cert
                    └── Swedish TSL lists all Swedish TSPs/QTSPs
                        └── TSPs issue ServiceCertificates to entities
                            (PID Providers, QEAA Providers, etc.)
```

---

## Level 1 — EU Trust Anchor: LOTL

| Property | Value |
|---|---|
| Published by | European Commission |
| Contains | All Member State TSL locations + TSL signing certs |
| Signing cert listed in | EU Official Journal |
| Standard | ETSI TS 119 612 |

The LOTL is the root of trust for the entire European trust infrastructure.
A Relying Party trusts a national TSL because the EC's LOTL says that TSL is legitimate.

---

## Level 2 — National Trust Anchor: Swedish TSL signing cert

| Property | Value |
|---|---|
| Issued to | PTS (Post- och telestyrelsen) |
| Role | Swedish TSL Scheme Operator |
| Used for | Signing the Swedish TSL XML |
| Listed in | EC LOTL (so RPs can verify the TSL signature) |
| Standard | ETSI TS 119 612 |

PTS is the Swedish supervisory authority for trust services. It holds the TSL
signing key and is responsible for the integrity of the Swedish TSL.

---

## Level 3 — TSL Content: QTSPs and their ServiceCertificates

The Swedish TSL lists:

```
Swedish TSL (signed by PTS)
├── TrustServiceProvider: "National QTSP" (e.g. Telia CA, Nexus)
│   └── TSPCertificate        ← QTSP's own organisational cert
│   └── ServiceCertificate    ← QTSP's signing/issuing cert
│       └── QTSP uses this to issue qualified certs to others
│
└── TrustServiceProvider: "Skatteverket" (PID Provider)
    └── TSPCertificate        ← Skatteverket's organisational cert
    └── ServiceCertificate    ← Skatteverket's PID signing cert
        └── carries id-etsi-qct-pid OID
        └── issued BY the QTSP above
        └── Skatteverket uses this to sign PIDs to citizens
```

---

## Role of ms-registry

ms-registry generates the TSL XML content via `tsl_generator/` but does **not**
hold the TSL signing key. The operational boundary is:

| Step | Who |
|---|---|
| Generate TSL XML content | ms-registry (`tsl_generator/`) |
| Sign the TSL XML | PTS (holds TSL signing cert) |
| Publish TSL at official URL | PTS |
| List Sweden in LOTL | European Commission |

This boundary is currently **not documented** in the codebase. ms-registry's
`tsl_generator/` produces unsigned XML — the submission-to-PTS step is a missing
operational workflow.

---

## How a Relying Party Verifies a PID

```
Relying Party receives PID (SD-JWT) from Citizen Wallet
    │
    │ 1. Extract x5c from PID header
    │    → leaf cert = Skatteverket ServiceCertificate
    │
    │ 2. Fetch Swedish TSL (or use cached copy)
    │    → verify TSL signature against PTS cert
    │    → verify PTS cert against LOTL entry
    │
    │ 3. Find Skatteverket TrustServiceProvider in TSL
    │    → find matching ServiceCertificate
    │
    │ 4. Chain verified: x5c leaf matches TSL entry ✓
    │
    │ 5. Verify PID signature against ServiceCertificate ✓
    │
    └── Trust the PID claims ✓
```

---

## Two Parallel Trust Paths (X.509 vs OpenID Federation)

| | X.509 / TSL path | OpenID Federation path |
|---|---|---|
| Root anchor | EC LOTL | OpenID Federation Trust Anchor |
| National anchor | PTS TSL signing cert | National federation operator |
| Entity trust | ServiceCertificate in TSL | Subordinate Entity Statement |
| Used for | PID signature verification | RP/Issuer metadata trust |
| Convergence | Same political authority (Member State + EC) | Same political authority |

Both paths are required in the EUDI framework. They operate in parallel and
ultimately represent the same governmental authority through different technical
mechanisms.

---

## Who Issues WRPAC/WRPRC in Sweden — PTS Role

**PTS does not issue WRPAC/WRPRC directly.** Its role is supervisory:

| Role | Entity | What they do |
|---|---|---|
| Supervisory authority | PTS | Approves and lists QTSPs in Swedish TSL, signs TSL |
| QTSP (issues WRPAC/WRPRC) | e.g. Telia CA, Nexus | PTS-approved CA that actually issues certificates |
| Registry Operator | ms-registry deployer | Requests WRPAC/WRPRC from QTSP on behalf of RP |

```
PTS
├── supervises and lists approved QTSPs in Swedish TSL
│
└── Swedish TSL
    └── TrustServiceProvider: "Approved QTSP" (e.g. Telia CA)
        └── ServiceCertificate: CA cert for WRP issuance
            └── QTSP issues WRPAC/WRPRC to registered RP
                └── ms-registry requests this via CA API client
```

So when ms-registry calls the "national CA API client" (UC2/UC3), it is calling
a **PTS-approved QTSP**, not PTS itself. PTS's role is to:
1. Qualify the QTSP and list it in the TSL
2. Sign the TSL so Wallet Units trust the QTSP's certificates
3. Revoke the QTSP's TSL entry if the QTSP loses qualification

---

## Standards Behind This Model

The conceptual model comes from multiple layered documents:

### Legal foundation — eIDAS Regulation (EU) No 910/2014

| Article | What it mandates |
|---|---|
| Art. 17 | Member States must designate a supervisory body → PTS in Sweden |
| Art. 20 | QTSPs must be audited and supervised before being listed in TSL |
| Art. 22 | Member States must maintain a national TSL of qualified TSPs |

### TSL technical format — ETSI TS 119 612

Defines the full conceptual model implemented in `tsl_generator/`:
- TSL structure (`TrustServiceProvider`, `TSPService`, `ServiceCertificate`)
- How national TSLs chain to the EC LOTL
- TSL signing requirements
- TSL publication and update obligations

### TSP policy requirements — ETSI EN 319 401

Defines what a TSP must do to be qualified and listed — the operational
requirements PTS audits against before listing a QTSP in the TSL.

### WRP certificate profiles — ETSI TS 119 475

Defines specifically:
- WRPAC and WRPRC certificate profiles
- That the issuing TSP must be listed in the TSL
- The `id-kp-WRPAccess` extended key usage

### Full standards stack mapped to ms-registry

| Standard | What it governs in ms-registry |
|---|---|
| eIDAS Art. 17 | `SupervisoryAuthority` model — PTS as supervisory body |
| eIDAS Art. 22 | `tsl_generator/` — TSL publication obligation |
| ETSI TS 119 612 | `TrustServiceProvider`, `TSPCertificate`, `ServiceCertificate` models |
| ETSI EN 319 401 | Pre-condition: QTSP must be listed before UC2/UC3 can run |
| ETSI TS 119 475 | WRPAC/WRPRC certificate content (UC2, UC3) |
| ETSI TS 119 412-6 | PID Provider cert QCStatement (UC4) |
| EN 319 412-5 | QEAA Provider qualified seal (UC5) |

### Conceptual model in one picture

```
eIDAS Regulation (legal mandate)
└── Member State designates supervisory body (PTS)  [Art. 17]
    └── PTS maintains national TSL  [Art. 22]
        └── TSL format: ETSI TS 119 612
            └── Lists QTSPs: ETSI EN 319 401 (policy)
                └── QTSPs issue certificates per profiles:
                    ├── WRPAC/WRPRC:       ETSI TS 119 475
                    ├── PID Provider cert: ETSI TS 119 412-6
                    ├── Qualified seal:    EN 319 412-5
                    └── Website auth:      EN 319 412-3
```

---

## References

- **eIDAS Regulation (EU) No 910/2014** — Legal framework, Art. 17, 20, 22
- **ETSI TS 119 612** — TSL format and publication requirements
- **ETSI EN 319 401** — General policy requirements for Trust Service Providers
- **ETSI TS 119 475** — WRP certificate profiles (WRPAC, WRPRC)
- **ETSI TS 119 412-6** — QCStatements (id-etsi-qct-pid, id-etsi-qct-wal)
- **EN 319 412-5** — Qualified certificate profile (QcType OIDs)
- **Commission Implementing Decision (EU) 2015/1505** — TSL technical specifications
- **EC LOTL** — List of Trusted Lists published by European Commission
- **PTS** — Post- och telestyrelsen, Swedish TSL Scheme Operator
- `tsl_generator/` — ms-registry TSL XML generation (unsigned output)
- `CA_role_certificates_20260310.md` — CA role and certificate types breakdown
