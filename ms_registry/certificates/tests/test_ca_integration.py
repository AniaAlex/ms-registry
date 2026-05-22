"""
Unit tests for certificates/ca_integration.py.

Tests the building-block functions directly without a real CA.
issue_access_certificate (CA signing) is covered in test_issue.py.
"""

import pytest
from certificates.ca_integration import (
    POLICY_OIDS,
    CertificateIssuanceError,
    build_san_from_entity,
    build_subject_from_entity,
    format_org_identifier,
    get_entity_for_issuance,
    get_policy_oid,
    revoke_entity_certificates,
    validate_csr_subject,
)
from certificates.models import EntityAccessCertificate
from core.models import Identifier, RegistrationStatus
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from django.utils import timezone
from legal_entities.models import (
    LegalEntity,
    NaturalPerson,
    PhysicalAddress,
)
from registry.tests.factories import (
    EntitySupportURIFactory,
    RegisteredEntityFactory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OID_MAP = {
    "C": x509.NameOID.COUNTRY_NAME,
    "O": x509.NameOID.ORGANIZATION_NAME,
    "CN": x509.NameOID.COMMON_NAME,
    "GN": x509.NameOID.GIVEN_NAME,
    "SN": x509.NameOID.SURNAME,
    "serialNumber": x509.NameOID.SERIAL_NUMBER,
    "organizationIdentifier": x509.ObjectIdentifier("2.5.4.97"),
}


def _make_csr(subject_attrs: dict) -> x509.CertificateSigningRequest:
    key = ec.generate_private_key(ec.SECP256R1())
    attrs = [x509.NameAttribute(_OID_MAP[k], v) for k, v in subject_attrs.items()]
    return (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name(attrs))
        .sign(key, hashes.SHA256())
    )


def _attach_identifier(
    legal_entity, identifier_type="VAT_NUMBER", value="12345", country="SE"
):
    ident = Identifier.objects.create(
        identifier_type=identifier_type,
        identifier_value=value,
        country_code=country,
    )
    legal_entity.primary_identifier = ident
    legal_entity.save()
    return ident


def _make_natural_person_entity(**kwargs):
    np = NaturalPerson.objects.create(given_name="Anna", family_name="Smith")
    le = LegalEntity.objects.create(
        entity_type="natural_person",
        natural_person=np,
        physical_address=PhysicalAddress.objects.create(country_code="DE"),
        email="anna@example.com",
    )
    from registry.models import SupervisoryAuthority

    sa = SupervisoryAuthority.objects.create(
        authority_name="DPA",
        country_code="DE",
        email="dpa@example.de",
    )
    from core.models import EntityRole
    from registry.models import RegisteredEntity

    entity = RegisteredEntity.objects.create(
        legal_entity=le,
        entity_role=EntityRole.PID_PROVIDER,
        supervisory_authority=sa,
        **kwargs,
    )
    return entity


def _make_cert_record(entity, *, is_current=True, revoked=False):
    now = timezone.now()
    return EntityAccessCertificate.objects.create(
        registered_entity=entity,
        certificate_serial=f"AA{entity.pk}",
        certificate_fingerprint_sha256="a" * 64,
        issuer_dn="CN=Test CA",
        subject_dn="CN=Test",
        not_before=now,
        not_after=now,
        is_current=is_current,
        revoked_at=now if revoked else None,
        certificate_pem=(
            "-----BEGIN CERTIFICATE-----\nZmFrZQ==\n-----END CERTIFICATE-----\n"
        ),
    )


# ---------------------------------------------------------------------------
# format_org_identifier
# ---------------------------------------------------------------------------


def test_format_org_identifier_vat():
    assert format_org_identifier("123456", "VAT_NUMBER", "SE") == "VATSE-123456"


def test_format_org_identifier_ntr():
    assert format_org_identifier("789", "NATIONAL_BUSINESS_REG", "DE") == "NTRDE-789"


def test_format_org_identifier_lei_uses_xg():
    result = format_org_identifier("ABC123", "LEI", "SE")
    assert result == "LEIXG-ABC123"


def test_format_org_identifier_unknown_type_falls_back_to_oth():
    assert format_org_identifier("999", "MYSTERY", "FR") == "OTHFR-999"


def test_format_org_identifier_strips_internal_dash():
    # Swedish org numbers are stored with a dash (e.g. "202100-5448")
    assert (
        format_org_identifier("202100-5448", "NATIONAL_BUSINESS_REG", "SE")
        == "NTRSE-2021005448"
    )


