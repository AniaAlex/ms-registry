# Entitlements in EUDI Wallet Ecosystem

## Overview

**Entitlements** define what a registered entity is **authorized to do** in the EUDI Wallet ecosystem. An entity can have **multiple entitlements** (`[1..*]` = one or more required).

All entities register as `WalletRelyingParty` regardless of whether they are verifiers or issuers. The **entitlement** determines their role.

---

## Entitlement URIs (from TS5)

| Entitlement URI | Role | Description |
|-----------------|------|-------------|
| `https://uri.etsi.org/19475/Entitlement/Service_Provider` | **Verifier** | Requests/verifies attributes from Wallet Users |
| `https://uri.etsi.org/19475/Entitlement/PID_Provider` | **Issuer** | Issues Person Identification Data |
| `https://uri.etsi.org/19475/Entitlement/QEAA_Provider` | **Issuer** | Issues Qualified Electronic Attestations of Attributes |
| `https://uri.etsi.org/19475/Entitlement/PUB_EAA_Provider` | **Issuer** | Issues Public Sector EAA (government bodies) |
| `https://uri.etsi.org/19475/Entitlement/Non_Q_EAA_Provider` | **Issuer** | Issues Non-Qualified EAA |
| `https://uri.etsi.org/19475/Entitlement/QCert_for_ESig_Provider` | **Issuer** | Issues Qualified Certificates for Electronic Signatures |
| `https://uri.etsi.org/19475/Entitlement/QCert_for_ESeal_Provider` | **Issuer** | Issues Qualified Certificates for Electronic Seals |
| `https://uri.etsi.org/19475/Entitlement/rQSigCDs_Provider` | **Provider** | Provides remote Qualified Signature Creation Devices |
| `https://uri.etsi.org/19475/Entitlement/rQSealCDs_Provider` | **Provider** | Provides remote Qualified Seal Creation Devices |
| `https://uri.etsi.org/19475/Entitlement/ESig_ESeal_Creation_Provider` | **Provider** | Provides Electronic Signature/Seal creation services |

---

## Key Rule: Dual Registration for Issuers

From TS5:

> *"An attestation provider that requires presentation of another attestation during issuance of their own attestation SHALL register both as a Service_Provider and with their attestation provider entitlement in a single registration."*

### Why Dual Registration?

When an **issuer** needs to **verify** something before issuing, they act as **both**:
1. **Verifier** (`Service_Provider`) - to request PID/attestations from the user
2. **Issuer** (e.g., `QEAA_Provider`) - to issue new attestations to the user

### Example: University Issuing Diplomas

```
Stockholm University
├── Entitlements:
│   ├── Service_Provider      ← To verify student's PID before issuance
│   └── PUB_EAA_Provider      ← To issue diploma attestations
│
├── IntendedUse (as verifier):
│   └── "Verify student identity before diploma issuance"
│       └── Requests: PID (name, DOB, personal_id)
│
└── providesAttestations (as issuer):
    └── Diploma Attestation
```

---

## PID Provider as WalletRelyingParty

**Yes, PID Providers register as `WalletRelyingParty`** with the `PID_Provider` entitlement.

The term "Wallet-Relying Party" means **anyone who relies on EUDI Wallets**, including:
- Verifiers who request attributes
- Issuers who deliver attestations to wallets

### Where is this mentioned in TS5?

1. **In the entitlement list** (Section 2.1):
   ```
   https://uri.etsi.org/19475/Entitlement/PID_Provider
   ```

2. **In the `providesAttestations` attribute** (Section 2.1):
   > "Shall be present only if any entitlement of the Wallet-Relying Party is of type QEAA_Provider, Non_Q_EAA_Provider, PUB_EAA_Provider or **PID_Provider**, listing the attestation type(s) the Wallet-Relying Party intends to issue to Wallet Units."

---

## Practical Examples

### Pure Verifier
```
Online Shop AB
└── Entitlements: [Service_Provider]
    └── Only verifies age/identity, never issues anything
```

### Pure Issuer (no verification needed)
```
Swedish Tax Agency (Skatteverket)
└── Entitlements: [PID_Provider]
    └── Issues PID, verifies identity through other means (in-person, BankID)
```

### Dual Role (verify then issue)
```
Bank AB
├── Entitlements: 
│   ├── Service_Provider      ← Verifies PID during account opening
│   └── QEAA_Provider         ← Issues income/employment attestations
│
├── IntendedUse: "KYC for account opening"
│   └── Requests: PID
│
└── providesAttestations:
    └── Income Attestation
```

### Qualified Trust Service Provider
```
Signing Service AB
├── Entitlements:
│   ├── Service_Provider           ← Verifies identity before issuing cert
│   ├── QCert_for_ESig_Provider    ← Issues qualified signing certificates
│   └── rQSigCDs_Provider          ← Provides remote signing devices
```

---

## Reference

**TS5 - Specification of common formats and API for Relying Party Registration information:**

https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts5-common-formats-and-api-for-rp-registration-information.md
