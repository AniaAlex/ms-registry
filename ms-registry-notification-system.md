# MS Registry and Notification System Documentation

## Architecture Overview

The EUDI Wallet ecosystem has a clear separation between Member State Registries and the Commission's Notification System:

```
┌─────────────────────────────────────────────────────────────┐
│                    EUROPEAN COMMISSION                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │     Secure Electronic Notification System            │    │
│  │     (receives notifications, publishes trusted lists)│    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ Notification API
                              │ (POST/PUT/DELETE providers)
                              │
┌─────────────────────────────┼───────────────────────────────┐
│         MEMBER STATE        │                                │
│  ┌──────────────────────────┴──────────────────────────┐    │
│  │            Client Component                          │    │
│  │   (notifies Commission about MS providers)           │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │      Member State Registry (this project)            │   │
│  │      - Registers Wallet Relying Parties              │   │
│  │      - Managed by WRP Registrar                      │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Key Distinctions

| System | Operated By | Purpose |
|--------|-------------|---------|
| **Member State Registry** | Member State (Registrar) | Register Wallet Relying Parties within the country |
| **Notification System** | European Commission | Receive notifications about MS providers and publish trusted lists |

## What Gets Notified to the Commission?

The Member State notifies the **Commission** about:
- The **Registrar** (who runs the registry)
- The **Register** (the registry itself - name, URL)
- Wallet Providers
- PID Providers
- PubEAA Providers
- WRP Access Certificate Providers

---

## TS2 Data Model (Notification System)

The TS2 data model defines how to **describe providers when notifying the European Commission**. It's the format for the **Notification System API**, not for how a registry internally stores its data.

### Class Hierarchy

```
LegalEntity (base class)
    │
    └── Provider (inherits from LegalEntity)
            │
            ├── WRPRegistrar (Wallet-Relying Party Registrar)
            ├── WalletProvider
            ├── PIDProvider
            ├── PubEAAProvider
            ├── TrustServiceProvider
            │       └── WRPAccCertProvider
            └── WalletRelyingParty
```

### Core Classes

#### 1. LegalEntity (base)
| Attribute | Cardinality | Type | Description |
|-----------|-------------|------|-------------|
| legalPerson | [0..1] | LegalPerson | If the entity is a legal person |
| naturalPerson | [0..1] | NaturalPerson | If the entity is a natural person |
| identifier | [0..*] | Identifier | EORI, LEI, EUID, VAT, national ID |
| postalAddress | [0..*] | string | Postal address (ITU-T X.520) |
| country | [1..1] | string | ISO 3166-1 alpha-2 code or "EU" |
| email | [0..*] | string | Email addresses (RFC 5322) |
| phone | [0..*] | string | Phone numbers (RFC 2806) |
| infoURI | [0..*] | string | URIs for info webpages |

#### 2. Provider (extends LegalEntity)
| Attribute | Cardinality | Type | Description |
|-----------|-------------|------|-------------|
| providerType | [1..1] | string | WRPRegistrar, WalletProvider, PIDProvider, etc. |
| policy | [1..*] | Policy | Registration policy, privacy policy, T&C |
| x5c | [0..*] | string | X.509 certificate chains (RFC 7515) |

#### 3. WRPRegistrar (extends Provider)
| Attribute | Cardinality | Type | Description |
|-----------|-------------|------|-------------|
| register | [1..1] | string | Name of the register |
| registerURI | [1..*] | string | URL(s) where register is accessible |

#### 4. WalletProvider (extends Provider)
| Attribute | Cardinality | Type | Description |
|-----------|-------------|------|-------------|
| walletSol | [1..*] | WalletSolution | Wallet solution details |

#### 5. PIDProvider (extends Provider)
| Attribute | Cardinality | Type | Description |
|-----------|-------------|------|-------------|
| PIDIssuer | [0..1] | string | Body responsible for associating PID with wallet |

### Auxiliary Classes

#### Identifier
| Attribute | Type | Description |
|-----------|------|-------------|
| type | string | URI: `http://data.europa.eu/eudi/id/EORI-No`, `/LEI`, `/EUID`, `/VAT`, `/NationalId` |
| identifier | string | The actual identifier value |

#### Policy
| Attribute | Type | Description |
|-----------|------|-------------|
| type | string | URI: `.../trust-service-practice-statement`, `.../terms-and-conditions`, `.../privacy-statement`, `.../registration-policy` |
| policyURI | string | URL where policy is published |

#### LegalPerson
| Attribute | Type | Description |
|-----------|------|-------------|
| legalName | string[1..*] | Legal name from official records |
| establishedByLaw | Law[0..*] | Legal basis (for public sector bodies) |

