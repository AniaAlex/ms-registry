# Use Cases: Relying Parties with Multiple Intended Uses

## Overview

A Wallet Relying Party can register **multiple Intended Uses** under a single registration. This allows one entity to request different data for different purposes while maintaining GDPR compliance through data minimisation.

From TS5:
```
intendedUse [0..*] Array of IntendedUse objects
```

The `[0..*]` multiplicity means **zero to many** intended uses per registration.

---

## Intended Use Scenarios

| Scenario | intendedUse Count | Valid? |
|----------|-------------------|--------|
| Intermediary only (no direct data requests) | 0 | ✅ |
| Single use case | 1 | ✅ |
| Multiple use cases | 2+ | ✅ |

---

## Use Case 1: Bank with Multiple Services

A bank registers once but has different data needs for different services:

```
Bank AB (RegisteredEntity)
│
├── IntendedUse #1: "Account Opening"
│   ├── intendedUseIdentifier: "BANK-AB-IU-001"
│   ├── Purpose: "Know Your Customer (KYC) verification for new account"
│   ├── Credentials requested:
│   │   └── PID (family_name, given_name, date_of_birth, address)
│   └── Privacy Policy: https://bank.se/privacy/account-opening
│
├── IntendedUse #2: "Loan Application"
│   ├── intendedUseIdentifier: "BANK-AB-IU-002"
│   ├── Purpose: "Credit assessment for loan application"
│   ├── Credentials requested:
│   │   ├── PID (family_name, given_name, date_of_birth)
│   │   └── Income Attestation (annual_income, employer)
│   └── Privacy Policy: https://bank.se/privacy/loans
│
└── IntendedUse #3: "ATM Age Verification"
    ├── intendedUseIdentifier: "BANK-AB-IU-003"
    ├── Purpose: "Verify user is 18+ for cash withdrawal limit increase"
    ├── Credentials requested:
    │   └── PID (age_over_18 only)
    └── Privacy Policy: https://bank.se/privacy/atm
```

---

## Use Case 2: E-Commerce Platform

An online retailer with different verification needs:

```
ShopOnline AB (RegisteredEntity)
│
├── IntendedUse #1: "Standard Purchase"
│   ├── intendedUseIdentifier: "SHOP-IU-001"
│   ├── Purpose: "Verify identity for order delivery"
│   ├── Credentials requested:
│   │   └── PID (family_name, given_name, address)
│   └── Privacy Policy: https://shop.se/privacy/orders
│
├── IntendedUse #2: "Age-Restricted Products"
│   ├── intendedUseIdentifier: "SHOP-IU-002"
│   ├── Purpose: "Age verification for alcohol/tobacco purchase"
│   ├── Credentials requested:
│   │   └── PID (age_over_18)
│   └── Privacy Policy: https://shop.se/privacy/age-restricted
│
└── IntendedUse #3: "Loyalty Program Enrollment"
    ├── intendedUseIdentifier: "SHOP-IU-003"
    ├── Purpose: "Create personalized loyalty account"
    ├── Credentials requested:
    │   └── PID (family_name, given_name, email)
    └── Privacy Policy: https://shop.se/privacy/loyalty
```

---

## Use Case 3: Healthcare Provider

A hospital with different clinical and administrative needs:

```
Regional Hospital (RegisteredEntity)
│   isPSB: true (Public Sector Body)
│
├── IntendedUse #1: "Patient Registration"
│   ├── intendedUseIdentifier: "HOSP-IU-001"
│   ├── Purpose: "Register new patient in hospital system"
│   ├── Credentials requested:
│   │   ├── PID (full identity data)
│   │   └── Health Insurance Card
│   └── Privacy Policy: https://hospital.se/privacy/patients
│
├── IntendedUse #2: "Emergency Treatment"
│   ├── intendedUseIdentifier: "HOSP-IU-002"
│   ├── Purpose: "Access critical health information in emergency"
│   ├── Credentials requested:
│   │   ├── PID (family_name, given_name, date_of_birth)
│   │   └── Medical Allergies Attestation
│   └── Privacy Policy: https://hospital.se/privacy/emergency
│
└── IntendedUse #3: "Prescription Collection"
    ├── intendedUseIdentifier: "HOSP-IU-003"
    ├── Purpose: "Verify identity for controlled substance pickup"
    ├── Credentials requested:
    │   └── PID (family_name, given_name, personal_id_number)
    └── Privacy Policy: https://hospital.se/privacy/pharmacy
```

---

## Use Case 4: University (Dual Role - Issuer + Verifier)

