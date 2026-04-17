# PID Provider — Full Summary and Open Questions
_Date: 2026-04-17_

---

## PID Provider — Full Summary

### What it is
A body responsible for issuing **Person Identification Data** (national identity) to EUDI Wallet Units. Approved by Member State policy.

---

### 1. Registration (with Member State Registrar)
- Submits **identification data + entitlements** (attestation types) to the Registrar
- Registrar approves and publishes entry to the **Registry**
- Registrar requests an **Access Certificate** from the Access CA on behalf of the PID Provider
- Optionally receives a **Registration Certificate**
- **Gap in docs**: where the PID Provider submits its signing certificate (trust anchor) during this process is not explicitly documented

---

### 2. Two certificates — completely different purposes

| | Access Certificate (WRPAC) | Signing Certificate |
|---|---|---|
| **Purpose** | Authenticate to Wallet Unit during session | Sign issued PIDs |
| **Issued by** | External Access CA (notified to EC) | Self-signed OR external CA (per ETSI TS 119 412-6, PID-4.2-01) |
| **Self-signed?** | **No** — must chain to Access CA TL | **Yes** — explicitly allowed |
| **Goes into TL?** | No | Yes — as trust anchor |
| **Standard** | ETSI TS 119 411-8 | ETSI TS 119 412-6 |

---

### 3. Trusted List (PID Provider TL)
- Compiled and published by the **European Commission** (not MS TLP)
- MS notifies EC with (per **PPNot_02**):
  - Identification data
  - **PID Provider trust anchors** (the signing certificate / public key)
  - Access CA trust anchors
  - Service supply points (URLs)
- Each TL entry contains:
  - Provider identity (name, country, registration number)
  - Service type: `http://uri.etsi.org/19602/SvcType/PID/Issuance`
  - `serviceDigitalIdentity` — the X.509 signing certificate (trust anchor)
  - Service supply points
  - Optional extensions: `allowedAttestationType`, `registrationCertificateRef`
- **No** `ServiceStatus` or `StatusStartingTime` (unlike other provider types)
- Signed with **Compact JAdES Baseline B**

---

### 4. If signing certificate is self-signed
- The self-signed cert **is itself the trust anchor**
- EC publishes it directly in the TL `serviceDigitalIdentity`
- Validators match the PID's signing cert directly against the TL — no chain verification needed
- Trust comes from **EC publication**, not from a CA chain

---

### 5. Validation flow (Wallet Unit receiving a PID)
```
PID Provider presents Access Cert → Wallet Unit verifies chain to Access CA TL
PID Provider issues signed PID   → Wallet Unit verifies:
    1. Signing cert matches trust anchor in PID Provider TL
    2. PID Provider is registered in MS Registry (ISSU_24a)
```

---

### 6. Key standards
- **ETSI TS 119 411-8** — Access Certificate issuance
- **ETSI TS 119 412-6** — Signing certificate profile (self-signed explicitly allowed per PID-4.2-01)
- **ETSI TS 119 602** — PID Provider Trusted List format (Annex D)
- **ARF Topic 27** — Registration requirements
- **ARF Topic 31** — Notification and TL publication

---

## Open Questions / Documentation Gaps

### 1. Where does the PID Provider submit its signing certificate?
The registration sequence diagram (Section 5.2 of `task2-trust-framework/trust-infrastructure-schema.md`) shows PID Providers submitting only `(Identification data, Entitlements)` to the Registrar — **no trust anchors**. Yet PPNot_02 requires the MS to notify the EC with PID Provider trust anchors.

**Question**: Does the PID Provider submit its signing certificate to the Registrar at registration? Or is it submitted directly to a separate MS notification process? The diagram should explicitly show this, as EAA/QEAA Providers explicitly show trust anchors at step 1.

---

### 2. Who within the Member State does the EC notification?
The docs say "the Member State notifies the EC" (per GenNot_01) but don't specify **which MS body** performs the notification for PID Providers — is it the Registrar, a separate government authority, or another body?

---

### 3. Registrar → EC notification path for PID Providers
For EAA/QEAA Providers there is a clear path: `Registrar → TLP → EC`. For PID Providers the TLP is bypassed and the EC compiles the TL directly — but **the path from Registrar/Registry to EC notification is not shown** in any sequence diagram.

---

### Summary of gaps

| Gap | Location to fix |
|---|---|
| PID Provider trust anchor submission not shown in registration flow | `task2-trust-framework/trust-infrastructure-schema.md` Section 5.2 |
| Which MS body notifies EC for PID Providers | `task2-trust-framework/trust-infrastructure-schema.md` Section 3.1.1 |
| Missing sequence diagram for PID Provider registration → EC notification | `task2-trust-framework/trust-infrastructure-schema.md` — needs a dedicated diagram like Section 5.3 |
