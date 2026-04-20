# LOTL (List of Trusted Lists) Structure

## Source

Derived from actual generator code in the [wp4-trust-group repo](https://github.com/webuild-consortium/wp4-trust-group/tree/d99a738abbe4e01c134a66a4ab9011be7abfd34f/tools/lotl):
- `tools/lotl/json_generator.py` — generates the JSON LOTL
- `tools/lotl/xml_generator.py` — generates the XML LOTL (ETSI TS 119 612 v2.4.1)
- `tools/lotl/tl_entry.py` — TLEntry data model
- `tools/lotl/settings.py` — TL type configuration
- `tools/lotl/producer.py` — orchestrates validate → collect → generate → sign → write
- `tools/lotl/collector.py` — scans `tl_entries/` and builds `TLEntry` list

## TL Entry Schema

Each participant file lives at `lotl/tl_entries/{tl_type}/{participant_id}.json`.

| Field | Required | Description |
|-------|----------|-------------|
| `tl_url` | Yes | URL to the TL (JSON or XML) |
| `tl_url_xml` | No | Alternative XML endpoint |
| `tl_url_json` | No | Alternative JSON endpoint |
| `trust_anchor` | Yes | X.509 certificate (PEM) to validate TL signature |
| `metadata` | No | Operator details (e.g. operator_name, country) |

```json
{
  "tl_url": "https://example.com/pid_providers.json",
  "tl_url_xml": "https://example.com/pid_providers.xml",
  "trust_anchor": "-----BEGIN CERTIFICATE-----\nMIIB...\n-----END CERTIFICATE-----",
  "metadata": {
    "operator_name": "Example TLP",
    "country": "IT"
  }
}
```

## LOTL JSON Output (`list_of_trusted_lists.json`)

Structure produced by `generate_lotl_json()`:

```json
{
  "loteTag": "http://uri.etsi.org/19602/LoTETag",
  "schemeInformation": {
    "loteVersionIdentifier": 1,
    "loteSequenceNumber": 1,
    "loteType": "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric",
    "schemeOperatorName": [{ "lang": "en", "value": "WE BUILD WP4 Trust Group" }],
    "schemeOperatorAddress": {
      "postalAddresses": [],
      "electronicAddress": [{ "lang": "en", "uri": "https://webuild-consortium.github.io/wp4-trust-group/" }]
    },
    "schemeName": [{ "lang": "en", "value": "WP4 List of Trusted Lists" }],
    "schemeInformationURI": [{ "lang": "en", "uri": "https://webuild-consortium.github.io/wp4-trust-group/" }],
    "statusDeterminationApproach": "http://uri.etsi.org/TrstSvc/TrustedList/StatusDetn/EUappropriate",
    "schemeTypeCommunityRules": [],
    "schemeTerritory": "EU",
    "listIssueDateTime": "2026-03-26T10:00:00Z",
    "nextUpdate": "2026-09-26T10:00:00Z",
    "distributionPoints": [
      {
        "tlType": "pid-provider",
        "participantId": "example-member-state",
        "tlUrl": "https://example.com/pid_providers.json",
        "tlUrlJson": "https://example.com/pid_providers.json",
        "tlUrlXml": "https://example.com/pid_providers.xml",
        "metadata": {
          "operator_name": "Example TLP",
          "country": "IT"
        }
      }
    ]
  }
}
```

The JSON output is signed with **JAdES Compact Baseline B**.

## LOTL XML Output (`list_of_trusted_lists.xml`)

Follows ETSI TS 119 612 v2.4.1, signed with **XAdES Baseline B**:

```xml
<TrustServiceStatusList ...>
  <SchemeInformation>
    <TSLVersionIdentifier>6</TSLVersionIdentifier>
    <TSLSequenceNumber>1</TSLSequenceNumber>
    <TSLType>http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric</TSLType>
    <SchemeOperatorName>
      <Name xml:lang="en">WE BUILD WP4 Trust Group</Name>
    </SchemeOperatorName>
    <SchemeName>
      <Name xml:lang="en">WP4 List of Trusted Lists</Name>
    </SchemeName>
    <SchemeTerritory>EU</SchemeTerritory>
    <ListIssueDateTime>2026-03-26T10:00:00Z</ListIssueDateTime>
    <NextUpdate>2026-09-26T10:00:00Z</NextUpdate>
    <DistributionPoints>
      <URI>https://example.com/pid_providers.json</URI>
    </DistributionPoints>
  </SchemeInformation>
</TrustServiceStatusList>
```

## Supported TL Types

- `wrpac-provider`
- `wrprc-provider`
- `pub-eaa-provider`
- `pid-provider`
- `qeaa-provider`
- `eaa-provider`
- `wallet-provider`
- `ebwoid-provider`

## Directory Structure

```
lotl/
├── tl_entries/
│   ├── pid-provider/{participant_id}.json
│   ├── wallet-provider/{participant_id}.json
│   └── ...
├── list_of_trusted_lists.json  (JAdES Compact Baseline B signed)
└── list_of_trusted_lists.xml   (XAdES Baseline B signed)
```

## Overall Hierarchy

The LOTL `distributionPoints` is a **flat list** — not nested by member state:

```
LOTL
└── distributionPoints[] (flat)
    ├── { participantId: "ms-a", tlType: "pid-provider",    tlUrl: → MS-A's PID TL }
    ├── { participantId: "ms-a", tlType: "wallet-provider", tlUrl: → MS-A's Wallet TL }
    ├── { participantId: "ms-b", tlType: "pid-provider",    tlUrl: → MS-B's PID TL }
    └── ...

Each individual TL (fetched from tlUrl)
└── lists the actual entities/providers for that participant + type
```

The LOTL maps `(participant_id, tl_type) → TL URL`. The actual member-state → entity relationship lives inside each individual TL.

## LOTE Generation Pipeline

Source: `tools/lotl/producer.py`, `tools/lotl/collector.py`

### Steps performed by `produce()`

1. **Validate** — scans `lotl/tl_entries/` and validates all JSON files against `tl_entry.json` schema
2. **Collect** — `collect_entries()` walks `tl_entries/{tl_type}/*.json`, derives `participant_id` from the filename stem, loads each into a `TLEntry`
3. **Sequence number** — reads existing `list_of_trusted_lists.json` (or XML) and increments `loteSequenceNumber`; defaults to 1 if no prior file exists
4. **Generate (unsigned)** — calls `generate_lotl_json()` and `generate_lotl_xml()` with the collected entries
5. **Sign** — `sign_json()` (JAdES Compact Baseline B) and `sign_xml()` (XAdES Baseline B)
6. **Write** — outputs `lotl/list_of_trusted_lists.json` and `lotl/list_of_trusted_lists.xml`

### Collector logic (`collector.py`)

```
tl_entries/
├── pid-provider/
│   └── italy.json        → TLEntry(tl_type="pid-provider", participant_id="italy", ...)
├── wallet-provider/
│   └── germany.json      → TLEntry(tl_type="wallet-provider", participant_id="germany", ...)
```

- Directory name → `tl_type`
- JSON filename stem → `participant_id`
- Skips directories not in `VALID_TL_TYPES`
- Raises `ValueError` on missing `tl_url` or `trust_anchor`

### Entry grouping

`iter_entries_by_type()` groups entries by `tl_type` (sorted), used for building the `distributionPoints` in the LOTL.

### `produce()` signature

```python
produce(
    tl_entries_dir,   # path to lotl/tl_entries/
    output_dir,       # path to lotl/
    signing_key,      # PEM private key (or path)
    signing_cert,     # PEM certificate (or path)
    validate_only,    # if True: validate only, no output written
) -> int              # 0 = success
```

## CI Validation

Before a PR merges, the CI workflow:
1. Fetches the TL from `tl_url`
2. Validates the signature using `trust_anchor`
3. Validates against ETSI schema

Published every 6 months with an incrementing `loteSequenceNumber`.
