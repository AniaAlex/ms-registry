# What Data to Get from ms-registry for go-trust-ecosystem

go-trust-ecosystem requires per entity: `entity.yaml`, `cert.pem`, and a public JWK
file (`pid_key.jwk` or `eaa_key.jwk`). This document summarises what is available in
ms-registry today and what is missing.

## entity.yaml fields

| Field | Available? | Source in ms-registry |
|---|---|---|
| `names` | ✅ | `RegisteredEntity.trade_name` — emit as single `{language: en, value: ...}` entry |
| `entityId` | ✅ | `RegisteredEntity.registry_uri` |
| `entityType` | ✅ | derived from `EntityEntitlement.entitlement_type` (`PID_Provider` → `"pid-provider"`, `PUB_EAA_Provider` → `"pubeaa-provider"`) |
| `status` (PID) | ✅ | hardcoded `granted` — field is ignored in output |
| `status` (PuB-EAA) | ✅ | `registration_status`: `active` → `notified`, `revoked` → `withdrawn` (see note below) |
| `address.postal.streetAddress` | ✅ | `LegalEntity → PhysicalAddress.street_address` |
| `address.postal.locality` | ✅ | `LegalEntity → PhysicalAddress.locality` |
| `address.postal.postalCode` | ✅ | `LegalEntity → PhysicalAddress.postal_code` |
| `address.postal.countryName` | ✅ | `LegalEntity → PhysicalAddress.country_code` |
| `address.electronic` | ✅ | `LegalEntity.info_uri`, `LegalEntity.email` (formatted as `mailto:`) |
| `informationURI` | ✅ | `LegalEntity.info_uri` — emit as `{language: en, value: ...}` |
| `services[].serviceNames` | ✅ | `EntityServiceDescription` (lang + content) |
| `services[].serviceType` | ✅ | `EntityEntitlement.entitlement_uri` |
| `services[].status` | ✅ | same as top-level status |

## cert.pem

| Available? | Source |
|---|---|
| ⚠️ Partial | `TSPCertificate.certificate_pem` via `LegalEntity → trust_service_providers → certificates` (tsl_generator app). Present in the data model but populated manually — not part of the entity registration API flow. |

## Public JWK

| File | Available? | Notes |
|---|---|---|
| `pid_key.jwk` | ❌ Missing | No JWK field anywhere in ms-registry |
| `eaa_key.jwk` | ❌ Missing | No JWK field anywhere in ms-registry |

A new field is needed on `RegisteredEntity` (or a related model) to store the public
JWK of the credential signing key.

Options:
- Simple: `public_jwk = models.JSONField(null=True, blank=True)` on `RegisteredEntity`
- Structured: a separate `EntityPublicKey` model (supports key rotation history)

## Query to collect PID providers

```python
RegisteredEntity.objects.filter(
    registration_status="active",
    entitlements__entitlement_type="PID_Provider"
).select_related(
    "legal_entity__legal_person",
    "legal_entity__physical_address",
    "legal_entity__trust_service_providers",
).prefetch_related(
    "entitlements",
    "service_descriptions",
)
```

## Query to collect PuB-EAA providers

Both active and revoked must be included — withdrawn entries stay in the LoTE
permanently so relying parties can verify past attestations.

```python
RegisteredEntity.objects.filter(
    registration_status__in=["active", "revoked"],
    entitlements__entitlement_type="PUB_EAA_Provider"
).select_related(
    "legal_entity__legal_person",
    "legal_entity__physical_address",
    "legal_entity__trust_service_providers",
).prefetch_related(
    "entitlements",
    "service_descriptions",
)
```

## Note on PuB-EAA status

It is unclear where the information about `notified`/`withdrawn` status for PuB-EAA
providers comes from in practice — who sets it, when, and through what process.
**Decision (initial implementation):** treat all active PuB-EAA providers as
`notified`. If notification turns out to be a separate explicit step in the future,
a dedicated status field can be added then.
