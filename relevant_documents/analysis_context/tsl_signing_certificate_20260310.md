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
```
In OpenID Federation terms specifically, if ms-registry signs JSON responses about entities, it starts to look like an Intermediate that issues Subordinate Entity Statements — signed JWTs asserting facts about registered entities. That is exactly what OpenID Federation intermediates do.
```


## Level 1 — EU Trust Anchor: LOTL

| Property | Value |
|---|---|
| Published by | European Commission |
| Contains | All Member State TSL locations + TSL signing certs |
| Signing cert listed in | EU Official Journal |
| Standard | ETSI TS 119 612 |

The LOTL is the root of trust for the entire European trust infrastructure.
A Relying Party trusts a national TSL because the EC's LOTL says that TSL is legitimate.

**Precision: the LOTL is not the trust anchor — the LOTL signing certificate is.**

The trust anchor is the EC's LOTL signing certificate — a public key trusted implicitly via
out-of-band publication in the EU Official Journal. The LOTL itself is the first *signed
artifact* in the chain, but it is signed *by* the trust anchor, not identical to it.

```
EU Official Journal
└── publishes: EC LOTL signing cert  ← trust anchor (trusted out-of-band)
      └── EC uses this key to sign the LOTL document
            └── LOTL lists: national TSL locations + national TSL signing certs
```

A Wallet or RP bootstraps trust by obtaining the EC LOTL signing cert from the Official
Journal (or a trusted distribution). Everything else is verified cryptographically from there.

**Concrete example — OJ C 233/01 (2016):**

The actual trust anchor publication is at:
https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=uriserv:OJ.C_.2016.233.01.0001.01.ENG

The LOTL is available at:
`https://ec.europa.eu/information_society/policy/esignature/trusted-list/tl-mp.xml`

It lists **4 trust anchor certificates** (not one), identified by their digest values:

| Cert | SHA-256 (Base64) | Issued to |
|---|---|---|
| 1 | `WcgNzHQpzP2MKxWQ/ohftPbHf3ycu0uCpiyxwn/04kY=` | EC_CNECT (DG CONNECT) — issued by QuoVadis EU CA G2 |
| 2 | `8bzdEXsVVBc4E6Qhg8VNuX46fhCdCvqY9LzTJnVKA1E=` | EC_DIGIT (DG DIGIT) — issued by QuoVadis EU CA G2 |
| 3 | `/+p/DtKb6wdz6jsMRym7+ACmw5C2IZXLJw8SpKpi8oQ=` | Pierre Damas (EC official) — Belgian eID |
| 4 | `97wNFk3sjzZwmr6F/FcCLzsWhHAKgEw2jTQykASQ38s=` | Maarten Ottoy (EC official) — Belgian eID |

Key observations:
- Certs 1 & 2 are **organisational** electronic seal certs for EC departments
- Certs 3 & 4 are **personal** signing certs of named EC officials via Belgian eID
- All 4 are issued by external CAs (QuoVadis, Belgian eID CA) but trusted **not** because
  of those CA chains — trusted because their **fingerprints appear in the Official Journal**
- QuoVadis could revoke cert 1 and it would remain a valid trust anchor until the OJ notice is superseded
- Multiple certs allow signing by different EC signatories and enable rotation without service interruption

**Rotation mechanism:**
When a cert needs to change, the EC publishes a new OJ notice with new digest values,
includes the new cert in the LOTL's "secure pointer", and provides a **15-day transition period**
for relying parties to update. The old and new certs are both valid during this window.

**The EC LOTL signing cert issuer is not a federation subordinate.**

In OpenID Federation, a subordinate is vouched for by a superior. The EC, as the LOTL
signing cert issuer, sits at the top of both hierarchies — there is no entity above it to
issue a Subordinate Entity Statement about it. The two models are politically equivalent
and run in parallel, neither subordinate to the other:

```
X.509 / TSL                           OpenID Federation
────────────────────────────          ──────────────────────────────
EC LOTL signing cert                  EU Federation Trust Anchor
  (trusted via Official Journal)        (trusted via out-of-band bootstrap)
        │                                         │
        ▼                                         ▼
  PTS (national TSL signing cert)      National Federation Trust Anchor
        │                                         │
        ▼                                         ▼
  QTSPs / ServiceCerts                 Intermediates / issuers
```

