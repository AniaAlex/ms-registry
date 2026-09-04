"""
Prefill helpers for adding a RegisteredEntity to a TSL as a Trust Service.

RegisteredEntity (registry app) already carries the organization identity
(via LegalEntity) and, for issuer entitlements, a current signing certificate
(certificates.EntitySigningCertificate). Rather than re-typing that data into
TrustServiceProviderCreateSerializer / TrustServiceCreateSerializer by hand,
this module derives the form/serializer input from the existing records.
"""

from core.models import EntitlementType

# Non-LoTE entitlements only - the ones actually published in the EUgeneric TL.
# Per ETSI TS 119 412-6 Annex: PID/Wallet/PuB-EAA are published in their own
# LoTE instead (see lote_source.entitlement_eligibility), and QEAA requires a
# QTSP-issued qualified certificate.
ENTITLEMENT_TO_SERVICE_TYPE = {
    EntitlementType.NON_Q_EAA_PROVIDER: (
        "http://uri.etsi.org/TrstSvc/Svctype/Non_Q_EAA_Provider"
    ),
    EntitlementType.QEAA_PROVIDER: "http://uri.etsi.org/TrstSvc/Svctype/QEAA_Provider",
}


def tsl_eligible_entitlement_types(entity):
    """Entitlement types held by this entity that can be published in the TL."""
    held = set(
        entity.entitlements.filter(is_active=True).values_list(
            "entitlement_type", flat=True
        )
    )
    return [et for et in ENTITLEMENT_TO_SERVICE_TYPE if et in held]


def build_trust_service_prefill(entity, entitlement_type):
    """
    Build initial values for TrustServiceCreateSerializer/add_trust_service.html
    from a RegisteredEntity's existing data.

    Does not create anything - the operator still picks the TSL scheme and
    confirms before anything is saved.
    """
    service_type = ENTITLEMENT_TO_SERVICE_TYPE.get(entitlement_type)
    if service_type is None:
        raise ValueError(f"{entitlement_type} is not published in the TL")

    legal_entity = entity.legal_entity
    name = entity.display_name

    certificate_pem = ""
    current_cert = entity.signing_certificates.filter(
        entitlement_type=entitlement_type,
        is_current=True,
        revoked_at__isnull=True,
    ).first()
    if current_cert:
        certificate_pem = current_cert.certificate_pem

    return {
        "legal_entity": legal_entity,
        "provider_name": name,
        "provider_name_language": "en",
        "trade_name": entity.trade_name or "",
        "electronic_address": entity.domain_uri or legal_entity.info_uri or "",
        "service_name": name,
        "service_name_language": "en",
        "service_type": service_type,
        "certificate_pem": certificate_pem,
    }