def test_format_org_identifier_strips_spaces():
    assert format_org_identifier("123 456", "VAT_NUMBER", "SE") == "VATSE-123456"


def test_format_org_identifier_lei_strips_dash_and_uses_xg():
    assert format_org_identifier("ABC-123", "LEI", "SE") == "LEIXG-ABC123"


# ---------------------------------------------------------------------------
# build_subject_from_entity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_build_subject_legal_person_with_identifier():
    entity = RegisteredEntityFactory()
    _attach_identifier(
        entity.legal_entity, identifier_type="VAT_NUMBER", value="V001", country="SE"
    )

    subject = build_subject_from_entity(entity)

    assert subject["C"] == "SE"
    assert "O" in subject
    assert "CN" in subject
    assert subject["organizationIdentifier"] == "VATSE-V001"


@pytest.mark.django_db
def test_build_subject_legal_person_without_identifier():
    entity = RegisteredEntityFactory()
    entity.legal_entity.primary_identifier = None
    entity.legal_entity.save()

    subject = build_subject_from_entity(entity)

    assert "organizationIdentifier" not in subject
    assert "C" in subject
    assert "CN" in subject


@pytest.mark.django_db
def test_build_subject_uses_identifier_country():
    entity = RegisteredEntityFactory()
    _attach_identifier(
        entity.legal_entity, identifier_type="VAT_NUMBER", value="V002", country="FI"
    )

    subject = build_subject_from_entity(entity)

    assert subject["C"] == "FI"


@pytest.mark.django_db
def test_build_subject_falls_back_to_address_country():
    entity = RegisteredEntityFactory()
    entity.legal_entity.primary_identifier = None
    entity.legal_entity.save()
    entity.legal_entity.physical_address.country_code = "NO"
    entity.legal_entity.physical_address.save()

    subject = build_subject_from_entity(entity)

    assert subject["C"] == "NO"


@pytest.mark.django_db
def test_build_subject_defaults_to_xx_when_no_country():
    entity = RegisteredEntityFactory()
    entity.legal_entity.primary_identifier = None
    entity.legal_entity.physical_address = None
    entity.legal_entity.save()

    subject = build_subject_from_entity(entity)

    assert subject["C"] == "XX"


@pytest.mark.django_db
def test_build_subject_natural_person():
    entity = _make_natural_person_entity()
    ident = Identifier.objects.create(
        identifier_type="SERIAL_NUMBER",
        identifier_value="PNR001",
        country_code="DE",
    )
    entity.legal_entity.primary_identifier = ident
    entity.legal_entity.save()

    subject = build_subject_from_entity(entity)

    assert subject["GN"] == "Anna"
    assert subject["SN"] == "Smith"
    assert "CN" in subject
    assert "serialNumber" in subject
    assert "O" not in subject
    assert "organizationIdentifier" not in subject


# ---------------------------------------------------------------------------
# validate_csr_subject
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validate_csr_subject_valid():
    entity = RegisteredEntityFactory()
    _attach_identifier(
        entity.legal_entity, identifier_type="VAT_NUMBER", value="V003", country="SE"
    )

    legal_name = entity.legal_entity.legal_person.legal_name
    csr = _make_csr(
        {
            "C": "SE",
            "O": legal_name,
            "CN": entity.trade_name or legal_name,
            "organizationIdentifier": "VATSE-V003",
        }
    )

    errors = validate_csr_subject(csr, entity)
    assert errors == []


@pytest.mark.django_db
def test_validate_csr_subject_country_mismatch():
    entity = RegisteredEntityFactory()
    _attach_identifier(
        entity.legal_entity, identifier_type="VAT_NUMBER", value="V004", country="SE"
    )

    csr = _make_csr({"C": "DE", "CN": "X"})
    errors = validate_csr_subject(csr, entity)

    assert any("Country mismatch" in e for e in errors)


@pytest.mark.django_db
def test_validate_csr_subject_org_mismatch():
    entity = RegisteredEntityFactory()
    _attach_identifier(
        entity.legal_entity, identifier_type="VAT_NUMBER", value="V005", country="SE"
    )

    csr = _make_csr({"C": "SE", "O": "WrongOrg", "CN": "X"})
    errors = validate_csr_subject(csr, entity)

    assert any("Organization mismatch" in e for e in errors)