Convergence is political (same governmental authority), not technical.

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
| Used for | PID signature verification / RP authentication | RP/Issuer metadata trust |
| Convergence | Same political authority (Member State + EC) | Same political authority |

### WRPAC and WRPRC — Two Distinct RP Credentials

Relying Parties (verifiers) hold two separate credentials serving different purposes:

| | WRPAC | WRPRC |
|---|---|---|
| Full name | Wallet Relying Party Access Certificate | Wallet Relying Party Registration Certificate |
| Format | X.509 | JWT or CWT (signed with AdES B-B) |
| Purpose | **Authentication** — proves RP identity when connecting to Wallet | **Policy/transparency** — describes RP's entitlements and data access scope |
| Shown to | Wallet (TLS/connection layer) | Wallet user (consent screen) |
| Private key | Under RP's control | N/A — issued by WRPRC provider, no RP key |
| Multiple per RP? | Yes — one per instance/deployment | One per RP (or per intermediary used) |
| Issued by | TSP (electronic seal/signature cert issuer) authorized by MS | Provider of WRP registration certs (may be ms-registry) |
| Content source | National register data | National register data |
| Standard | ETSI TS 119 475 §4.3 / §5.1 | ETSI TS 119 475 §4.4 / §5.2 |

If no WRPRC is issued, the Wallet retrieves the same information directly from the national
register (ms-registry). The WRPRC is a signed, portable version of that same register data.

### Trust Anchor for WRPAC Verification

The EC LOTL is the trust anchor for all three verification paths. The Wallet verifies a
WRPAC by following the same TSL chain it uses for PID verification:

```
EC LOTL  ← trust anchor (Wallet bootstraps from this)
  └── Swedish TSL (signed by PTS)
        └── WRPAC issuer TSP (listed in TSL)
              └── WRPAC (X.509) issued to RP
                    └── RP authenticates to Wallet with private key
```

The EC LOTL is the single root of trust for all three verification paths:

| What is verified | By whom | Chain ends at |
|---|---|---|
| WRPAC (RP authentication) | Wallet | EC LOTL → TSL → WRPAC issuer TSP → WRPAC |
| WRPRC (RP entitlements) | Wallet | EC LOTL → TSL → WRPRC issuer TSP → WRPRC JWT (x5c) |
| PID signature | Relying Party | EC LOTL → TSL → PID Provider ServiceCert |

### Trust Path Split by Role

Verifiers are **not** OpenID Federation participants. Both WRPAC and WRPRC are anchored
in the TSL/LOTL chain, not in the OpenID Federation. The federation path applies only to
issuers (PID Providers, QEAA Providers).

| Entity | Trust path | Credentials |
|---|---|---|
| PID Provider, QEAA Provider | OpenID Federation + TSL | Entity Statements (federation) + ServiceCertificate (TSL) |
| Relying Party (verifier) | TSL only | WRPAC (X.509) + WRPRC (JWT/CWT) — both anchored in TSL |

### Implication for ms-registry

ms-registry is the **national register** — the authoritative source for WRPRC content.
It can act as the WRPRC issuer directly (signing JWT responses about registered RPs), or
another authorized TSP can issue WRPRCs based on ms-registry data.

If ms-registry issues WRPRCs (signs JWT responses):
- It operates on the **verifier/TSL path**, not the federation path
- Its signing cert must be listed in the national TSL as a WRPRC provider TSP
- The chain for a WRPRC signed by ms-registry:

```
EC LOTL
  └── Swedish TSL (signed by PTS)
        └── ms-registry listed as WRPRC provider TSP
              └── ms-registry signs WRPRC (JWT, x5c contains ms-registry cert)
                    └── Wallet verifies WRPRC → shows RP entitlements to user
```

If ms-registry also signs JSON for the **federation/issuer path** (Entity Statements about
PID Providers, QEAA Providers), that is a separate signing key and a separate trust chain:

```
EU / National Federation Trust Anchor
  └── Subordinate ES about ms-registry (as federation Intermediate)
        └── ms-registry signs Entity Statements about issuers
              └── PID Provider, QEAA Provider
```

These are two distinct roles, two distinct signing keys, two distinct trust chains — both
ultimately representing the same governmental authority through different technical mechanisms.

**Open question — who operates the national Federation Trust Anchor?**

