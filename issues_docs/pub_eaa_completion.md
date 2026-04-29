# PuB-EAA Provider — Implementation Notes

## Status values

Unlike PID providers (where status is ignored in the output), PuB-EAA `ServiceStatus`
IS written to the LoTE output:

- `notified` → provider is active in the LoTE
- `withdrawn` → provider has been removed, entry kept permanently

`revoked` in ms-registry maps to `withdrawn` in the LoTE.

**NOTE:** It is unclear where the information about `notified`/`withdrawn` status
for PuB-EAA providers comes from in practice — who sets it, when, and through what
process. **Decision (initial implementation):** treat all active PuB-EAA providers
as `notified`. If notification turns out to be a separate explicit step in the
future, a dedicated status field can be added then.

## Withdrawn entries must be kept in LoTE
Per ETSI requirements, withdrawn PuB-EAA entries must remain in the LoTE permanently
(so relying parties can verify past attestations). Unlike PID Providers, revoked PuB-EAA
entities must NOT be filtered out of the list.

## Status change timestamp tracking (missing)
The ms-registry currently only tracks the current status (`registration_status`) and has
no record of when a status change occurred. The LoTE requires `StatusStartingTime` for
withdrawn entries.

**What needs to be added:**
Either Option A (simple) or Option B (full audit trail):

**Option A — Timestamp fields on RegisteredEntity:**
```python
revoked_at = models.DateTimeField(null=True, blank=True)
suspended_at = models.DateTimeField(null=True, blank=True)
```

**Option B — Status history table (preferred):**
```python
class RegistrationStatusHistory(models.Model):
    registered_entity = ForeignKey(RegisteredEntity)
    status = CharField(...)
    changed_at = DateTimeField(auto_now_add=True)
    changed_by = CharField(...)
```

Option B gives a full audit trail and is the correct long-term solution.

## Digital identity certificate
PuB-EAA providers get their digital identity certificate issued by a QTSP as part of
the accreditation process. This certificate must be stored in the registry separately
from the EntityAccessCertificate (which is for API access control only).

A `digital_identity_certificate` field (X.509 PEM) needs to be added to
`RegisteredEntity` or as a related model, specifically for LoTE publication.

## LoTE query
When generating EUPubEAAProvidersList, include both active and revoked entities:
```python
pubeaa_entities = RegisteredEntity.objects.filter(
    registration_status__in=["active", "revoked"],
    entitlements__entitlement_type="PUB_EAA_Provider"
)
```