@pytest.mark.django_db
def test_validate_csr_subject_org_id_mismatch():
    entity = RegisteredEntityFactory()
    _attach_identifier(
        entity.legal_entity, identifier_type="VAT_NUMBER", value="V006", country="SE"
    )

    legal_name = entity.legal_entity.legal_person.legal_name
    csr = _make_csr(
        {
            "C": "SE",
            "O": legal_name,
            "CN": "X",
            "organizationIdentifier": "VATSE-WRONG",
        }
    )
    errors = validate_csr_subject(csr, entity)

    assert any("organizationIdentifier mismatch" in e for e in errors)


@pytest.mark.django_db
def test_validate_csr_subject_org_id_case_insensitive():
    entity = RegisteredEntityFactory()
    _attach_identifier(
        entity.legal_entity, identifier_type="VAT_NUMBER", value="V007", country="SE"
    )

    legal_name = entity.legal_entity.legal_person.legal_name
    csr = _make_csr(
        {
            "C": "SE",
            "O": legal_name,
            "CN": "X",
            "organizationIdentifier": "vatse-v007",  # lowercase
        }
    )
    errors = validate_csr_subject(csr, entity)

    assert not any("organizationIdentifier" in e for e in errors)


@pytest.mark.django_db
def test_validate_csr_subject_serial_number_mismatch_natural_person():
    entity = _make_natural_person_entity()
    ident = Identifier.objects.create(
        identifier_type="SERIAL_NUMBER",
        identifier_value="PNR002",
        country_code="DE",
    )
    entity.legal_entity.primary_identifier = ident
    entity.legal_entity.save()

    csr = _make_csr(
        {
            "C": "DE",
            "GN": "Anna",
            "SN": "Smith",
            "CN": "Anna",
            "serialNumber": "PASDE-WRONG",
        }
    )
    errors = validate_csr_subject(csr, entity)

    assert any("serialNumber mismatch" in e for e in errors)


# ---------------------------------------------------------------------------
# build_san_from_entity
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_build_san_includes_registry_uri():
    entity = RegisteredEntityFactory(registry_uri="https://registry.example.com/e/1")
    entity.legal_entity.email = None
    entity.legal_entity.save()

    san = build_san_from_entity(entity)

    uris = [e for e in san if isinstance(e, x509.UniformResourceIdentifier)]
    assert any(u.value == "https://registry.example.com/e/1" for u in uris)


@pytest.mark.django_db
def test_build_san_includes_email():
    entity = RegisteredEntityFactory()
    entity.legal_entity.email = "contact@example.com"
    entity.legal_entity.save()

    san = build_san_from_entity(entity)

    emails = [e for e in san if isinstance(e, x509.RFC822Name)]
    assert any(e.value == "contact@example.com" for e in emails)


@pytest.mark.django_db
def test_build_san_includes_phone_as_othername():
    entity = RegisteredEntityFactory()
    entity.legal_entity.phone = "+46701234567"
    entity.legal_entity.save()

    san = build_san_from_entity(entity)

    other_names = [e for e in san if isinstance(e, x509.OtherName)]
    assert len(other_names) == 1
    assert other_names[0].type_id.dotted_string == "2.5.4.20"


@pytest.mark.django_db
def test_build_san_includes_support_uris():
    entity = RegisteredEntityFactory(registry_uri="")
    entity.legal_entity.email = None
    entity.legal_entity.save()
    EntitySupportURIFactory(
        registered_entity=entity, support_uri="https://help.example.com"
    )

    san = build_san_from_entity(entity)

    uris = [e for e in san if isinstance(e, x509.UniformResourceIdentifier)]
    assert any(u.value == "https://help.example.com" for u in uris)


@pytest.mark.django_db
def test_build_san_empty_when_no_contact():
    entity = RegisteredEntityFactory(registry_uri="")
    entity.legal_entity.email = None
    entity.legal_entity.phone = None
    entity.legal_entity.save()

    san = build_san_from_entity(entity)

    assert san == []


@pytest.mark.django_db
def test_build_san_phone_utf8_encoded():
    entity = RegisteredEntityFactory()
    entity.legal_entity.phone = "+46"
    entity.legal_entity.save()

    san = build_san_from_entity(entity)
    other = next(e for e in san if isinstance(e, x509.OtherName))

    # DER: 0x0C (UTF8String tag) + length + UTF-8 bytes
    expected = b"\x0c\x03+46"
    assert other.value == expected