The parallel with X.509 would suggest PTS (it signs the TSL, so it would naturally also
operate or delegate the national federation Trust Anchor). That would produce:

```
EU Federation Trust Anchor (EC-level)
  └── PTS as National Federation Trust Anchor
        └── ms-registry as Intermediate
              └── Issuers (PID Providers, QEAA Providers)
```

This is architecturally consistent with the X.509/TSL hierarchy but is **not yet settled**
in the EUDI ARF. Who operates the national Federation Trust Anchor is a Member State
implementation decision and may or may not be the same body as the TSL Scheme Operator (PTS).

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

## Who Issues the PID Provider Certificate

### Role of the PID Provider

A PID Provider **issues** credentials (Personal Identification Data) to citizens. It does **not** request
credentials from Wallets. It is on the issuer side, not the relying party side.

| | Relying Party (RP) | PID Provider |
|---|---|---|
| Role | Requests credentials from Wallet | Issues credentials to Wallet |
| Gets WRPAC? | Yes | No |
| Gets WRPRC? | Yes | No |
| Certificate purpose | Authenticate presentation requests | Sign PIDs issued to citizens |
| Appears in TSL? | No | Yes — as `TrustServiceProvider` under `IdV` service type |
| Registered in ms-registry? | Yes — `RegisteredEntity` (role=`RELYING_PARTY`) | Yes — `RegisteredEntity` (role=`PID_PROVIDER`) |

### What Certificate Does a PID Provider Hold?

An end-entity electronic seal certificate containing the `id-etsi-qct-pid` QCStatement OID
(`0.4.0.194126.1.1`), per ETSI TS 119 412-6. This certificate is used to sign PIDs issued to citizens.

### Who Issues It — The Open Question

**ETSI TS 119 412-6** defines the `id-etsi-qct-pid` OID and requires it in the certificate.
It says **nothing** about who issues the certificate.

**ETSI TS 119 475** defines WRPAC/WRPRC profiles. It does **not** define a PID Issuer CA profile at all.

There is no dedicated PID Issuer CA profile in any ETSI standard.

### Two Practical Options

| Option | Issuer | Basis |
|---|---|---|
| **A — National QTSP** | e.g. Telia CA, Nexus | Issues qualified seal cert, injects `id-etsi-qct-pid` OID — X.509 path, nothing forbids this |
| **B — Federation Trust Anchor** | National or EU federation operator | Issues Entity Statement (JWT) carrying `id-etsi-qct-pid` — EUDI ARF preferred model |

Option B is preferred by the EUDI ARF because the Federation Trust Anchor already knows
which entities are authorised PID Providers (it controls federation onboarding). Adding a
separate CA would be redundant. This is also the conclusion from IT-Wallet Issue #1055:
https://github.com/italia/eid-wallet-it-docs/issues/1055

### Accuracy Caveat

| Claim | Accuracy |
|---|---|
| `id-etsi-qct-pid` OID is required | Correct — ETSI TS 119 412-6 |
| Federation Trust Anchor issues it | **Interpretation** — from Issue #1055 / EUDI ARF, not universal law |
| No separate PID Issuer CA profile exists | Correct — no ETSI profile defines one |

A Member State **could** still issue an X.509 certificate with the `id-etsi-qct-pid` OID via a
national QTSP — nothing in the standards forbids it. The federation path is the EUDI ARF preferred
model but not the only compliant approach.

### Recommendation for ms-registry UC4

Support both paths:
- Federation Trust Anchor API client (ARF preferred)
- National QTSP / CA fallback (X.509 with `id-etsi-qct-pid` OID)

---

## Can WRPAC/WRPRC Be Issued by the Federation Trust Anchor?

**No.** WRPAC and WRPRC are X.509 certificates only. The Federation Trust Anchor path does not apply to them.

| | WRPAC / WRPRC | PID Provider cert |
|---|---|---|
| Format | X.509 v3 (RFC 5280) | X.509 or Entity Statement (JWT) |
| Issuer | National QTSP (TSL-listed) | QTSP or Federation Trust Anchor |
| Standard | ETSI TS 119 475 | ETSI TS 119 412-6 |
| Federation TA can issue? | **No** | Yes (ARF preferred) |

