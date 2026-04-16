# Certificates Module Changelog

## 2026-04-16

### Added — WRPAC attribute coverage (CIR (EU) 2025/848 Annex I, ETSI TS 119 411-8 §6.6.1)

**`views.py`**
- `CnfView`: added `friendly_name`, `urls`, and `contact` fields to the cnf JWT payload
  - `friendly_name` → `RegisteredEntity.trade_name` (CIR Annex I pt 2)
  - `urls` → all `EntitySupportURI.support_uri` entries for the entity (CIR Annex I pt 5)
  - `contact.email`, `contact.phone` → `LegalEntity.email` / `.phone` (CIR Annex I pt 7)
- Added `"support_uris"` to `prefetch_related` in `CnfView` and `_get_entity_for_upload`

**`serializers.py`**
- Added `_check_san_contact_info`: validates SAN contains at least one of
  `uniformResourceIdentifier` (website), `rfc822Name` (email), or
  `otherName/id-at-telephoneNumber` (phone) per GEN-6.6.1-07 [CHOICE]
- Added `_TELEPHONE_NUMBER_OID` constant (ITU-T X.520 §6.7.1, OID 2.5.4.20)

**`tests/_cert_builder.py`**
- Added `friendly_name` parameter → subject `CN` (trade name or display name)
- Added `url` parameter → SAN `uniformResourceIdentifier` (derived from primary support URI)
- Added `contact_email` parameter → SAN `rfc822Name` (derived from `LegalEntity.email`)

**`core/management/commands/generate_access_certificates_help_function.py`**
- Reads `friendly_name`, `urls`, and `contact` from cnf payload (newly added fields)
- Uses `friendly_name` for subject `CN` (falls back to `name`)
- Adds `urls[0]` as SAN `uniformResourceIdentifier` and `contact.email` as SAN `rfc822Name`
  to satisfy GEN-6.6.1-07 contact info requirement

### Fixed — alignment with ETSI TS 119 411-8

**`serializers.py`**
- Removed `_check_eku` (checked for `id-kp-clientAuth`): TS 119 411-8 GEN-6.6.1-01 NOTE
  explicitly states WRPACs are not website authentication certificates; the spec mandates
  no specific ExtendedKeyUsage OID
- Removed `_check_subject_cn`: GEN-6.1.1-04 uses "may" — CN is optional, not mandatory
- Removed `_check_san_url` and `_check_san_contact` (enforced URL and email separately):
  replaced by `_check_san_contact_info` which correctly implements GEN-6.6.1-07 as a
  CHOICE (at least one of URL / email / phone, not all required)
- Fixed `_check_key_usage` error message (was referencing spec number in error text)
- Updated `_EUDIWRP_POLICY_OIDS` comment from §5.1 to §5.3 (correct section)

**`tests/_cert_builder.py`**
- Removed `ExtendedKeyUsage([id-kp-clientAuth])` extension from built certificates,
  consistent with EKU check removal above
- Removed unused `ExtendedKeyUsageOID` import

**`core/management/commands/generate_access_certificates_help_function.py`**
- Removed `ExtendedKeyUsage([id-kp-clientAuth])` extension (same reason as above)
- Removed unused `ExtendedKeyUsageOID` import