A university that both requests and issues attestations:

```
Stockholm University (RegisteredEntity)
│   isPSB: true
│   Entitlements: [Service_Provider, PUB_EAA_Provider]
│
├── providesAttestations (as Issuer):
│   ├── Diploma Attestation
│   ├── Student ID Attestation
│   └── Enrollment Certificate
│
├── IntendedUse #1: "Student Enrollment" (as Verifier)
│   ├── intendedUseIdentifier: "UNI-IU-001"
│   ├── Purpose: "Verify identity for university enrollment"
│   ├── Credentials requested:
│   │   ├── PID (full identity)
│   │   └── Secondary School Diploma
│   └── Privacy Policy: https://uni.se/privacy/enrollment
│
└── IntendedUse #2: "Library Access" (as Verifier)
    ├── intendedUseIdentifier: "UNI-IU-002"
    ├── Purpose: "Verify student status for library services"
    ├── Credentials requested:
    │   └── Student ID Attestation (from any university)
    └── Privacy Policy: https://uni.se/privacy/library
```

---

## Use Case 5: Intermediary Acting for Multiple End-RPs

An identity verification service acting on behalf of multiple clients:

```
IDVerify AB (RegisteredEntity)
│   isIntermediary: true
│   Entitlements: [Service_Provider, Intermediary]
│
├── IntendedUse #1: "General Age Verification"
│   ├── intendedUseIdentifier: "IDVERIFY-IU-001"
│   ├── Purpose: "Age verification service for client websites"
│   ├── Credentials requested:
│   │   └── PID (age_over_18)
│   └── Privacy Policy: https://idverify.se/privacy/age
│
└── IntendedUse #2: "Full KYC Service"
    ├── intendedUseIdentifier: "IDVERIFY-IU-002"
    ├── Purpose: "Complete identity verification for client onboarding"
    ├── Credentials requested:
    │   └── PID (full identity data)
    └── Privacy Policy: https://idverify.se/privacy/kyc

---
End-Relying Parties using this Intermediary:
├── WebShop A (usesIntermediary: IDVerify AB)
├── Gaming Site B (usesIntermediary: IDVerify AB)
└── Fintech C (usesIntermediary: IDVerify AB)
```

---

## Key Principles

### 1. Data Minimisation (GDPR Article 5.1c)
Each intended use should request **only** the minimum credentials and claims needed for that specific purpose.

### 2. Purpose Limitation (GDPR Article 5.1b)
Each intended use has a specific, declared purpose. Data collected under one intended use cannot be used for another purpose.

### 3. Transparency
- Each intended use has its own privacy policy URL
- The wallet displays the specific `purpose` to the user before consent
- Users can see exactly what data is being requested and why

### 4. Separate Registration Certificates
If the Member State issues Registration Certificates (RPRC), each intended use gets its own certificate with the same `intendedUseIdentifier`.

### 5. Independent Validity
Each intended use has its own:
- `createdAt` (validity start)
- `revokedAt` (validity end, if revoked or expired)

An entity can revoke or expire one intended use without affecting others.

---

## Implementation in This Registry

```python
# One RegisteredEntity can have many IntendedUses
class IntendedUse(BaseModel):
    registered_entity = models.ForeignKey(
        RegisteredEntity, 
        on_delete=models.CASCADE, 
        related_name="intended_uses"
    )
    intended_use_identifier = models.CharField(max_length=500, unique=True)
    validity_start = models.DateField()
    validity_end = models.DateField(blank=True, null=True)
    
# Each IntendedUse has its own purposes (multilingual)
class IntendedUsePurpose(BaseModel):
    intended_use = models.ForeignKey(IntendedUse, related_name="purposes")
    lang = models.CharField(max_length=5)
    content = models.TextField()

# Each IntendedUse has its own privacy policies
class IntendedUsePrivacyPolicy(BaseModel):
    intended_use = models.ForeignKey(IntendedUse, related_name="privacy_policies")
    policy = models.ForeignKey(Policy)

# Each IntendedUse specifies which credentials it requests
class IntendedUseCredential(BaseModel):
    intended_use = models.ForeignKey(IntendedUse, related_name="credential_links")
    credential = models.ForeignKey(Credential)
    is_mandatory = models.BooleanField(default=False)
```

---

## Reference

- **TS5**: https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts5-common-formats-and-api-for-rp-registration-information.md
- **CIR 2025/848**: Commission Implementing Regulation on Relying Party Registration
- **GDPR**: Regulation (EU) 2016/679 - Data minimisation and purpose limitation principles


the question of person validation 
