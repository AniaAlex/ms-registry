# Access Certificate Analysis: Skatteverket Example

This document compares the provided certificate/CSR configuration against the normative requirements, identifying issues and citing references.

**Date**: 2026-04-24  
**Entity**: Skatteverket (Swedish Tax Agency)  
**Certificate Type**: Wallet-Relying Party Access Certificate (WRPAC)

---

## 1. Issues Identified

### 1.1 Incorrect Key Size for ECDSA

| Field | Provided Value | Correct Value | Issue |
|-------|----------------|---------------|-------|
| `default_bits` | `256` | N/A (use `default_md` for ECDSA) | `default_bits` is RSA parameter, not ECDSA |

**Reference**: RFC 5480, ETSI EN 319 412-1

**Explanation**: For ECDSA keys, you don't use `default_bits`. Instead:
- Use `openssl ecparam -name prime256v1` for P-256 curve
- Or specify in CSR command: `openssl req -new -newkey ec:<(openssl ecparam -name prime256v1)`

---

### 1.2 Incorrect organizationIdentifier Format

| Field | Provided Value | Correct Value | Issue |
|-------|----------------|---------------|-------|
| `organizationIdentifier` | `VATSE-202100524011` | `VATSE-202100-5240-11` (with hyphens) | Swedish org numbers use format NNNNNN-NNNN |

**Reference**: ETSI EN 319 412-1 Section 5.1.4, Swedish organizational number format

**Correct format for Swedish entities**:
```
organizationIdentifier = VATSE-NNNNNN-NNNN
```
Where NNNNNN-NNNN is the Swedish organizational number with hyphen.

---

### 1.3 Entity Setting CA-Controlled Fields

The following fields should NOT be in the CSR - they are set by the CA:

| Field | In CSR? | Should Be? | Who Sets It | Reference |
|-------|---------|------------|-------------|-----------|
| `basicConstraints` | ❌ Should not be | CA sets | Access CA | RFC 5280 Section 4.2.1.9 |
| `keyUsage` | ❌ Should not be | CA sets | Access CA | RFC 5280 Section 4.2.1.3 |
| `extendedKeyUsage` | ❌ Should not be | CA sets | Access CA | RFC 5280 Section 4.2.1.12 |
| `authorityKeyIdentifier` | ❌ Should not be | CA sets | Access CA | RFC 5280 Section 4.2.1.1 |
| `subjectKeyIdentifier` | ❌ Should not be | CA sets | Access CA | RFC 5280 Section 4.2.1.2 |
| `certificatePolicies` | ❌ Should not be | CA sets | Access CA | RFC 5280 Section 4.2.1.4 |
| `crlDistributionPoints` | ❌ Should not be | CA sets | Access CA | RFC 5280 Section 4.2.1.13 |
| `authorityInfoAccess` | ❌ Should not be | CA sets | Access CA | RFC 5280 Section 4.2.2.1 |

**Reference**: RFC 5280, ETSI EN 319 411-1, ETSI TS 119 411-8

---

## 2. CSR vs Certificate Field Responsibilities

### 2.1 Fields Entity MUST Provide in CSR

| Field | OID | Example Value | Reference |
|-------|-----|---------------|-----------|
| `commonName (CN)` | 2.5.4.3 | `Skatteverket PID Issuance Service` | RFC 5280 |
| `organizationName (O)` | 2.5.4.10 | `Skatteverket` | RFC 5280 |
| `countryName (C)` | 2.5.4.6 | `SE` | RFC 5280 |
| `organizationIdentifier` | 2.5.4.97 | `VATSE-202100-5240-11` | ETSI EN 319 412-1 Section 5.1.4 |
| `serialNumber` (optional) | 2.5.4.5 | Service identifier | RFC 5280 |

### 2.2 Fields CA Sets (NOT in CSR)

| Field | OID | Value Set By CA | Reference |
|-------|-----|-----------------|-----------|
| `basicConstraints` | 2.5.29.19 | `CA:FALSE` | RFC 5280 Section 4.2.1.9 |
| `keyUsage` | 2.5.29.15 | `digitalSignature` | RFC 5280 Section 4.2.1.3, ETSI TS 119 411-8 |
| `extendedKeyUsage` | 2.5.29.37 | `id-kp-clientAuth` (1.3.6.1.5.5.7.3.2) | RFC 5280, ETSI TS 119 411-8 |
| `certificatePolicies` | 2.5.29.32 | Access CA policy OID | RFC 5280 Section 4.2.1.4 |
| `qcStatements` | 1.3.6.1.5.5.7.1.3 | Entitlement OIDs | ETSI EN 319 412-5, ETSI TS 119 475 |

### 2.3 Entitlement OIDs (Set by CA based on registration)

