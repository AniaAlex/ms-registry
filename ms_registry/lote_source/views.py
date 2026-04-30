"""
LoTE source views — ETSI TS 119 602 unsigned JSON for g119612 (tsl-tool).

These two endpoints serve unsigned LoTE documents that are consumed by the
docker-siros-lote container running tsl-tool (g119612). tsl-tool fetches the
JSON, validates it, signs it with JAdES-B-B, and writes:

  /var/www/html/lote/pid_providers/
      pid_providers.json          (unsigned)
      pid_providers.json.jws      (JAdES-B-B compact signature)
      pid_providers.xml           (XML representation)

  /var/www/html/lote/pubeaa_providers/
      pubeaa_providers.json
      pubeaa_providers.json.jws
      pubeaa_providers.xml

nginx serves these files publicly.

IMPORTANT — Member State notification requirement
-------------------------------------------------
Both PID Providers and PuB-EAA Providers must be formally notified to the
Member State Registry before they may appear in the respective LoTE. This is
a legal/regulatory step separate from the technical registration workflow.

Until a dedicated notification workflow is implemented, "active" registration
status is used as the operational proxy for "notified". When the notification
step is added (e.g. a Supervisory Authority explicitly marks an entity as
notified), the queryset filter here should be updated accordingly.

Data sources
------------
This app intentionally collects data from across ms-registry:
  - registry.RegisteredEntity    — trade name, registry URI, status
  - registry.EntityServiceDescription — multilingual service names
  - legal_entities.LegalEntity   — postal address, info URI, e-mail
  - tsl_generator.TSPCertificate — digital identity certificate (PEM/DER)
    (populated manually via Django admin until a dedicated digital-identity
     module is added to the registration flow)

Missing data that will cause warnings in tsl-tool output:
  - X.509 certificate: only present if TSPCertificate is loaded via admin
  - Public JWK (pid_key.jwk / eaa_key.jwk): not stored in ms-registry yet

Configure via Django settings (all optional):
  LOTE_OPERATOR_NAME    default "WP4Trust Registry"
  LOTE_TERRITORY        default "EU"
  LOTE_SEQUENCE_NUMBER  default 1
  LOTE_PUBLIC_BASE_URL  default "http://localhost"
                        Set to the public HTTPS URL of your nginx server so
                        DistributionPoints in the LoTE reflects the real URL
                        where signed files are served.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from registry.models import RegisteredEntity
from rest_framework.response import Response
from rest_framework.views import APIView

# ---------------------------------------------------------------------------
# ETSI TS 119 602 URI constants
# ---------------------------------------------------------------------------

_LOTE_TYPE_PID = "http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList"
_LOTE_TYPE_PUBEAA = "http://uri.etsi.org/19602/LoTEType/EUPubEAAProvidersList"

_SVC_TYPE_PID = "http://uri.etsi.org/19602/SvcType/PIDProvider"
_SVC_TYPE_PUBEAA = "http://uri.etsi.org/19602/SvcType/PubEAAProvider"

# PuB-EAA ServiceStatus values (PID profile must NOT have ServiceStatus)
_STATUS_GRANTED = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted"
_STATUS_WITHDRAWN = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/withdrawn"

_LOTE_VERSION = 1
_NEXT_UPDATE_DAYS = 180


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _dist_url(path):
    base = getattr(settings, "LOTE_PUBLIC_BASE_URL", "").rstrip("/")
    return f"{base or 'http://localhost'}{path}"


def _operator_name():
    return getattr(settings, "LOTE_OPERATOR_NAME", "WP4Trust Registry")


def _territory():
    return getattr(settings, "LOTE_TERRITORY", "EU")


def _sequence_number():
    return getattr(settings, "LOTE_SEQUENCE_NUMBER", 1)


def _names(entity):
    """Multilingual names from EntityServiceDescription, falling back to trade_name."""
    descriptions = list(entity.service_descriptions.all())
    if descriptions:
        return [{"lang": d.lang, "value": d.content} for d in descriptions]
    return [{"lang": "en", "value": entity.trade_name or entity.display_name}]


def _te_address(le):
    """
    TEAddress from LegalEntity postal address and contact details.
    Always returns the dict (never None) — TEAddress null fails g119612 validation.
    """
    postal = []
    try:
        addr = le.physical_address
        if addr:
            postal.append(
                {
                    "lang": "",
                    "StreetAddress": addr.street_address or "",
                    "Locality": addr.locality or "",
                    "PostalCode": addr.postal_code or "",
                    "Country": addr.country_code or "",
                }
            )
    except Exception:
        pass

    electronic = []
    if getattr(le, "info_uri", None):
        electronic.append({"lang": "", "uriValue": le.info_uri})
    if getattr(le, "email", None):
        electronic.append({"lang": "", "uriValue": f"mailto:{le.email}"})

    return {
        "TEPostalAddress": postal,
        "TEElectronicAddress": electronic,
    }


def _te_info_uri(le, entity):
    """
    TEInformationURI — required non-empty by g119612 validation.
    Prefers LegalEntity.info_uri; falls back to RegisteredEntity.registry_uri.
    """
    if getattr(le, "info_uri", None):
        return [{"lang": "en", "uriValue": le.info_uri}]
    if entity.registry_uri:
        return [{"lang": "en", "uriValue": entity.registry_uri}]
    return []


def _service_digital_identity(entity):
    """
    X.509 certificate from tsl_generator ServiceCertificate (base64 DER).

    Path: LegalEntity → TrustServiceProvider → TrustService → ServiceCertificate.

    Returns a non-empty ServiceDigitalIdentity dict, or None if no certificate
    is found. Callers must exclude entities that return None — an empty
    ServiceDigitalIdentity is invalid per ETSI TS 119 602: relying parties have
    no way to verify the entity's identity without a certificate.

    Certificates are currently populated manually via Django admin through the
    tsl_generator app. A dedicated digital-identity module will replace this
    once it is added to the registration flow.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        for tsp in entity.legal_entity.trust_service_providers.all():
            if not tsp.is_active:
                continue
            for svc in tsp.services.all():
                if not svc.is_active:
                    continue
                for cert in svc.certificates.all():
                    b64 = cert.get_base64_der()
                    if not b64:
                        continue
                    sdi = {"X509Certificates": [{"val": b64}]}
                    if cert.x509_subject_name:
                        sdi["X509SubjectNames"] = [cert.x509_subject_name]
                    if cert.x509_ski:
                        sdi["X509SKIs"] = [cert.x509_ski]
                    return sdi
    except Exception:
        logger.exception(
            "LoTE: error reading digital identity for %s (%s) — excluded from LoTE",
            entity.display_name,
            entity.pk,
        )
        return None

    logger.warning(
        "LoTE: no ServiceCertificate found for %s (%s) — excluded from LoTE",
        entity.display_name,
        entity.pk,
    )
    return None


