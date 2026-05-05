# go-trust-ecosystem Adapter — Implementation Notes

## Architecture

ms-registry is the source of truth for registered entities. go-trust-ecosystem is a
separate library that consumes a YAML directory structure and produces signed LoTEs.

```
ms-registry (Django DB) → export command → YAML directory tree → go-trust-ecosystem → signed LoTE
```

The adapter is a Django management command that reads from the database and writes the
YAML directory structure that go-trust-ecosystem expects.

## go-trust-ecosystem input format (per entity)

Each entity gets a directory under `entities/<list_type>/entities/<slug>/` containing:

```
entity.yaml       ← entity metadata
cert.pem          ← digital identity X.509 certificate
pid_key.jwk       ← public JWK (PID providers)
eaa_key.jwk       ← public JWK (PuB-EAA providers)
```

### entity.yaml fields

```yaml
names:
  - language: en
    value: "Trade name in English"
entityId: "https://..."
entityType: "pid-provider"         # or "pubeaa-provider"
status: "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted"
address:
  postal:
    streetAddress: "..."
    locality: "..."
    postalCode: "..."
    countryName: "SE"
  electronic:
    - "https://..."
    - "mailto:..."
informationURI:
  - language: en
    value: "https://..."
services:
  - serviceNames:
      - language: en
        value: "..."
    serviceType: "http://uri.etsi.org/19602/SvcType/PIDProvider"
    status: "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted"
```

## Data source mapping

| entity.yaml field | Source in ms-registry |
|---|---|
| `names` | `RegisteredEntity.trade_name` (emit with `language: en`) |
| `entityId` | `RegisteredEntity.registry_uri` |
| `entityType` | derived from `EntityEntitlement.entitlement_type` |
| `status` (PID) | hardcoded `granted` — field is ignored in output anyway |
| `status` (PuB-EAA) | **MISSING — needs separate ETSI trust status field** (see below) |
| `address.postal` | `LegalEntity → PhysicalAddress` |
| `address.electronic` | `LegalEntity.info_uri`, `LegalEntity.email` |
| `informationURI` | `LegalEntity.info_uri` (emit with `language: en`) |
| `services[].serviceNames` | `EntityServiceDescription` (lang + content) |
| `services[].serviceType` | `EntityEntitlement.entitlement_uri` |
| `services[].status` | same as top-level status |
| `cert.pem` | `TSPCertificate.certificate_pem` via `LegalEntity → trust_service_providers` |
| `pid_key.jwk` / `eaa_key.jwk` | **MISSING — needs new field** |

## Status — two completely separate concepts

`registration_status` (`active`, `pending`, `suspended`, `revoked`) is an **internal
administrative status** — it tracks the registration workflow in ms-registry. It is
NOT the same as the ETSI LoTE trust service status.

ms-registry IS the member state registry. For PID providers, `registration_status`
maps directly to the ETSI status (ignored in output anyway).

For PuB-EAA providers the mapping is less clear:

| Entity type | `registration_status` | ETSI status URI | Written to output? |
|---|---|---|---|
| PID Provider | `active` | `granted` | No (ignored) |
| PuB-EAA Provider | `active` | `notified` (assumption — see below) | Yes |
| PuB-EAA Provider | `revoked` | `withdrawn` | Yes — entry kept permanently |

**NOTE:** It is unclear where the information about `notified`/`withdrawn` status
for PuB-EAA providers comes from in practice — who sets it, when, and through what
process. **Decision (initial implementation):** treat all active PuB-EAA providers
as `notified`. If notification turns out to be a separate explicit step in the
future, a dedicated status field can be added then.

See also `pub_eaa_completion.md` for PuB-EAA specific requirements.

## What tsl_generator contributes

tsl_generator is NOT the primary data source for the export. The registration models
(registry + legal_entities) cover almost everything. The only field tsl_generator
contributes that has no equivalent in the registration models is:

- **`cert.pem`** — digital identity X.509 certificate, stored in `TSPCertificate`
  linked via `LegalEntity → trust_service_providers → certificates`

`TSPName` (multilingual names) is NOT needed — `RegisteredEntity.trade_name` covers
the `names` field. Trade names typically do not change between languages.

`ServiceHistoryInstance` is not currently consumed by the adapter (status history is
a future requirement for PuB-EAA withdrawn entries).

## What is missing

### Public JWK (blocker)
`pid_key.jwk` and `eaa_key.jwk` do not exist anywhere in ms-registry. A new field or
related model is needed on `RegisteredEntity` to store the public JWK of the
credential signing key.

Options:
- Simple: `public_jwk = models.JSONField(null=True, blank=True)` on `RegisteredEntity`
- Structured: a separate `EntityPublicKey` model (allows multiple keys, rotation history)

### Digital identity certificate not linked to registration flow
`TSPCertificate` exists in tsl_generator but is populated manually — it is not part
of the entity registration API flow. The certificate must be uploaded separately and
linked via `TrustServiceProvider → LegalEntity`.

## Lists to generate

| go-trust list | Entitlement filter | Notes |
|---|---|---|
| `pid_providers` | `PID_Provider` | status: active only (no history requirement) |
| `pubeaa_providers` | `PUB_EAA_Provider` | include both active + revoked (withdrawn must be kept) |
