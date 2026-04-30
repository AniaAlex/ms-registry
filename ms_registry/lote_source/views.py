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

JSON format matches etsi119602.ListOfTrustedEntities Go struct (g119612):
  - top level: version, schemeInformation, trustedEntities
  - LangString fields use "language" (not "lang")
  - digitalIdentities use {"type": "x509", "x509Certificate": "<base64-DER>"}

IMPORTANT — Member State notification requirement
-------------------------------------------------
Both PID Providers and PuB-EAA Providers must be formally notified to the
Member State Registry before they may appear in the respective LoTE. This is
a legal/regulatory step separate from the technical registration workflow.

Until a dedicated notification workflow is implemented, "active" registration
status is used as the operational proxy for "notified". When the notification
step is added (e.g. a Supervisory Authority explicitly marks an entity as
notified), the queryset filter here should be updated accordingly.

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

_STATUS_GRANTED = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted"
_STATUS_WITHDRAWN = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/withdrawn"

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
    """NameSet (list of {language, value}) from EntityServiceDescription."""
    descriptions = list(entity.service_descriptions.all())
    if descriptions:
        return [{"language": d.lang, "value": d.content} for d in descriptions]
    return [{"language": "en", "value": entity.trade_name or entity.display_name}]


def _digital_identities(entity):
    """
    X.509 certificate from tsl_generator ServiceCertificate (base64 DER).
    Returns list of DigitalIdentity dicts, or empty list if none found.
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
                    di = {"type": "x509", "x509Certificate": b64}
                    if cert.x509_subject_name:
                        di["x509SubjectName"] = cert.x509_subject_name
                    return [di]
    except Exception:
        logger.exception(
            "LoTE: error reading digital identity for %s (%s)",
            entity.display_name,
            entity.pk,
        )

    logger.warning(
        "LoTE: no ServiceCertificate found for %s (%s) — excluded from LoTE",
        entity.display_name,
        entity.pk,
    )
    return []


def _info_uris(entity):
    """informationURIs from LegalEntity.info_uri or registry_uri."""
    le = entity.legal_entity
    if getattr(le, "info_uri", None):
        return [{"language": "en", "uri": le.info_uri}]
    if entity.registry_uri:
        return [{"language": "en", "uri": entity.registry_uri}]
    return []


def _build_entity(entity, service_type, service_status=None):
    """
    Build a TrustedEntity dict matching etsi119602.TrustedEntity Go struct.
    Returns None if the entity has no digital identity.

    PID profile: service_status must be None (absent from output).
    PuB-EAA profile: service_status is required.
    """
    digital_identities = _digital_identities(entity)
    if not digital_identities:
        return None

    names = _names(entity)

    service = {
        "serviceType": service_type,
        "serviceName": names,
        "digitalIdentities": digital_identities,
    }
    if service_status is not None:
        service["serviceStatus"] = service_status

    return {
        "entityId": entity.registry_uri,
        "entityName": names,
        "entityStatus": _STATUS_GRANTED,
        "digitalIdentities": digital_identities,
        "services": [service],
        "informationURIs": _info_uris(entity),
    }


def _scheme_information(lote_type, dist_point, now):
    """Build schemeInformation matching etsi119602.SchemeInformation Go struct."""
    return {
        "territory": _territory(),
        "schemeOperator": [{"language": "en", "value": _operator_name()}],
        "schemeName": [{"language": "en", "value": "EU Trusted Entities List"}],
        "schemeType": lote_type,
        "issueDate": _iso(now),
        "nextUpdate": _iso(now + timedelta(days=_NEXT_UPDATE_DAYS)),
        "sequenceNumber": _sequence_number(),
        "distributionPoints": [_dist_url(dist_point)],
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class LOTEPIDProvidersView(APIView):
    """
    GET /lote-source/pid-providers/

    Unsigned PID Providers LoTE (ETSI TS 119 602).
    Format matches etsi119602.ListOfTrustedEntities (g119612).

    PID LoTE rule: ServiceStatus MUST be absent per g119612 validate.go.
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

        trusted_entities = [
            entry
            for e in entities
            if (entry := _build_entity(e, _SVC_TYPE_PID)) is not None
        ]

        lote = {
            "version": "1",
            "schemeInformation": _scheme_information(
                _LOTE_TYPE_PID,
                "/lote/pid_providers/pid_providers.json",
                now,
            ),
            "trustedEntities": trusted_entities,
        }
        return Response(lote)


class LOTEPubEAAProvidersView(APIView):
    """
    GET /lote-source/pubeaa-providers/

    Unsigned PuB-EAA Providers LoTE (ETSI TS 119 602).
    Format matches etsi119602.ListOfTrustedEntities (g119612).

    PuB-EAA LoTE rule: ServiceStatus REQUIRED per g119612 validate.go.
    Revoked entities remain permanently as withdrawn.
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

        def svc_status(entity):
            return (
                _STATUS_GRANTED
                if entity.registration_status == "active"
                else _STATUS_WITHDRAWN
            )

        trusted_entities = [
            entry
            for e in entities
            if (
                entry := _build_entity(
                    e, _SVC_TYPE_PUBEAA, service_status=svc_status(e)
                )
            )
            is not None
        ]

        lote = {
            "version": "1",
            "schemeInformation": _scheme_information(
                _LOTE_TYPE_PUBEAA,
                "/lote/pubeaa_providers/pubeaa_providers.json",
                now,
            ),
            "trustedEntities": trusted_entities,
        }
        return Response(lote)