| Entitlement | OID | Reference |
|-------------|-----|-----------|
| PID Provider | `0.4.0.19475.1.1` | ETSI TS 119 475 |
| QEAA Provider | `0.4.0.19475.1.2` | ETSI TS 119 475 |
| PuB-EAA Provider | `0.4.0.19475.1.3` | ETSI TS 119 475 |
| Non-qualified EAA Provider | `0.4.0.19475.1.4` | ETSI TS 119 475 |
| General Relying Party (Service Provider) | `0.4.0.19475.1.5` | ETSI TS 119 475 |

---

## 3. Corrected .cnf File Template

```ini
# Corrected OpenSSL configuration for Skatteverket PID Provider Access Certificate CSR
# Entity-provided fields ONLY - CA will add extensions

[ req ]
distinguished_name = req_distinguished_name
prompt = no
# For ECDSA, key is generated separately, not via default_bits

[ req_distinguished_name ]
# Required fields - Entity provides these
countryName = SE
organizationName = Skatteverket
organizationIdentifier = VATSE-202100-5240-11
commonName = Skatteverket PID Issuance Service

# Optional fields
# serialNumber = <service-specific-identifier>
# localityName = Stockholm
# stateOrProvinceName = Stockholm
```

**CSR Generation Command** (for ECDSA P-256):
```bash
# Generate EC key
openssl ecparam -name prime256v1 -genkey -noout -out skatteverket_pid.key

# Generate CSR
openssl req -new -key skatteverket_pid.key -out skatteverket_pid.csr -config skatteverket_pid.cnf
```

---

## 4. What CA Adds to Certificate

The Access CA will add the following extensions based on the entity's registration data:

| Extension | Value | Source |
|-----------|-------|--------|
| `basicConstraints` | `CA:FALSE` | CA policy |
| `keyUsage` | `digitalSignature` | ETSI TS 119 411-8 |
| `extendedKeyUsage` | `id-kp-clientAuth` | ETSI TS 119 411-8 |
| `certificatePolicies` | CA policy OID | CA Certificate Policy |
| `qcStatements.QcType` | `id-etsi-qct-web` | ETSI EN 319 412-5 |
| `qcStatements.QcEuPDS` | PDS URL | CA policy |
| `entitlements` | `0.4.0.19475.1.1` (PID Provider) | ETSI TS 119 475, based on registration |
| `subEntitlements` | Attestation type OIDs | ETSI TS 119 475, based on registration |
| `authorityKeyIdentifier` | CA key identifier | RFC 5280 |
| `subjectKeyIdentifier` | Hash of subject public key | RFC 5280 |
| `crlDistributionPoints` | CRL URL | CA infrastructure |
| `authorityInfoAccess` | OCSP URL, CA cert URL | CA infrastructure |

---

## 5. Validation Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Key algorithm correct (ECDSA P-256 or RSA 2048+) | ⚠️ | Fix key generation command |
| organizationIdentifier format correct | ❌ | Add hyphens: `VATSE-NNNNNN-NNNN` |
| CSR contains only entity fields | ❌ | Remove CA-controlled extensions |
| countryName is ISO 3166-1 alpha-2 | ✅ | `SE` is correct |
| organizationName matches registration | ✅ | `Skatteverket` |
| commonName identifies service | ✅ | `Skatteverket PID Issuance Service` |

---

## 6. References

| Document | Section | Topic |
|----------|---------|-------|
| RFC 5280 | 4.1, 4.2 | Certificate and extension profiles |
| ETSI EN 319 412-1 | 5.1.4 | organizationIdentifier semantics |
| ETSI EN 319 412-5 | 4.2 | QC statements |
| ETSI TS 119 411-8 | 6 | WRPAC certificate profile |
| ETSI TS 119 475 | 5 | Entitlement OIDs |
| ETSI EN 319 411-1 | 6.3 | Certificate issuance requirements |
| [relying_party_access_certificate.md](../../task5-participants-certificates-policies/relying_party_access_certificate.md) | - | WP4 WRPAC profile |
| [pid_provider_access_certificate.md](../../task5-participants-certificates-policies/pid_provider_access_certificate.md) | - | WP4 PID Provider certificate profile |
| [eaa_provider_access_certificate.md](../../task5-participants-certificates-policies/eaa_provider_access_certificate.md) | - | WP4 EAA Provider certificate profile |

---

## 7. Documentation Gaps Identified

| Gap | Description | Status |
|-----|-------------|--------|
| CSR submission protocol | How CSR is submitted to Access CA | ❌ Not documented |
| Registrar→Access CA notification | API for registration data transfer | ❌ Not documented |
| Certificate return mechanism | How certificate is delivered to entity | ❌ Not documented |
| Entitlement verification | How CA verifies entitlements against registry | ❌ Not documented |