#### WalletSolution
| Attribute | Type | Description |
|-----------|------|-------------|
| solProvider | string | Body providing the wallet solution |
| walletName | string | Name of the wallet solution |
| refNum | string | Reference number (Official Journal) |

### Notification API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/providers` | List providers with filter criteria |
| POST | `/v1/{country}/providers` | Create a provider |
| GET | `/v1/{country}/providers/{providerId}` | Get provider details |
| PUT | `/v1/{country}/providers/{providerId}` | Update provider data |
| DELETE | `/v1/{country}/providers/{providerId}` | Delete a provider |

---

## MS Registry Data Model (This Project)

The MS Registry uses **TS5/TS6** and **Trust Infrastructure Schema** for its internal data model.

### Entities Covered by TS5/MS Registry

Despite the name "Relying Party Registration," TS5 actually covers **all entities that register with a Member State Registrar**:

| Entity Type | Role | Entitlement URI |
|-------------|------|-----------------|
| **Service Provider** | Verifier (requests attributes) | `https://uri.etsi.org/19475/Entitlement/Service_Provider` |
| **PID Provider** | Issuer (issues PID) | `https://uri.etsi.org/19475/Entitlement/PID_Provider` |
| **QEAA Provider** | Issuer (Qualified EAA) | `https://uri.etsi.org/19475/Entitlement/QEAA_Provider` |
| **PuB-EAA Provider** | Issuer (Public sector EAA) | `https://uri.etsi.org/19475/Entitlement/PUB_EAA_Provider` |
| **Non-Q EAA Provider** | Issuer (Non-qualified EAA) | `https://uri.etsi.org/19475/Entitlement/Non_Q_EAA_Provider` |
| **Intermediary** | Acts on behalf of other RPs | `https://uri.etsi.org/19475/Entitlement/Intermediary` |

The term **"Wallet-Relying Party"** in the regulation includes **anyone who relies on EUDI Wallets** - this means:
- **Verifiers** who request attributes from wallets
- **Issuers** who need to verify identity before issuing credentials

From TS5:
> *"An attestation provider that requires presentation of another attestation during issuance of their own attestation SHALL register both as a Service_Provider and with their attestation provider entitlement in a single registration."*

**Link:** https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts5-common-formats-and-api-for-rp-registration-information.md

### Comparison: TS2 vs MS Registry Model

| Aspect | TS2 (Notification) | MS Registry (TS5/TS6) |
|--------|-------------------|----------------------|
| **Purpose** | Describe providers to EC | Manage entity registrations |
| **Main Entity** | `Provider` (WRPRegistrar, WalletProvider, etc.) | `RegisteredEntity` (RP, PID, Attestation) |
| **Focus** | Provider metadata | Registration lifecycle + intended uses |
| **Certificates** | `x5c` (static chains) | Full certificate management with CT logs |
| **Status** | Not tracked | `RegistrationStatus` (pending, active, suspended, revoked) |
| **Intended Use** | Not present | Full support with credentials/claims |

---

## Official Standards Links

### Primary Standards (Registry Data Model)

| Document | Description | Link |
|----------|-------------|------|
| **TS5** | Common Formats and API for RP Registration Information | https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts5-common-formats-and-api-for-rp-registration-information.md |
| **TS6** | Common Set of Information to be Registered | https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts6-common-set-of-information-to-be-registered.md |
| **Trust Infrastructure Schema** | WEBUILD WP4 - Trust Infrastructure | https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts4-trust-infrastructure-detailed-specification.md |

### Supporting Standards

| Document | Description | Link |
|----------|-------------|------|
| **TS2** | Notification & Publication of Provider Information (for notifying EC) | https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts2-notification-publication-provider-information.md |
| **ARF** | Architecture Reference Framework | https://github.com/eu-digital-identity-wallet/eudi-doc-architecture-and-reference-framework |

### Legal Basis (EUR-Lex)

| Regulation | Description | Link |
|------------|-------------|------|
| **eIDAS2** | (EU) No 910/2014 (amended) | https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A02014R0910-20241018 |
| **CIR 2024/2979** | Relying Party Registration Rules | https://eur-lex.europa.eu/eli/reg_impl/2024/2979/oj |
| **CIR 2024/2980** | Notification to Commission | https://eur-lex.europa.eu/eli/reg_impl/2024/2980/oj |

### Main Repository

All technical specifications: https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications

---

## Summary

- **This project (ms_registry)**: Implements a Member State Registry based on TS5/TS6
- **TS2**: Defines how to notify the Commission about your registry (as a WRPRegistrar) and other providers
- The Notification System is operated by the EC, not part of the MS Registry
