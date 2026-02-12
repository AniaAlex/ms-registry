# Summary 09-02-2026: rp_registration App Restructuring

## Proposed Django App Structure

Splitting the monolithic `rp_registration` app (~1174 lines of models) into focused domain apps:

```
rp_register/
├── core/                   # Domain foundations: Law, Identifier, Policy, enums
├── legal_entities/         # LegalPerson, NaturalPerson, PhysicalAddress, LegalEntity
├── registry/               # RegisteredEntity lifecycle + entitlements + DPA
├── credentials/            # Credential, Claim, IntendedUse, attestations
├── certificates/           # Access/Registration Certificates, AuditLog
└── tsl_generator/          # TSL XML generation (existing)
```

## App Contents

### 1. `core` - Domain Foundations
Foundational components shared across all apps.

| Component | Purpose |
|-----------|---------|
| `UUIDModel` | Abstract model with UUID primary key |
| `TimestampedModel` | Abstract model with `created_at`/`updated_at` |
| `Law` | Legal references |
| `Identifier` | Entity identifiers (EUID, VAT, LEI, etc.) |
| `Policy` | Privacy/Terms policies |
| All `TextChoices` enums | `EntityRole`, `EntityType`, `IdentifierType`, `CredentialFormat`, `RegistrationStatus`, etc. |

#### Abstract Base Models

```python
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)

    class Meta:
        abstract = True
```

Models can inherit from one or both:
- `class MyModel(UUIDModel, TimestampedModel):` — UUID + timestamps
- `class MyModel(UUIDModel):` — UUID only
- `class MyModel(TimestampedModel):` — Auto-increment ID + timestamps

### 2. `legal_entities` - Legal Entity Management
Legal person/natural person identity management.

| Component | Purpose |
|-----------|---------|
| `LegalPerson` | Company/organization data |
| `NaturalPerson` | Individual person data |
| `PhysicalAddress` | Address records |
| `LegalEntity` | Unified entity wrapper |
| `LegalEntityIdentifier` | M2M link to identifiers |

### 3. `registry` - Entity Lifecycle Management
Main registration logic for EUDI Wallet entities (full lifecycle: register → suspend → revoke).

| Component | Purpose |
|-----------|---------|
| `RegisteredEntity` | Main entity registration (RP, PID Provider, Attestation Provider) |
| `EntitySupportURI` | Support URIs [1..*] |
| `EntityEntitlement` | Authorization entitlements [1..*] |
| `EntityServiceDescription` | Multilingual descriptions |
| `RegisteredEntityPolicy` | Policy links |
| `SupervisoryAuthority` | DPA records |
| `EntityUsesIntermediary` | RP → Intermediary relationships |

### 4. `credentials` - Credential & Attestation Management
Attestation types, claims, and intended use tracking.

| Component | Purpose |
|-----------|---------|
| `Credential` | Attestation format definitions (SD-JWT, mDL, etc.) |
| `Claim` | Claim paths within credentials |
| `IntendedUse` | Data request use cases |
| `IntendedUsePurpose` | Multilingual purposes |
| `IntendedUsePrivacyPolicy` | Privacy policy links |
| `IntendedUseCredential` | Requested credentials M2M |
| `EntityProvidesAttestation` | Attestations provided by issuers |

### 5. `certificates` - Certificate & Audit Management
PKI and certificate transparency management.

| Component | Purpose |
|-----------|---------|
| `EntityAccessCertificate` | Access certificate history with CT logs |
| `EntityRegistrationCertificate` | Optional registration certificates |
| `AuditLog` | Change tracking |

## Dependency Graph

```
core
  ↑
legal_entities
  ↑
registry ←── credentials
  ↑              ↑
certificates ────┘
```

## Benefits

| Benefit | Description |
|---------|-------------|
| **Single Responsibility** | Each app handles one domain concern |
| **Reusability** | `core` and `legal_entities` can be reused by other projects |
| **Team Scaling** | Different teams can own different apps |
| **Testing** | Isolated test suites per domain |
| **Migration Management** | Smaller, focused migrations |
| **Clear Dependencies** | `core` ← `legal_entities` ← `registry` ← `credentials`/`certificates` |

## Implementation Notes

1. **Cross-app ForeignKeys**: Use `'app_label.ModelName'` string references
2. **Circular Imports**: Keep `core` dependency-free; use lazy imports
3. **Migrations**: Run `makemigrations` for each app in dependency order
4. **Admin**: Split admin.py accordingly, use `autocomplete_fields` across apps
5. **Settings**: Add all apps to `INSTALLED_APPS`:
   ```python
   INSTALLED_APPS = [
       ...
       'core',
       'legal_entities',
       'registry',
       'credentials',
       'certificates',
       'tsl_generator',
   ]
   ```

## Naming Decision: `registry` vs alternatives

Chose **`registry`** because:
- Aligns with ARF/Trust Infrastructure terminology ("Member State Registrar", "registryURI")
- Covers full entity lifecycle (not just "onboarding" or "registration")
- Matches domain language used in spec documents

## Naming Decision: `core` vs `utils`

Chose **`core`** because:
- Contains **domain models** (Law, Identifier, Policy), not generic utilities
- These are EUDI Wallet-specific concepts, not reusable helpers
- `utils` should be reserved for helper functions (formatters, validators, etc.)