ETSI TS 119 475 explicitly defines WRPAC and WRPRC as X.509 certificate profiles. The standard mandates:
- The issuer must be a TSP **listed in the national TSL**
- The certificate must follow the X.509 v3 profile (Subject DN, Key Usage, EKU extensions)

A Federation Trust Anchor issues **Entity Statements** (JWTs) — a completely different format and
trust model. There is no WRPAC/WRPRC profile defined for JWT/OpenID Federation.

The Federation Trust Anchor enters the picture only for **issuers** (PID Providers, QEAA Providers)
— entities that issue credentials to citizens. RPs (which consume credentials) use the X.509/TSL
path exclusively.

---

## How the PID Signing Certificate Ties Together

The certificate issued to the PID Provider (by QTSP or Federation TA) is **the same certificate**
that signs credentials issued to citizens, AND the same certificate published in the TSL.

```
QTSP (or Federation TA)
└── issues signing cert to PID Provider (with id-etsi-qct-pid OID)
    └── PID Provider uses this cert to sign PIDs → citizens
        └── Citizen Wallet presents PID to Relying Party
            └── RP verifies PID signature against cert
                └── RP finds that cert in Swedish TSL
                    └── RP trusts TSL because PTS signed it
                        └── RP trusts PTS cert because EC LOTL lists it
```

The TSL is the **public registry of legitimate signing certs** — it tells a Relying Party which
certificates are authorised to sign PIDs, without needing to know each issuer in advance.

| Step | What happens |
|---|---|
| QTSP/Federation TA issues cert | PID Provider gets signing cert with `id-etsi-qct-pid` |
| ms-registry publishes TSL | PID Provider's cert appears as `ServiceCertificate` under `IdV` service type |
| PID Provider signs PID | Uses that same private key to sign the SD-JWT/mdoc |
| Wallet delivers PID to RP | PID header contains `x5c` with the signing cert |
| RP verifies | Finds cert in TSL → chain verified → signature verified → trusts PID claims |

---

## Why Can the Federation Trust Anchor Issue for PID Providers but Not for RPs?

Because the PID Provider is a **credential issuer**, not a relying party — and the trust model for
issuers in the EUDI framework runs through the OpenID Federation, not the X.509/TSL path.

The Federation Trust Anchor already controls who is an authorised PID Provider — it approves them
during federation onboarding and issues Entity Statements carrying the PID Provider's public key,
metadata, and `id-etsi-qct-pid` assertion. There is no need for a separate CA to issue an X.509
certificate saying the same thing — the Federation TA's signature *is* the authorisation.

| | RP (gets WRPAC/WRPRC) | PID Provider (gets pid cert) |
|---|---|---|
| What needs to be proven | "This RP is registered and approved to request credentials" | "This entity is authorised to issue PIDs" |
| Who controls that approval | Member State registry → QTSP | Federation Trust Anchor |
| Trust mechanism | X.509 chain → national TSL → PTS → LOTL | OpenID Federation chain → Trust Anchor |
| Format mandated by standard | X.509 v3 — ETSI TS 119 475 is explicit | No format mandated — standard only defines the OID content |

The key difference: **ETSI TS 119 475 explicitly defines an X.509 profile** for WRPAC/WRPRC.
**ETSI TS 119 412-6 only defines the QCStatement OID content** — it says nothing about format or
issuer. That gap is what allows the Federation TA path to work for PID Providers.

---

## Can the PID Provider Signing Cert Be Added to the TSL?

Yes — and it **must** be, for Relying Parties to trust it.

The PID Provider's signing cert (qualified seal with `id-etsi-qct-pid`) is published in the TSL
as a `ServiceCertificate` under the `IdV` service type. That is how an RP knows the cert is legitimate.

There is a subtlety depending on which path was used to issue it:

### Path A — National QTSP issues X.509 cert

Straightforward — the cert is a standard X.509 certificate. It goes directly into the TSL as a
`ServiceCertificate`. RP extracts it from the PID's `x5c` header, finds it in the TSL, done.

### Path B — Federation Trust Anchor issues Entity Statement (JWT)

More complex. The Entity Statement is a JWT — not an X.509 cert. But the TSL expects X.509
(`ServiceCertificate` is a DER-encoded certificate element per ETSI TS 119 612).

Two ways this is handled:

