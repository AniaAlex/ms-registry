# CNF File & Certificate Issuing — Design Conclusions

## Minimal Viable Flow (without CA integration)

```
1. Entity registers
   → RegisteredEntity created (status: PENDING)

2. Registry generates a .cnf for the entity
   → pre-filled with their registered data:
        CN  = trade_name
        O   = legal_person.legal_name
        C   = physical_address.country_code
        SAN = registry_uri

3. Entity uses the .cnf locally:
   openssl genrsa -out entity.key 2048
   openssl req -new -config entity.cnf -key entity.key -out entity.csr
   openssl x509 -req -days 365 -in entity.csr -signkey entity.key -out entity.crt

4. Entity uploads entity.crt to the registry
   POST /registry/wrp/{id}/digital-identity/
   → stored in EntityDigitalIdentity (type=x509, is_current=True)

5. Registrar reviews → status: ACTIVE

6. GET /registry/lote-se/
   → entity appears in trustedEntities with digitalIdentities populated
```

The private key **never leaves the entity**.

---

## What is a CSR?

CSR = **Certificate Signing Request**.

A file the entity generates locally containing:
- Their **public key**
- Their **identity info** (CN, O, C, etc. — from the `.cnf`)
- A **signature** proving they hold the corresponding private key

The `.cnf` the registry generates ensures the entity puts the **correct identity fields**
in their CSR — matching what is registered (legal name, country, registry URI).

---

## With CA Integration (future)

The entity's step 3 becomes: submit CSR to registry → registry forwards to CA → gets back signed cert.
The registry is the intermediary (registrar-initiated model per ETSI TS 119 475 Annex D):

```
Entity                    MS Registry                National CA
  │                           │                          │
  │── POST /wrp/{id}/         │                          │
  │   certificate/request     │                          │
  │   (uploads CSR) ─────────►│                          │
  │                           │── validates CSR matches  │
  │                           │   registered entity data │
  │                           │── forwards CSR ─────────►│
  │                           │                          │── issues cert
  │                           │◄── signed cert ──────────│
  │                           │── stores in              │
  │                           │   EntityDigitalIdentity  │
  │◄── returns signed cert ───│                          │
```

Steps 1, 2, 4, 5, 6 stay identical. Only step 3 changes.

---

## Certificate Hierarchy

```
Self-signed cert (root/CA)        →  LOTE digitalIdentities
  └── Leaf signing certificate    →  TSL XML ServiceDigitalIdentity
        (issued by root)
```

- **Root cert**: establishes identity and trust. Long validity (3–5 years). Wallets look
  it up to verify "is this entity trusted?". Goes in **LOTE `digitalIdentities`**.
- **Leaf cert**: what the entity uses day-to-day to sign credentials/requests. Short
  validity (1 year), rotated regularly. Goes in **TSL XML `ServiceDigitalIdentity`**.
  Chains up to root → wallet verifies chain → entity is trusted.

**For the minimal scenario**: one self-signed cert, no leaf hierarchy. That single cert
goes in both LOTE and TSL XML. Leaf separation becomes important when rotation is needed
without changing what is published in the LOTE.

---

## Digital Identity Model (target)

Both `EntityAccessCertificate` and `ServiceCertificate` serve the same digital identity
purpose — they answer: "How do I cryptographically identify and verify this entity?"

The split is an implementation artifact (two apps built independently). The correct model is:

```
EntityDigitalIdentity
  ├── registered_entity → RegisteredEntity
  ├── type: x509 | jwk | did
  ├── certificate_pem  (if x509)
  ├── jwk              (if jwk, JSON)
  ├── did              (if did, string)
  └── is_current
```

- **LOTE view** reads `EntityDigitalIdentity` → builds `digitalIdentities` array
- **TSL generator** reads `EntityDigitalIdentity` → renders `ServiceDigitalIdentity` in XML
- `ServiceCertificate` stays as a TSL XML rendering detail, not source of truth

---

## Entity Type → Digital Identity Type

| Entity type     | Certificate type                      | Signs                        | Verified by  |
|-----------------|---------------------------------------|------------------------------|--------------|
| Relying party   | WRPAC (x509)                          | Presentation requests        | Wallet unit  |
| PID provider    | Signing cert id-etsi-qct-pid (x509)   | PIDs / credentials           | Wallet unit  |
| QEAA provider   | Qualified seal id-etsi-qct-eseal (x509)| Attestations                | Wallet unit  |
| Verifier        | DID / JWK / x509                      | Presentation requests        | Wallet unit  |

All entity types: same operational pattern — private key to sign, public certificate/JWK/DID
published in LOTE `digitalIdentities` so wallets can verify.
