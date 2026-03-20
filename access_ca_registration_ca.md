# Access Certificate and Registry Relationship

This document describes the relationship between Registrars, Access Certificate Authorities (Access CAs), and the certificate issuance flow in the EUDI Wallet trust infrastructure.

## Overview

Access Certificates are issued to registered entities (PID Providers, Attestation Providers, Relying Parties) to enable authentication during service interactions with Wallet Units. The issuance process involves coordination between Registrars and Access Certificate Authorities.

## Key Entities

### Registrar
- Established by Member States to manage registration and operational authorization
- Collects entity data: identification, entitlements, attestation types, service endpoints
- Maintains the **registry** (publicly accessible database of registered entities)
- Approves or rejects registration applications
- Initiates access certificate requests to the Access CA

### Access Certificate Authority (Access CA)
- Issues access certificates to entities that have been registered by a Registrar
- Notified by Member States to the European Commission (does not register with Registrars)
- Listed on the **Access CA Trusted List** (compiled by EC)
- Verifies registration status before issuing certificates
- Logs all issued certificates for Certificate Transparency

## Certificate Issuance Flow

```
┌─────────────┐    1. Register    ┌─────────────┐
│   Entity    │ ───────────────▶  │  Registrar  │
│ (RP, PID,   │                   │             │
│  EAA, etc.) │                   └──────┬──────┘
└─────────────┘                          │
                                         │ 2. Inform Access CA
                                         │    (send entity parameters)
                                         ▼
                                  ┌─────────────┐
                                  │  Access CA  │
                                  │             │
                                  └──────┬──────┘
                                         │
                    3. Verify against    │
                       National Register │
                                         ▼
                                  ┌─────────────┐
                                  │  National   │
                                  │  Register   │
                                  └──────┬──────┘
                                         │
                    4. Issue Access      │
                       Certificate       │
                                         ▼
                                  ┌─────────────┐
                                  │   Entity    │
                                  │ (receives   │
                                  │  certificate)│
                                  └─────────────┘
```

### Step 1: Entity Registration
The entity registers with the Member State Registrar, providing:
- Identification data (name, country, business registration number)
- Entitlements (attestation types to issue, or attributes to request)
- Service supply points (URLs)

### Step 2: Access Certificate Request
After successful registration, the Registrar informs the Access Certificate Authority about the registered entity, providing the parameters needed for certificate issuance.

*Reference*: [Regulation (EU) 2025/848, Article 7, Annex IV](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202500848)

### Step 3: Access CA Verification
The Access CA independently verifies:
- That the entity is included **with a valid registration status** in the National Register
- That information in the certificate request is **accurate and consistent** with the registration information

*Reference*: Regulation (EU) 2025/848, Annex IV requires:
> "the obligation for the providers of wallet-relying party access certificates, when issuing a wallet-relying party access certificate, to verify that the wallet-relying party is included, with a valid registration status, in a National Register"

### Step 4: Certificate Issuance
If verification passes, the Access CA issues the access certificate containing:
- Entity identification (name, country, organization identifier)
- Reference to registration information
- Certificate policy references
- Trust anchor chain information

The certificate is logged per Certificate Transparency requirements.

## Trust Anchor Requirements

### Baseline Registry Requirement
The CA used with the baseline registry **MUST** be one of the CAs listed on the Access CA Trusted List (or Registration Certificate Provider TL). This ensures:
- Wallet Units can verify the certificate chain by looking up the CA in the TL
- Trust anchors are discoverable via the LoTL → TL hierarchy
- Per **RPACANot_04**: Trust anchors are accepted because of "secure notification by the Member States to the Commission and by their publication in the corresponding Commission-compiled Trusted Lists"

### Access CA Trusted List
The Access CA TL is compiled by the European Commission and contains trust anchors for all notified Access Certificate Authorities. Wallet Units use this TL to validate access certificates presented by Relying Parties and Providers.

## Validation by Wallet Units

When a Wallet Unit receives an access certificate, it performs dual validation:

1. **Certificate Validation**: Verify the certificate chains to a trusted CA listed in the Access CA TL (via LoTL discovery)
2. **Registry Validation**: Query the National Register API to verify:
   - Entity registration status is valid
   - Requested attributes match registered entitlements (for RPs)
   - Attestation types match registered types (for Providers)

## Requirements References

| Requirement | Description | Source |
|-------------|-------------|--------|
| **Reg_10** | Access Certificate Authority SHALL issue access certificates to all PID Providers, QEAAs, PuB-EAAs, and non-qualified EAAs in registries | Topic 27, Topic 31 |
| **Reg_10a** | Member State SHALL ensure Access Certificate Authority issues one or more access certificates to all Relying Parties in registries. A Relying Party SHALL receive a separate access certificate for each of its Relying Party Instances | Topic 27 |
| **Reg_11** | Access Certificate Authority SHALL comply with at least ETSI EN 319 411-1 NCP requirements | Topic 27 |
| **RPACANot_04** | Trust anchors of Access CAs SHALL be accepted because of secure notification by Member States to Commission and publication in Commission-compiled Trusted Lists | Topic 31 |
| **RPA_04** | Wallet Unit SHALL verify Relying Party access certificate against Access CA TL | Topic 31 |

## Normative References

- [ETSI TS 119 411-8](https://www.etsi.org/deliver/etsi_ts/119400_119499/11941108/01.01.01_60/ts_11941108v010101p.pdf) - Access Certificate Policy for EUDI Wallet
- [ETSI EN 319 411-1](https://www.etsi.org/deliver/etsi_en/319400_319499/31941101/01.04.01_60/en_31941101v010401p.pdf) - Certificate Policy requirements (NCP)
- [Regulation (EU) 2025/848](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ:L_202500848) - Articles 7, 8, Annex IV, Annex V
- [Trust Infrastructure Schema](../../task2-trust-framework/trust-infrastructure-schema.md)
- [Consolidated Terms and Entity Definitions](../terms-and-entities.md)

## See Also

- [Relying Party Onboarding](relying_party_onboarding.md) - Steps 2.1-2.3 for RP access certificate flow
- [PID/EAA Provider Onboarding](pid_eaa_provider_onboarding.md) - Steps 2.1-2.3 for Provider access certificate flow
- [Trusted List Discovery and Consumption](../subtask1-2-trust-registry/trusted-list-discovery-consumption.md) - How entities discover and use TLs