| Option | What happens |
|---|---|
| **Entity Statement contains an X.509 cert** | Federation TA embeds an X.509 cert in the Entity Statement's `jwks` — that X.509 cert is what gets published in the TSL |
| **Dual publication** | PID Provider holds both an X.509 cert (for TSL/x5c) and is registered in the federation (for OpenID Federation trust chain) — both exist in parallel |

In practice the EUDI ARF assumes **both trust paths run in parallel** — the TSL (X.509) path for
credential signature verification, and the OpenID Federation path for metadata/endpoint trust.
They are not mutually exclusive. Regardless of who issued the cert, the X.509 representation of
the PID Provider's signing key ends up in the TSL.

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
- **IT-Wallet Issue #1055** — QCStatement profiles for PID/QEAA/PSB: https://github.com/italia/eid-wallet-it-docs/issues/1055
- `tsl_generator/` — ms-registry TSL XML generation (unsigned output)
- `CA_role_certificates_20260310.md` — CA role and certificate types breakdown


PID provider 4.5 

https://www.etsi.org/deliver/etsi_ts/119400_119499/11941206/01.01.01_60/ts_11941206v010101p.pdf


https://www.etsi.org/deliver/etsi_en/319400_319499/31941205/02.05.01_60/en_31941205v020501p.pdf
QCS-4.3.5-02: [CONDITIONAL] If this qcStatement is included in the certificate, it shall contain the OID value
corresponding to the identification used for identity verification of the certificate

id-etsi-qct-pid: OID 0.4.0.194126.1.1 OID arc

---

## What Does the Federation Trust Anchor Actually Issue?

The Federation Trust Anchor issues **Entity Statements** (JWTs) — not X.509 certificates.

An Entity Statement for a PID Provider contains:

```json
{
  "iss": "https://trust-anchor.example.eu",
  "sub": "https://pid-provider.skatteverket.se",
  "jwks": {
    "keys": [
      {
        "kty": "EC",
        "crv": "P-256",
        "x": "...",
        "y": "...",
        "kid": "pid-signing-key-2026"
      }
    ]
  },
  "metadata": {
    "openid_credential_issuer": {
      "credential_issuer": "https://pid-provider.skatteverket.se",
      "credential_configurations_supported": {}
    }
  },
  "trust_marks": [
    {
      "id": "http://uri.etsi.org/TrstSvc/Svctype/PID_Issuer",
      "trust_mark": "<signed JWT asserting PID Provider status>"
    }
  ]
}
```

| What it contains | Purpose |
|---|---|
| PID Provider's **public key** (`jwks`) | Used to verify PIDs the provider signs |
| **Endpoints** (issuer URL, credential endpoint) | Wallet knows where to request PID from |
| **Trust marks** | Asserts the entity is an approved PID Provider |
| Implicitly carries `id-etsi-qct-pid` assertion | Via trust mark or metadata claim |

The Entity Statement itself is the credential of trust — a JWT signed by the Trust Anchor's
private key. It does **not** issue an X.509 certificate.

### The Gap with the TSL

The Entity Statement covers the **OpenID Federation trust path** — Wallet discovering and trusting
the PID Provider's endpoint and key. But the TSL requires an **X.509 cert** (`ServiceCertificate`
is DER-encoded per ETSI TS 119 612).

This is why two parallel credentials exist for the same PID Provider entity:

| Credential | Issued by | Used for |
|---|---|---|
| Entity Statement (JWT) | Federation Trust Anchor | OpenID Federation trust path — Wallet discovers PID Provider endpoint and key |
| X.509 qualified seal cert | QTSP (or embedded in Entity Statement `jwks`) | TSL publication — RP verifies PID signature via TSL chain |

Both are required. They are not alternatives — they serve different trust paths that run in parallel
in the EUDI framework.



## definition of the wallet relying parties
https://eur-lex.europa.eu/eli/reg_impl/2025/848/oj


12.

The entitlement or entitlments of the wallet-relying party, that shall be expressed as follows:

(a)

‘Service_Provider’ to express the entitlement of the wallet-relying party as a provider of services;

(b)

‘QEAA_Provider’ to express the entitlement of the wallet-relying party as a qualified trust service provider issuing qualified electronic attestations of attributes;

(c)

‘Non_Q_EAA_Provider’ to express the entitlement of the wallet-relying party as a trust service provider issuing non-qualified electronic attestations of attributes;

(d)

