"""
Certificate views.

GET  /certificates/cnf/<entity_id>/
    Returns a signed JWT containing the confirmed registry data (cnf) for an
    active registered entity. The CA or the entity uses this data to build and
    sign the X.509 access certificate.

POST /certificates/upload/<entity_id>/
    Accepts a PEM-encoded X.509 access certificate, validates it against the
    registered entity data (ETSI TS 119 411-8), and stores the certificate
    in EntityAccessCertificate.

GET/POST /certificates/upload/<entity_id>/view/
    HTML form equivalent of the upload endpoint.
"""

import hashlib
import time

from certificates.models import EntityAccessCertificate
from certificates.serializers import AccessCertificateUploadSerializer
from core.models import RegistrationStatus
from core.signing import sign_jwt
from cryptography.hazmat.primitives import serialization
from django.db import transaction
from django.shortcuts import render
from django.views import View
from drf_spectacular.utils import extend_schema
from registry.models import RegisteredEntity
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

CNF_VALIDITY_SECONDS = 24 * 60 * 60  # 24 hours


class CnfView(APIView):
    """
    GET /certificates/cnf/<entity_id>/

    Returns a signed JWT with the confirmed registry data for the entity.
    Only entities with registration_status=active are eligible.

    The JWT payload ("cnf" claim) contains:
      - name: legal or trade name
      - country: ISO 3166-1 alpha-2 member state code
      - org_identifier: primary identifier value (e.g. NTRDEU-HRB12345)
      - org_identifier_type: identifier type (e.g. EUID, NATIONAL_BUSINESS_REG)
      - role: entity_role (relying_party / pid_provider / attestation_provider)
      - entitlements: list of entitlement_type values
      - registration_status: always "active" at time of issuance
    """

    permission_classes = []
    authentication_classes = []

    @extend_schema(
        summary="Get signed cnf JWT for access certificate issuance",
        description=(
            "Returns an ES256-signed JWT containing the confirmed registry data "
            "(cnf claim) for the given registered entity. "
            "Only active entities are eligible. "
            "The CA uses this JWT to verify the entity data before issuing an "
            "X.509 access certificate."
        ),
        responses={
            200: {"type": "object", "properties": {"token": {"type": "string"}}},
            404: {"description": "Entity not found"},
            409: {"description": "Entity is not active"},
            500: {"description": "Failed to generate signed JWT"},
        },
    )
    # TODO: reconsider the endpoint, probably serializer lookup
    def get(self, request, entity_id, *args, **kwargs):
        try:
            entity = (
                RegisteredEntity.objects.select_related(
                    "legal_entity__legal_person",
                    "legal_entity__natural_person",
                    "legal_entity__primary_identifier",
                    "legal_entity__physical_address",
                )
                .prefetch_related("entitlements", "support_uris")
                .get(id=entity_id)
            )
        except RegisteredEntity.DoesNotExist:
            return Response(
                {"detail": "Entity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if entity.registration_status != RegistrationStatus.ACTIVE:
            return Response(
                {
                    "detail": (
                        f"Entity registration status is "
                        f"'{entity.registration_status}', not 'active'. "
                        f"cnf can only be issued for active entities."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        # GEN-6.6.1-07 [CHOICE]: the certificate SAN must contain at least one
        # contact method (URL, email, or phone). Reject the cnf request early if
        # none are registered — the resulting certificate would fail validation.
        has_contact = (
            entity.support_uris.exists()
            or entity.legal_entity.email
            or entity.legal_entity.phone
        )
        if not has_contact:
            return Response(
                {
                    "detail": (
                        "Entity has no contact information. "
                        "At least one of support URL, email, or phone is required "
                        "for the certificate SAN (GEN-6.6.1-07)."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        primary_id = entity.legal_entity.primary_identifier
        now = int(time.time())
        issuer = request.build_absolute_uri("/").rstrip("/")

        payload = {
            "iss": issuer,
            "sub": str(entity.id),
            "iat": now,
            "exp": now + CNF_VALIDITY_SECONDS,
            "cnf": {
                # entity_type drives which Subject DN attributes the CA must use:
                # legal_person  → O + organizationIdentifier (ETSI EN 319 412-3)
                # natural_person → GN + SN + serialNumber   (ETSI EN 319 412-2)
                "entity_type": entity.legal_entity.entity_type,
                # name: formal legal name from the official record (CIR Annex I pt 1)
                # For legal persons: LegalPerson.legal_name
                # For natural persons: given_name + family_name
                "name": entity.legal_entity.display_name,
                # friendly_name: user-recognisable trade/service name (CIR Annex I pt 2)
                # Goes into CN; may be absent if no trade name is registered
                "friendly_name": entity.trade_name,
                # given_name / family_name: provided for natural persons so the CA can
                # populate GN and SN in the Subject DN (ETSI EN 319 412-2)
                "given_name": (
                    entity.legal_entity.natural_person.given_name
                    if entity.legal_entity.natural_person
                    else None
                ),
                "family_name": (
                    entity.legal_entity.natural_person.family_name
                    if entity.legal_entity.natural_person
                    else None
                ),
                "country": (
                    (primary_id.country_code if primary_id else None)
                    or (
                        entity.legal_entity.physical_address.country_code
                        if entity.legal_entity.physical_address
                        else None
                    )
                ),
                "org_identifier": (primary_id.identifier_value if primary_id else None),
                "org_identifier_type": (
                    primary_id.identifier_type if primary_id else None
                ),
                "role": entity.entity_role,
                "entitlements": [e.entitlement_type for e in entity.entitlements.all()],
                "urls": [su.support_uri for su in entity.support_uris.all()],
                "contact": {
                    "email": entity.legal_entity.email,
                    "phone": entity.legal_entity.phone,
                },
                "registration_status": entity.registration_status,
            },
        }

        token = sign_jwt(payload)
        return Response({"token": token}, status=status.HTTP_200_OK)


# django views, excluded from swagger
class CnfPageView(View):
    """
    GET /certificates/cnf/<entity_id>/view/

    Calls CnfView internally and renders the result (token or error) as HTML.
    """

    def get(self, request, entity_id):
        api_response = CnfView.as_view()(request, entity_id=entity_id)
        if api_response.status_code == 200:
            context = {"token": api_response.data.get("token")}
        else:
            context = {"error": api_response.data.get("detail")}
        return render(
            request, "cnf_result.html", context, status=api_response.status_code
        )


# ── helpers shared by upload views ────────────────────────────────────────────


def _get_entity_for_upload(entity_id):
    """
    Look up a RegisteredEntity with all relations needed for certificate
    validation.  Returns the entity or raises RegisteredEntity.DoesNotExist.
    """
    return (
        RegisteredEntity.objects.select_related(
            "legal_entity__legal_person",
            "legal_entity__natural_person",
            "legal_entity__primary_identifier",
            "legal_entity__physical_address",
        )
        .prefetch_related("entitlements", "support_uris")
        .get(id=entity_id)
    )


def _store_certificate(entity, cert, certificate_pem: str) -> EntityAccessCertificate:
    """
    Persist the certificate record atomically.
    Marks any existing current certificate for the entity as no longer current.
    """
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    fingerprint = hashlib.sha256(cert_der).hexdigest()
    serial = format(cert.serial_number, "x").upper()

    # TODO: Add a proper CT log implementation, e.g. using the python-ct library
    # from certificates.ct_log import create_ct_log_entry
    # from datetime import datetime, timezone
    # log_id, timestamp_ms, sct_bytes = create_ct_log_entry(cert_der)
    # ct_timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

    with transaction.atomic():
        EntityAccessCertificate.objects.filter(
            registered_entity=entity, is_current=True
        ).update(is_current=False)

        return EntityAccessCertificate.objects.create(
            registered_entity=entity,
            certificate_serial=serial,
            certificate_fingerprint_sha256=fingerprint,
            issuer_dn=cert.issuer.rfc4514_string(),
            subject_dn=cert.subject.rfc4514_string(),
            not_before=cert.not_valid_before_utc,
            not_after=cert.not_valid_after_utc,
            # TODO: ct_log_id=log_id,
            # TODO: ct_log_timestamp=ct_timestamp,
            # TODO: ct_sct=sct_bytes,
            is_current=True,
            certificate_pem=certificate_pem,
        )


# ── JSON API ──────────────────────────────────────────────────────────────────


class AccessCertificateUploadView(APIView):
    """
    POST /certificates/upload/<entity_id>/

    Accepts a PEM-encoded X.509 access certificate, validates it against the
    registered entity data per ETSI TS 119 411-8, creates a simplified RFC 9162
    CT log entry, and stores the record in EntityAccessCertificate.

    Request body (JSON):
        { "certificate_pem": "-----BEGIN CERTIFICATE-----\\n..." }

    Responses:
        201  Certificate accepted; returns stored record fields.
        400  Validation error; returns error details.
        404  Entity not found.
        409  Entity is not active.
    """

    permission_classes = []
    authentication_classes = []

    @extend_schema(
        summary="Upload access certificate for an entity (simplified flow)",
        description=(
            "Validates the PEM certificate against registry data "
            "(ETSI TS 119 411-8) and stores the certificate. "
            "Only active entities are accepted."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {"certificate_pem": {"type": "string"}},
                "required": ["certificate_pem"],
            }
        },
        responses={
            201: {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "certificate_serial": {"type": "string"},
                    "certificate_fingerprint_sha256": {"type": "string"},
                    "subject_dn": {"type": "string"},
                    "issuer_dn": {"type": "string"},
                    "not_before": {"type": "string"},
                    "not_after": {"type": "string"},
                },
            },
            400: {"description": "Validation error"},
            404: {"description": "Entity not found"},
            409: {"description": "Entity is not active"},
        },
    )
    def post(self, request, entity_id, *args, **kwargs):
        try:
            entity = _get_entity_for_upload(entity_id)
        except RegisteredEntity.DoesNotExist:
            return Response(
                {"detail": "Entity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if entity.registration_status != RegistrationStatus.ACTIVE:
            return Response(
                {
                    "detail": (
                        f"Entity registration status is "
                        f"'{entity.registration_status}', not 'active'."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = AccessCertificateUploadSerializer(
            data=request.data,
            context={"entity": entity},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cert = serializer.validated_data["certificate_pem"]
        certificate_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        cert_record = _store_certificate(entity, cert, certificate_pem)

        return Response(
            {
                "id": str(cert_record.id),
                "certificate_serial": cert_record.certificate_serial,
                "certificate_fingerprint_sha256": (
                    cert_record.certificate_fingerprint_sha256
                ),
                "subject_dn": cert_record.subject_dn,
                "issuer_dn": cert_record.issuer_dn,
                "not_before": cert_record.not_before.isoformat(),
                "not_after": cert_record.not_after.isoformat(),
                # TODO: "ct_log_id": cert_record.ct_log_id,
                # TODO: "ct_log_timestamp": cert_record.ct_log_timestamp.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


# ── Certificate detail page ───────────────────────────────────────────────────


class AccessCertificateDetailPageView(View):
    """
    GET /certificates/detail/<entity_id>/view/

    Shows the current active access certificate for the entity.
    """

    def get(self, request, entity_id):
        try:
            entity = _get_entity_for_upload(entity_id)
        except RegisteredEntity.DoesNotExist:
            return render(
                request,
                "certificate_detail.html",
                {"error": "Entity not found."},
                status=404,
            )

        from django.utils import timezone as tz

        certificate = (
            EntityAccessCertificate.objects.filter(
                registered_entity=entity,
                is_current=True,
                revoked_at__isnull=True,
                not_after__gt=tz.now(),
            )
            .order_by("-created_at")
            .first()
        )

        return render(
            request,
            "certificate_detail.html",
            {
                "entity_name": entity.display_name,
                "entity_id": str(entity.id),
                "certificate": certificate,
            },
        )


# ── HTML page view ────────────────────────────────────────────────────────────


class AccessCertificateUploadPageView(View):
    """
    GET  /certificates/upload/<entity_id>/view/  – render upload form
    POST /certificates/upload/<entity_id>/view/  – process upload, show result
    """

    def _base_context(self, entity):
        return {"entity_name": entity.display_name, "entity_id": str(entity.id)}

    def get(self, request, entity_id):
        try:
            entity = _get_entity_for_upload(entity_id)
        except RegisteredEntity.DoesNotExist:
            return render(
                request,
                "upload_certificate.html",
                {"error": "Entity not found."},
                status=404,
            )
        return render(request, "upload_certificate.html", self._base_context(entity))

    def post(self, request, entity_id):
        try:
            entity = _get_entity_for_upload(entity_id)
        except RegisteredEntity.DoesNotExist:
            return render(
                request,
                "upload_certificate.html",
                {"error": "Entity not found."},
                status=404,
            )

        if entity.registration_status != RegistrationStatus.ACTIVE:
            ctx = self._base_context(entity)
            ctx["error"] = (
                f"Entity registration status is '{entity.registration_status}', "
                f"not 'active'."
            )
            return render(request, "upload_certificate.html", ctx, status=409)

        pem_value = request.POST.get("certificate_pem", "")
        serializer = AccessCertificateUploadSerializer(
            data={"certificate_pem": pem_value},
            context={"entity": entity},
        )

        ctx = self._base_context(entity)
        ctx["pem_value"] = pem_value

        if not serializer.is_valid():
            pem_errors = serializer.errors.get("certificate_pem", [])
            # flatten nested lists / single strings
            flat_errors = []
            for e in pem_errors:
                if isinstance(e, list):
                    flat_errors.extend(e)
                else:
                    flat_errors.append(str(e))
            ctx["errors"] = flat_errors
            return render(request, "upload_certificate.html", ctx, status=400)

        cert = serializer.validated_data["certificate_pem"]
        certificate_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        cert_record = _store_certificate(entity, cert, certificate_pem)
        ctx["certificate"] = cert_record
        return render(request, "upload_certificate.html", ctx, status=201)
