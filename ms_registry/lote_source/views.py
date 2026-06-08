"""
LoTE source views — ETSI TS 119 602 unsigned JSON for g119612 (tsl-tool).

These two endpoints serve unsigned LoTE documents consumed by the
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

JSON format matches etsi119602 Go struct (g119612 commit 28620f4a):
  - root envelope: {"LoTE": {"ListAndSchemeInformation": {...},
    "TrustedEntitiesList": [...]}}
  - LangString/NameSet fields use "lang" (not "language")
  - URI fields use "uriValue" (not "uri")
  - ServiceDigitalIdentity: {"X509Certificates": [{"val": "<base64-DER>"}]}
  - TEAddress required (non-null); TEInformationURI required (non-empty)
  - PID profile: ServiceStatus must be absent
  - PuB-EAA profile: ServiceStatus required (granted/withdrawn)

IMPORTANT — Member State notification requirement
-------------------------------------------------
Both PID Providers and PuB-EAA Providers must be formally notified to the
Member State Registry before they may appear in the respective LoTE. Until a
dedicated notification workflow is implemented, "active" registration status
is used as the operational proxy for "notified".

Configure via Django settings (all optional):
  LOTE_OPERATOR_NAME    default "WP4Trust Registry"
  LOTE_TERRITORY        default "EU"
  LOTE_SEQUENCE_NUMBER  default 1
  LOTE_PUBLIC_BASE_URL  default "http://localhost"
"""

import base64
import logging
from datetime import timedelta

from core.models import EntitlementType
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.utils import timezone
from registry.models import RegisteredEntity
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ETSI TS 119 602 URI constants
# ---------------------------------------------------------------------------

_LOTE_TYPE_PID = "http://uri.etsi.org/19602/LoTEType/EUPIDProvidersList"
_LOTE_TYPE_PUBEAA = "http://uri.etsi.org/19602/LoTEType/EUPubEAAProvidersList"

_SVC_TYPE_PID = "http://uri.etsi.org/19602/SvcType/PIDProvider"
_SVC_TYPE_PUBEAA = "http://uri.etsi.org/19602/SvcType/PubEAAProvider"

_STATUS_NOTIFIED = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/notified"
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


def _nameset(entity):
    """NameSet as [{"lang": ..., "value": ...}] from EntityServiceDescription."""
    descriptions = list(entity.service_descriptions.all())
    if descriptions:
        return [{"lang": d.lang, "value": d.content} for d in descriptions]
    return [{"lang": "en", "value": entity.trade_name or entity.display_name}]


def _service_digital_identity(entity, entitlement_type):
    """
    ServiceDigitalIdentity from EntitySigningCertificate.
    Returns {"X509Certificates": [{"val": "<base64-DER>"}]} or None if not found.
    """
    try:
        cert_record = next(
            (
                c
                for c in entity.signing_certificates.all()
                if c.entitlement_type == entitlement_type
                and c.is_current
                and c.revoked_at is None
            ),
            None,
        )

        if cert_record is None:
            logger.warning(
                "LoTE: no signing certificate for %s (%s) entitlement %s — excluded",
                entity.display_name,
                entity.pk,
                entitlement_type,
            )
            return None

        cert = x509.load_pem_x509_certificate(cert_record.certificate_pem.encode())
        der = cert.public_bytes(serialization.Encoding.DER)
        b64 = base64.b64encode(der).decode()

        sdi = {"X509Certificates": [{"val": b64}]}
        if cert_record.subject_dn:
            sdi["X509SubjectNames"] = [cert_record.subject_dn]
        return sdi

    except Exception:
        logger.exception(
            "LoTE: error reading signing certificate for %s (%s)",
            entity.display_name,
            entity.pk,
        )
        return None


def _te_information_uri(entity):
    """TEInformationURI as [{"lang": "en", "uriValue": "..."}]."""
    le = entity.legal_entity
    if getattr(le, "info_uri", None):
        return [{"lang": "en", "uriValue": le.info_uri}]
    if entity.domain_uri:
        return [{"lang": "en", "uriValue": entity.domain_uri}]
    if entity.registry_uri:
        return [{"lang": "en", "uriValue": entity.registry_uri}]
    return []