def _build_entity(entity, service_type, service_status=None):
    """
    Build a TrustedEntity dict for the LoTE, or return None if the entity
    has no digital identity (excluded from output per ETSI TS 119 602).
    """
    sdi = _service_digital_identity(entity)
    if sdi is None:
        return None

    le = entity.legal_entity
    names = _names(entity)
    svc_info = {
        "ServiceName": names,
        "ServiceDigitalIdentity": sdi,
        "ServiceTypeIdentifier": service_type,
    }
    # ServiceStatus: required for PuB-EAA, must be absent for PID
    if service_status is not None:
        svc_info["ServiceStatus"] = service_status

    return {
        "TrustedEntityInformation": {
            "TEName": names,
            "TEAddress": _te_address(le),
            "TEInformationURI": _te_info_uri(le, entity),
        },
        "TrustedEntityServices": [{"ServiceInformation": svc_info}],
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class LOTEPIDProvidersView(APIView):
    """
    GET /lote-source/pid-providers/

    Unsigned PID Providers LoTE (ETSI TS 119 602).

    NOTE: Entities here must be formally notified to the Member State Registry
    as PID Providers. Until a notification workflow exists, active registration
    status acts as the proxy for notification.

    PID LoTE rule (g119612 validate.go): ServiceStatus MUST be absent.
    Presence of ServiceStatus = trusted per the ETSI spec, so the field must
    not appear at all in PID profile output.
    """

    permission_classes = []
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        now = timezone.now()

        entities = (
            RegisteredEntity.objects.filter(
                registration_status="active",
                entitlements__entitlement_type="PID_Provider",
            )
            .distinct()
            .select_related("legal_entity__physical_address")
            .prefetch_related(
                "service_descriptions",
                "legal_entity__trust_service_providers__services__certificates",
            )
        )

        lote = {
            "LoTE": {
                "ListAndSchemeInformation": {
                    "LoTEVersionIdentifier": _LOTE_VERSION,
                    "LoTESequenceNumber": _sequence_number(),
                    "LoTEType": _LOTE_TYPE_PID,
                    "SchemeOperatorName": [{"lang": "en", "value": _operator_name()}],
                    "SchemeName": [{"lang": "en", "value": "EU PID Providers List"}],
                    "SchemeTerritory": _territory(),
                    "ListIssueDateTime": _iso(now),
                    "NextUpdate": _iso(now + timedelta(days=_NEXT_UPDATE_DAYS)),
                    "DistributionPoints": [
                        _dist_url("/lote/pid_providers/pid_providers.json")
                    ],
                },
                "TrustedEntitiesList": [
                    entry
                    for e in entities
                    if (entry := _build_entity(e, _SVC_TYPE_PID)) is not None
                ],
            }
        }
        return Response(lote)


class LOTEPubEAAProvidersView(APIView):
    """
    GET /lote-source/pubeaa-providers/

    Unsigned PuB-EAA Providers LoTE (ETSI TS 119 602).

    NOTE: Entities here must be formally notified to the Member State Registry
    as PuB-EAA Providers. Until a notification workflow exists, active
    registration status acts as the proxy for notification. Revoked entities
    remain permanently (as withdrawn) so relying parties can verify past
    attestations.

    PuB-EAA LoTE rule (g119612 validate.go): ServiceStatus REQUIRED.
    active → granted, revoked → withdrawn.
    """

    permission_classes = []
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        now = timezone.now()

        entities = (
            RegisteredEntity.objects.filter(
                registration_status__in=["active", "revoked"],
                entitlements__entitlement_type="PUB_EAA_Provider",
            )
            .distinct()
            .select_related("legal_entity__physical_address")
            .prefetch_related(
                "service_descriptions",
                "legal_entity__trust_service_providers__services__certificates",
            )
        )

        def pubeaa_status(entity):
            return (
                _STATUS_GRANTED
                if entity.registration_status == "active"
                else _STATUS_WITHDRAWN
            )

        lote = {
            "LoTE": {
                "ListAndSchemeInformation": {
                    "LoTEVersionIdentifier": _LOTE_VERSION,
                    "LoTESequenceNumber": _sequence_number(),
                    "LoTEType": _LOTE_TYPE_PUBEAA,
                    "SchemeOperatorName": [{"lang": "en", "value": _operator_name()}],
                    "SchemeName": [
                        {"lang": "en", "value": "EU Pub-EAA Providers List"}
                    ],
                    "SchemeTerritory": _territory(),
                    "ListIssueDateTime": _iso(now),
                    "NextUpdate": _iso(now + timedelta(days=_NEXT_UPDATE_DAYS)),
                    "DistributionPoints": [
                        _dist_url("/lote/pubeaa_providers/pubeaa_providers.json")
                    ],
                },
                "TrustedEntitiesList": [
                    entry
                    for e in entities
                    if (
                        entry := _build_entity(
                            e, _SVC_TYPE_PUBEAA, service_status=pubeaa_status(e)
                        )
                    )
                    is not None
                ],
            }
        }
        return Response(lote)
