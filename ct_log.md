# CT Log — ms-registry Simplified Flow

The `certificates/ct_log.py` module implements a **simplified Certificate Transparency log** for the ms-registry simplified flow, as described in RFC 9162.

ms-registry acts as the CT log itself.  For each uploaded access certificate it produces an SCT-like record signed with the registry's own ECDSA P-256 key.  This is **not** a full RFC 9162 Merkle-tree log — it records a signed timestamp that proves ms-registry saw the certificate at a given moment.

---

## Log ID (RFC 9162 §4.4)

RFC 9162 identifies each CT log by an **OID** (Object Identifier) allocated from the [IANA CT Log Parameters registry](https://www.iana.org/assignments/ct-log-parameters).  This replaced the SHA-256(SPKI) approach used in RFC 6962.

The log ID is configured via the `CT_LOG_OID` environment variable.  If unset, the placeholder `1.3.6.1.4.1.99999.1` is used (development/simplified flow only — not IANA-allocated).

### Obtaining a real OID

1. Apply for a **Private Enterprise Number (PEN)** at:
   [https://www.iana.org/assignments/enterprise-numbers/](https://www.iana.org/assignments/enterprise-numbers/)
   (free, ~1 week turnaround)

2. Use your PEN to define a sub-arc for this log, e.g.:
   ```
   1.3.6.1.4.1.<PEN>.1   → ms-registry CT log instance 1
   ```

3. Set the OID in your environment:
   ```
   CT_LOG_OID=1.3.6.1.4.1.<PEN>.1
   ```

> Formal registration in the IANA CT Log Parameters registry is only required for **public internet CT logs** trusted by browsers.  For this internal simplified log, a PEN-based OID is sufficient.

---

## Wire Format

Stored as raw TLS bytes in `EntityAccessCertificate.ct_sct`.  The encoding is
a proper RFC 9162 §4.5 `TransItemList` containing a single `x509_sct_v2` `TransItem`.

```
TransItemList                     uint16 total_len + payload
└── TransItem
    ├── type      uint16 = 1      x509_sct_v2  (RFC 9162 §4.5)
    ├── data_len  uint16
    └── data      SignedCertificateTimestampDataV2  (RFC 9162 §4.8)
        ├── log_id      uint8 len + OID DER value bytes  (RFC 9162 §4.4)
        ├── timestamp   uint64  milliseconds since epoch
        ├── extensions  uint16 len = 0  (empty)
        └── signature
            ├── scheme  uint16 = 0x0403  ecdsa_secp256r1_sha256  (RFC 8446 §4.2.3)
            ├── length  uint16
            └── bytes   ECDSA-P256(signed_content)
```

### Signed content (simplified RFC 9162 §4.8 CertificateTimestamp)

```
sct_version  uint8  = 1
type         uint16 = 1  (x509_sct_v2)
timestamp    uint64  milliseconds since epoch
log_id       uint8 len + OID DER value bytes
cert_hash    uint16 len=32 + SHA-256(cert DER)   ← simplified: full cert, not TBSCertificate
extensions   uint16 len = 0
```

| Field | RFC 9162 ref | Value |
|-------|-------------|-------|
| `log_id` | §4.4 — OID from IANA registry | `CT_LOG_OID` env var (or placeholder) |
| `timestamp` | §4.8 — milliseconds since epoch | time of upload |
| `cert_hash` | §4.8 (simplified) | SHA-256 of full DER certificate |
| `signature` | §4.8 | ECDSA-P256 / ecdsa_secp256r1_sha256 |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CT_LOG_OID` | No | OID identifying this CT log (RFC 9162 §4.4). Defaults to `1.3.6.1.4.1.99999.1` (placeholder). |
| `REGISTRY_SIGNING_KEY_PEM` | Yes | ECDSA P-256 private key used to sign SCTs. |

---

## Normative References

- [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162) — Certificate Transparency Version 2.0
- [IANA Private Enterprise Numbers](https://www.iana.org/assignments/enterprise-numbers/) — PEN allocation
- [IANA CT Log Parameters](https://www.iana.org/assignments/ct-log-parameters) — CT log OID registry
