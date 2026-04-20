# Identity Proofing: Natural Person vs Legal Person (Sweden)

**Date**: 2026-03-10
**Context**: ms-registry — precondition for WRPAC issuance (CA_usecases_20260310.md, line 55)

---

## Current Model State

Identity proofing outcome is stored across:
- `NaturalPerson` — given_name, family_name, date_of_birth, nationality
- `LegalPerson` — legal_name, legal_form, registration_date
- `Identifier` — identifier_type + identifier_value (CIR Annex I(2) types)
- `LegalEntity` — wrapper with entity_type = NATURAL_PERSON | LEGAL_PERSON

**Gap**: no record of *how* or *when* identity was proofed, or at what assurance level.

---

## Natural Person — BankID+

### Identifier type
`SERIAL_NUMBER` — Swedish personnummer (or eIDAS PID unique identifier)

### Proofing mechanism
BankID+ via OIDC flow. Returns verified claims:
- `given_name`, `family_name`, `birthdate`
- `personal_identifier` (personnummer)
- Level of assurance: eIDAS HIGH

### Automation flow
```
RP (natural person) visits registration portal
    │
    │── Clicks "Verify with BankID+"
    │── Redirected to BankID+ OIDC flow
    │── Returns with verified claims:
    │       given_name, family_name, date_of_birth,
    │       personal_identifier (personnummer or eIDAS PID)
    │
    ▼
Registry auto-populates:
    NaturalPerson   ← given_name, family_name, date_of_birth
    Identifier      ← SERIAL_NUMBER = <personnummer>
    LegalEntity     ← entity_type = NATURAL_PERSON
    IdentityProofing (missing) ← method=BankID+, loa=HIGH, timestamp, token_ref
```

---

## Legal Person — Bolagsverket

### Identifier type
`NATIONAL_BUSINESS_REG` — Swedish organisationsnummer (format: `556XXX-XXXX`)
Issued by: **Bolagsverket** (Swedish Companies Registration Office)

### Proofing mechanism
Bolagsverket API lookup (or BRIS — Business Register Interconnection System for EU cross-border).
Returns verified data:
- `legal_name`
- `legal_form` (AB, HB, KB, etc.)
- `registration_date`
- `registered_address`
- `status` (active / dissolved)

### Automation flow
```
RP (legal person) enters organisationsnummer in portal
    │
    │── Registry calls Bolagsverket API
    │── Returns verified:
    │       legal_name, legal_form, registration_date,
    │       registered_address, status=active
    │
    ▼
Registry auto-populates:
    LegalPerson     ← legal_name, legal_form, registration_date
    Identifier      ← NATIONAL_BUSINESS_REG = "556XXX-XXXX"
    PhysicalAddress ← registered_address from Bolagsverket
    LegalEntity     ← entity_type = LEGAL_PERSON
    IdentityProofing (missing) ← method=Bolagsverket_API, timestamp, source_ref
```

### Representative authorisation
Bolagsverket proves the organisation exists and is active, but does **not** prove the
person acting on behalf of the organisation is authorised. The authorised signatory
(firmatecknare) must be verified separately — typically also via **BankID+**, by
checking the signatory's personnummer against the Bolagsverket firmatecknare record.

---

## Missing Model: IdentityProofing

To support automated proofing and satisfy ETSI TS 119 475 assurance requirements,
a new model is needed:

```python
class IdentityProofing(BaseModel):
    legal_entity = models.ForeignKey(LegalEntity, on_delete=models.CASCADE)
    method = models.CharField(max_length=100)
    # e.g. "BankID_Plus", "Bolagsverket_API", "Manual"
    loa = models.CharField(max_length=50, blank=True, null=True)
    # e.g. "eIDAS_HIGH", "eIDAS_SUBSTANTIAL"
    proofing_timestamp = models.DateTimeField()
    proofing_authority = models.CharField(max_length=200, blank=True, null=True)
    # e.g. "Bolagsverket", "BankID AB"
    token_reference = models.CharField(max_length=500, blank=True, null=True)
    # OIDC sub or assertion ID for audit trail
```

---

## Summary

| | Natural Person | Legal Person |
|---|---|---|
| Swedish identifier | personnummer | organisationsnummer |
| `IdentifierType` | `SERIAL_NUMBER` | `NATIONAL_BUSINESS_REG` |
| Proofing mechanism | BankID+ (OIDC) | Bolagsverket API |
| Assurance level | eIDAS HIGH | Registration lookup |
| Representative check | N/A | BankID+ for firmatecknare |
| Cross-border | eIDAS PID | BRIS |