# ---------------------------------------------------------------------------
# get_policy_oid
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_policy_oid_legal_person():
    entity = RegisteredEntityFactory()
    assert get_policy_oid(entity) == POLICY_OIDS["NCP-l-eudiwrp"]


@pytest.mark.django_db
def test_get_policy_oid_natural_person():
    entity = _make_natural_person_entity()
    assert get_policy_oid(entity) == POLICY_OIDS["NCP-n-eudiwrp"]


# ---------------------------------------------------------------------------
# get_entity_for_issuance
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_entity_for_issuance_not_found():
    import uuid

    with pytest.raises(Exception):  # DoesNotExist
        get_entity_for_issuance(str(uuid.uuid4()))


@pytest.mark.django_db
def test_get_entity_for_issuance_pending_raises_409():
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.PENDING)

    with pytest.raises(CertificateIssuanceError) as exc_info:
        get_entity_for_issuance(str(entity.id))

    assert exc_info.value.http_status == 409


@pytest.mark.django_db
def test_get_entity_for_issuance_suspended_raises_409():
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.SUSPENDED)

    with pytest.raises(CertificateIssuanceError) as exc_info:
        get_entity_for_issuance(str(entity.id))

    assert exc_info.value.http_status == 409


@pytest.mark.django_db
def test_get_entity_for_issuance_no_contact_raises_400():
    entity = RegisteredEntityFactory(
        registration_status=RegistrationStatus.ACTIVE,
        registry_uri="",
    )
    entity.legal_entity.email = None
    entity.legal_entity.phone = None
    entity.legal_entity.save()

    with pytest.raises(CertificateIssuanceError) as exc_info:
        get_entity_for_issuance(str(entity.id))

    assert exc_info.value.http_status == 400


@pytest.mark.django_db
def test_get_entity_for_issuance_active_with_email_succeeds():
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.ACTIVE)
    entity.legal_entity.email = "contact@example.com"
    entity.legal_entity.save()

    result = get_entity_for_issuance(str(entity.id))

    assert result.id == entity.id


@pytest.mark.django_db
def test_get_entity_for_issuance_active_with_registry_uri_succeeds():
    entity = RegisteredEntityFactory(
        registration_status=RegistrationStatus.ACTIVE,
        registry_uri="https://registry.example.com/e/99",
    )
    entity.legal_entity.email = None
    entity.legal_entity.save()

    result = get_entity_for_issuance(str(entity.id))

    assert result.id == entity.id


@pytest.mark.django_db
def test_get_entity_for_issuance_active_with_support_uri_succeeds():
    entity = RegisteredEntityFactory(
        registration_status=RegistrationStatus.ACTIVE,
        registry_uri="",
    )
    entity.legal_entity.email = None
    entity.legal_entity.save()
    EntitySupportURIFactory(registered_entity=entity)

    result = get_entity_for_issuance(str(entity.id))

    assert result.id == entity.id


# ---------------------------------------------------------------------------
# revoke_entity_certificates
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_revoke_marks_current_certs_revoked():
    entity = RegisteredEntityFactory()
    cert = _make_cert_record(entity, is_current=True)

    count = revoke_entity_certificates(entity, reason="cessationOfOperation")

    assert count == 1
    cert.refresh_from_db()
    assert cert.revoked_at is not None
    assert cert.revocation_reason == "cessationOfOperation"


@pytest.mark.django_db
def test_revoke_skips_already_revoked():
    entity = RegisteredEntityFactory()
    _make_cert_record(entity, is_current=True, revoked=True)

    count = revoke_entity_certificates(entity)

    assert count == 0


@pytest.mark.django_db
def test_revoke_skips_non_current_certs():
    entity = RegisteredEntityFactory()
    _make_cert_record(entity, is_current=False)

    count = revoke_entity_certificates(entity)

    assert count == 0


@pytest.mark.django_db
def test_revoke_returns_count_of_revoked():
    entity = RegisteredEntityFactory()
    # Two current certs, one already revoked
    _make_cert_record(entity, is_current=True)
    _make_cert_record(entity, is_current=True)
    _make_cert_record(entity, is_current=True, revoked=True)

    count = revoke_entity_certificates(entity)

    assert count == 2


@pytest.mark.django_db
def test_revoke_sets_custom_reason():
    entity = RegisteredEntityFactory()
    cert = _make_cert_record(entity)

    revoke_entity_certificates(entity, reason="certificateHold")

    cert.refresh_from_db()
    assert cert.revocation_reason == "certificateHold"