‘PUB_EAA_Provider’ to express the entitlement of the wallet-relying party as a provider of electronic attestations of attributes issued by or on behalf of a public sector body responsible for an authentic source;

(e)

‘PID_Provider’ to express the entitlement of the wallet-relying party as a provider of person identification data;

(f)

‘QCert_for_ESeal_Provider’ to express the entitlement of the wallet-relying party as a qualified trust service provider issuing qualified certificates for electronic seals;

(g)

‘QCert_for_ESig_Provider’ to express the entitlement of the wallet-relying party as a qualified trust service provider issuing qualified certificates for electronic signatures;

(h)

‘rQSigCDs_Provider’ to express the entitlement of the wallet-relying party as a qualified trust service provider providing qualified trust services for the management of a remote qualified electronic signature creation device;

(i)

‘rQSealCDs_Provider’ to express the entitlement of the wallet-relying party as a qualified trust service provider providing qualified trust services for the management of a remote qualified electronic seal creation device;

(j)

‘ESig_ESeal_Creation_Provider’ to express the entitlement of the wallet-relying party as a non-qualified trust service provider providing a non-qualified trust service for remote creation of electronic signatures or electronic seals.

---

## Intended Use — Examples

**Intended Use** is the declared purpose for which an RP requests specific wallet data.
Each intended use is a separate registration record with its own identifier, purpose
statement (shown to the wallet user), data request scope, and privacy policy URL.

An RP can have multiple intended uses — each enforcing GDPR data minimisation independently.
The WRPRC presented to the wallet user is bound to a specific intended use identifier.

### Key fields per Intended Use

| Field | Description |
|---|---|
| `intendedUseIdentifier` | Unique identifier (e.g. `BANK-AB-IU-001`) |
| `purpose` | Human-readable description shown to wallet user |
| Credentials requested | Specific credential types and claims |
| Privacy policy URL | Purpose-specific policy |
| `validity_start` / `validity_end` | Independent validity per use |

### Examples

**Bank — multiple uses under one registration:**

```
Bank AB (RegisteredEntity, entitlement: Service_Provider)
├── IntendedUse: "Account Opening" (KYC)
│   └── Requests: PID → family_name, given_name, date_of_birth, address
│
├── IntendedUse: "Loan Application"
│   └── Requests: PID → name, DOB + Income Attestation → annual_income, employer
│
└── IntendedUse: "ATM Age Check"
    └── Requests: PID → age_over_18 only
```

**Hospital (public sector body):**

```
Regional Hospital (RegisteredEntity, isPSB: true, entitlement: Service_Provider)
├── IntendedUse: "Patient Registration"
│   └── Requests: PID (full) + Health Insurance Card
│
├── IntendedUse: "Emergency Treatment"
│   └── Requests: PID → name, DOB + Medical Allergies Attestation
│
└── IntendedUse: "Prescription Collection"
    └── Requests: PID → family_name, given_name, personal_id_number
```

**University (dual role — issuer + verifier):**

```
Stockholm University (entitlements: Service_Provider + PUB_EAA_Provider)
├── providesAttestations: Diploma, Student ID, Enrollment Certificate
│
├── IntendedUse: "Student Enrollment" (as verifier)
│   └── Requests: PID (full) + Secondary School Diploma
│
└── IntendedUse: "Library Access" (as verifier)
    └── Requests: Student ID Attestation (from any university)
```

**Intermediary acting for multiple end-RPs:**

```
IDVerify AB (isIntermediary: true, entitlement: Service_Provider)
├── IntendedUse: "General Age Verification"
│   └── Requests: PID → age_over_18
│
└── IntendedUse: "Full KYC Service"
    └── Requests: PID (full identity)

End-RPs using this intermediary:
└── WebShop A, Gaming Site B, Fintech C
    └── Each gets a separate WRPRC identifying both the final RP and IDVerify AB
```

### GDPR principles enforced per Intended Use

| Principle | How enforced |
|---|---|
| Data minimisation (Art. 5.1c) | Each use requests only the minimum claims needed |
| Purpose limitation (Art. 5.1b) | Data collected under one use cannot be used for another |
| Transparency | Wallet displays the specific `purpose` before consent |
| Independent revocation | One intended use can be revoked without affecting others |

See `use-cases-relying-parties.md` for full implementation details.
