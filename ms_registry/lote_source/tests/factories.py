import hashlib
from datetime import datetime, timezone

import factory
from certificates.models import EntitySigningCertificate
from core.models import EntitlementType
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from legal_entities.tests.factories import LegalEntityFactory  # noqa: F401
from registry.models import EntityEntitlement, EntityServiceDescription
from registry.tests.factories import RegisteredEntityFactory

_ISSUER_ENTITLEMENT_TYPES = {
    EntitlementType.PID_PROVIDER,
    EntitlementType.QEAA_PROVIDER,
    EntitlementType.PUB_EAA_PROVIDER,
    EntitlementType.NON_Q_EAA_PROVIDER,
}


def _make_test_cert_pem(cn="test"):
    """Generate a minimal self-signed EC certificate for tests."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime(2024, 1, 1, tzinfo=timezone.utc))
        .not_valid_after(datetime(2030, 1, 1, tzinfo=timezone.utc))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


class PIDProviderFactory(RegisteredEntityFactory):
    """Active PID Provider."""

    trade_name = factory.Sequence(lambda n: f"PID Provider {n}")
    registration_status = "active"
    registry_uri = factory.Sequence(
        lambda n: f"https://registry.example.com/entities/pid-{n}"
    )


class PubEAAProviderFactory(RegisteredEntityFactory):
    """Active PuB-EAA Provider."""

    trade_name = factory.Sequence(lambda n: f"PuB-EAA Provider {n}")
    registration_status = "active"
    registry_uri = factory.Sequence(
        lambda n: f"https://registry.example.com/entities/pubeaa-{n}"
    )


class EntityEntitlementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityEntitlement

    registered_entity = factory.SubFactory(RegisteredEntityFactory)
    entitlement_type = EntitlementType.PID_PROVIDER
    entitlement_uri = "http://uri.etsi.org/19602/SvcType/PIDProvider"
    is_active = True


class EntityServiceDescriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EntityServiceDescription

    registered_entity = factory.SubFactory(RegisteredEntityFactory)
    lang = "en"
    content = factory.Sequence(lambda n: f"Service description {n}")


def add_pid_entitlement(entity):
    return EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.PID_PROVIDER,
        entitlement_uri="http://uri.etsi.org/19602/SvcType/PIDProvider",
    )


def add_pubeaa_entitlement(entity):
    return EntityEntitlementFactory(
        registered_entity=entity,
        entitlement_type=EntitlementType.PUB_EAA_PROVIDER,
        entitlement_uri="http://uri.etsi.org/19602/SvcType/PubEAAProvider",
    )


def add_certificate(entity):
    """
    Create an EntitySigningCertificate for each active issuer entitlement
    the entity currently holds. Tests must call add_*_entitlement() first.
    """
    entitlement_types = list(
        entity.entitlements.filter(
            entitlement_type__in=list(_ISSUER_ENTITLEMENT_TYPES),
        ).values_list("entitlement_type", flat=True)
    )

    certs = []
    for et in entitlement_types:
        pem = _make_test_cert_pem(cn=f"test-{et}")
        cert_obj = x509.load_pem_x509_certificate(pem.encode())
        der = cert_obj.public_bytes(serialization.Encoding.DER)
        certs.append(
            EntitySigningCertificate.objects.create(
                registered_entity=entity,
                entitlement_type=et,
                certificate_pem=pem,
                certificate_serial=format(cert_obj.serial_number, "x").upper(),
                certificate_fingerprint_sha256=hashlib.sha256(der).hexdigest(),
                subject_dn=cert_obj.subject.rfc4514_string(),
                not_before=cert_obj.not_valid_before_utc,
                not_after=cert_obj.not_valid_after_utc,
                is_current=True,
            )
        )
    return certs