def _build_entity(entity, service_type, entitlement_type, service_status=None):
    """
    Build a TrustedEntity dict matching etsi119602.TrustedEntity Go struct.
    Returns None if the entity has no digital identity or no information URI.

    PID profile: service_status must be None (absent from output).
    PuB-EAA profile: service_status is required.
    """
    sdi = _service_digital_identity(entity, entitlement_type)
    if not sdi:
        return None

    info_uri = _te_information_uri(entity)
    if not info_uri:
        return None

    names = _nameset(entity)

    service_info = {
        "ServiceName": names,
        "ServiceDigitalIdentity": sdi,
        "ServiceTypeIdentifier": service_type,
    }
    if service_status is not None:
        service_info["ServiceStatus"] = service_status

    return {
        "TrustedEntityInformation": {
            "TEName": names,
            "TEAddress": {"TEPostalAddress": [], "TEElectronicAddress": []},
            "TEInformationURI": info_uri,
        },
        "TrustedEntityServices": [{"ServiceInformation": service_info}],
    }


def _scheme_information(lote_type, dist_point, now):
    """Build ListAndSchemeInformation matching etsi119602 Go struct."""
    return {
        "LoTEVersionIdentifier": 1,
        "LoTESequenceNumber": _sequence_number(),
        "LoTEType": lote_type,
        "SchemeOperatorName": [{"lang": "en", "value": _operator_name()}],
        "SchemeName": [{"lang": "en", "value": "EU Trusted Entities List"}],
        "SchemeTerritory": _territory(),
        "ListIssueDateTime": _iso(now),
        "NextUpdate": _iso(now + timedelta(days=_NEXT_UPDATE_DAYS)),
        "DistributionPoints": [_dist_url(dist_point)],
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class LOTEPIDProvidersView(APIView):
    """
    GET /lote-source/pid-providers/

    Unsigned PID Providers LoTE (ETSI TS 119 602).
    Format matches etsi119602.LoTEDocument (g119612 commit 28620f4a).

    PID LoTE rule: ServiceStatus MUST be absent per g119612 validate.go.
    """

    permission_classes = (AllowAny,)

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
                "signing_certificates",
            )
        )

        trusted_entities = [
            entry
            for e in entities
            if (entry := _build_entity(e, _SVC_TYPE_PID, EntitlementType.PID_PROVIDER))
            is not None
        ]

        lote = {
            "LoTE": {
                "ListAndSchemeInformation": _scheme_information(
                    _LOTE_TYPE_PID,
                    "/lote/pid_providers/pid_providers.json",
                    now,
                ),
                "TrustedEntitiesList": trusted_entities,
            }
        }
        return Response(lote)


class LOTEPubEAAProvidersView(APIView):
    """
    GET /lote-source/pubeaa-providers/

    Unsigned PuB-EAA Providers LoTE (ETSI TS 119 602).
    Format matches etsi119602.LoTEDocument (g119612 commit 28620f4a).

    PuB-EAA LoTE rule: ServiceStatus REQUIRED per g119612 validate.go.
    Revoked entities remain permanently as withdrawn.
    """

    permission_classes = (AllowAny,)

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
                "signing_certificates",
            )
        )

        def svc_status(entity):
            return (
                _STATUS_NOTIFIED
                if entity.registration_status == "active"
                else _STATUS_WITHDRAWN
            )

        trusted_entities = [
            entry
            for e in entities
            if (
                entry := _build_entity(
                    e,
                    _SVC_TYPE_PUBEAA,
                    EntitlementType.PUB_EAA_PROVIDER,
                    service_status=svc_status(e),
                )
            )
            is not None
        ]

        lote = {
            "LoTE": {
                "ListAndSchemeInformation": _scheme_information(
                    _LOTE_TYPE_PUBEAA,
                    "/lote/pubeaa_providers/pubeaa_providers.json",
                    now,
                ),
                "TrustedEntitiesList": trusted_entities,
            }
        }
        return Response(lote)
