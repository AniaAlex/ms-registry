"""
Certificate views.

GET  /certificates/cnf/<entity_id>/
    Returns a signed JWT containing the confirmed registry data (cnf) for an
    active registered entity. The CA or the entity uses this data to build and
    sign the X.509 access certificate.

POST /certificates/issue/<entity_id>/
    Accepts a CSR, validates the entity, and issues a signed access certificate
    using the integrated Access CA (django-ca).

GET/POST /certificates/issue/<entity_id>/view/
    HTML form equivalent of the issue endpoint: submit a CSR and the
    integrated Access CA generates the access certificate.
"""

import hashlib
import logging
import time

import jwt as pyjwt
from certificates.models import EntityAccessCertificate, EntitySigningCertificate
from certificates.serializers import (
    CSRSubmissionSerializer,
    SigningCertificateUploadSerializer,
)
from core.models import EntitlementType, RegistrationStatus
from core.signing import sign_jwt
from cryptography.hazmat.primitives import serialization
from django.db import transaction
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from drf_spectacular.utils import extend_schema
from participant.views import JWTLoginRequiredMixin
from registry.models import RegisteredEntity
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def _user_facing_issuance_error(error, entity_id) -> str:
    """User-safe message for a CertificateIssuanceError.

    4xx errors are validation feedback (subject/key mismatch, eligibility) and
    are safe to show as-is. 5xx errors may carry internal django-ca/crypto
    detail, so the full error is logged server-side and the user sees a generic
    message — avoids leaking implementation details.
    """
    if getattr(error, "http_status", 500) >= 500:
        logger.error(
            "Certificate issuance failed for entity %s: %s",
            entity_id,
            error,
            exc_info=True,
        )
        return (
            "Certificate issuance failed due to a server error. "
            "Please contact the operator."
        )
    return str(error)


_ISSUER_ENTITLEMENT_TYPES = {
    EntitlementType.PID_PROVIDER,
    EntitlementType.QEAA_PROVIDER,
    EntitlementType.PUB_EAA_PROVIDER,
    EntitlementType.NON_Q_EAA_PROVIDER,
}

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

    permission_classes = (IsAuthenticated,)

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
            # Scoped to the requesting operator: the cnf JWT is the authoritative
            # input the CA trusts to build the access certificate, so only an
            # entity's own operators may request it.
            entity = (
                RegisteredEntity.objects.filter(operators=request.user)
                .select_related(
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
        support_uris = list(entity.support_uris.all())
        has_contact = (
            bool(support_uris) or entity.legal_entity.email or entity.legal_entity.phone
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
                "urls": [su.support_uri for su in support_uris],
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
class CnfPageView(JWTLoginRequiredMixin, View):
    """
    GET /certificates/cnf/<entity_id>/view/

    Calls CnfView internally and renders the result (token or error) as HTML.
    """

    def get(self, request, entity_id):
        api_response = CnfView.as_view()(request, entity_id=entity_id)
        if api_response.status_code == 200:
            token = api_response.data.get("token")
            payload = pyjwt.decode(
                token, options={"verify_signature": False}, algorithms=["ES256"]
            )
            context = {"token": token, "cnf_data": payload.get("cnf", {})}
        else:
            context = {"error": api_response.data.get("detail")}
        return render(
            request, "cnf_result.html", context, status=api_response.status_code
        )


# ── helpers shared by upload views ────────────────────────────────────────────


def _get_entity_for_upload(entity_id, user):
    """
    Look up a RegisteredEntity with all relations needed for certificate
    validation, scoped to entities the requesting participant operates.

    Certificate issuance mints an access certificate that authenticates the
    entity, so it must be restricted to that entity's operators — otherwise any
    authenticated participant could obtain a certificate impersonating an entity
    they do not control (the CSR subject fields are public registry data).
    Non-operators get RegisteredEntity.DoesNotExist (surfaced as 404) so the
    endpoint does not leak which entity IDs exist.

    Returns the entity or raises RegisteredEntity.DoesNotExist.
    """
    return (
        RegisteredEntity.objects.filter(operators=user)
        .select_related(
            "legal_entity__legal_person",
            "legal_entity__natural_person",
            "legal_entity__primary_identifier",
            "legal_entity__physical_address",
        )
        .prefetch_related("entitlements", "support_uris")
        .get(id=entity_id)
    )


# ── Certificate Issuance (Integrated Access CA) ───────────────────────────────


class IssueCertificateView(APIView):
    """
    POST /certificates/issue/<entity_id>/

    Issue an access certificate for a registered entity using the integrated
    Access CA (django-ca). Implements the Integrated Model per ETSI TS 119 475
    Annex D.1.

    The entity submits a CSR; the CA validates it against registry data and
    issues a signed X.509 access certificate with:
    - Subject DN from registry (C, O, CN, organizationIdentifier)
    - SAN containing registry_uri, email, and entitlement OIDs
    - Certificate policy OID (NCP-l-eudiwrp or NCP-n-eudiwrp)
    - 1 year validity

    Request body (JSON):
        { "csr_pem": "-----BEGIN CERTIFICATE REQUEST-----\\n..." }

    Responses:
        201  Certificate issued; returns certificate and metadata.
        400  Validation error (invalid CSR, entity not eligible).
        404  Entity not found.
        409  Entity is not active.
        500  CA error (CA not configured, signing failed).
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Issue access certificate (Integrated Access CA)",
        description=(
            "Submit a CSR to receive a signed X.509 access certificate. "
            "The certificate is issued by the integrated Access CA and includes "
            "Subject DN, SAN (with entitlement OIDs), and certificate policy "
            "derived from the entity's registry data. "
            "Only active entities are eligible."
        ),
        request={
            "application/json": {
                "type": "object",
                "properties": {"csr_pem": {"type": "string"}},
                "required": ["csr_pem"],
            }
        },
        responses={
            201: {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "certificate_pem": {"type": "string"},
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
            500: {"description": "CA error"},
        },
    )
    def post(self, request, entity_id, *args, **kwargs):
        # 1. Get entity (scoped to the requesting operator)
        try:
            entity = _get_entity_for_upload(entity_id, request.user)
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

        # 2. Validate CSR
        serializer = CSRSubmissionSerializer(
            data=request.data,
            context={"entity": entity},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 3. Issue certificate via CA integration
        from certificates.ca_integration import (
            CertificateIssuanceError,
            issue_access_certificate,
        )

        try:
            cert_record = issue_access_certificate(
                entity_id=str(entity_id),
                csr=serializer.validated_data["csr"],
            )
        except CertificateIssuanceError as e:
            detail = _user_facing_issuance_error(e, entity_id)
            return Response({"detail": detail}, status=e.http_status)

        # 4. Return certificate
        return Response(
            {
                "id": str(cert_record.id),
                "certificate_pem": cert_record.certificate_pem,
                "certificate_serial": cert_record.certificate_serial,
                "certificate_fingerprint_sha256": (
                    cert_record.certificate_fingerprint_sha256
                ),
                "subject_dn": cert_record.subject_dn,
                "issuer_dn": cert_record.issuer_dn,
                "not_before": cert_record.not_before.isoformat(),
                "not_after": cert_record.not_after.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


# ── Certificate detail page ───────────────────────────────────────────────────


class AccessCertificateDetailPageView(JWTLoginRequiredMixin, View):
    """
    GET /certificates/detail/<entity_id>/view/

    Shows the current active access certificate for the entity.
    """

    def get(self, request, entity_id):
        try:
            entity = _get_entity_for_upload(entity_id, request.user)
        except RegisteredEntity.DoesNotExist:
            return render(
                request,
                "certificate_detail.html",
                {"error": "Entity not found."},
                status=404,
            )

        now = timezone.now()
        certificate = (
            EntityAccessCertificate.objects.filter(
                registered_entity=entity,
                is_current=True,
                revoked_at__isnull=True,
                not_before__lte=now,
                not_after__gt=now,
            )
            .order_by("-created_at")
            .first()
        )

        # Decode the full X.509 structure (all fields + extensions) from the
        # stored PEM so the page can show everything, not just the DB columns.
        decoded = None
        if certificate and certificate.certificate_pem:
            from certificates.cert_decoder import decode_certificate

            decoded = decode_certificate(certificate.certificate_pem)

        return render(
            request,
            "certificate_detail.html",
            {
                "entity_name": entity.display_name,
                "entity_id": str(entity.id),
                "certificate": certificate,
                "decoded": decoded,
            },
        )


# ── HTML page view ────────────────────────────────────────────────────────────


class IssueCertificatePageView(JWTLoginRequiredMixin, View):
    """
    GET  /certificates/issue/<entity_id>/view/  – render CSR submission form
    POST /certificates/issue/<entity_id>/view/  – issue an access certificate
                                                   from the CSR, show result

    HTML form equivalent of IssueCertificateView. Reuses the same CSR
    validation (CSRSubmissionSerializer) and issuance logic
    (issue_access_certificate) as the JSON API endpoint, so the certificate is
    generated by the integrated Access CA rather than uploaded.
    """

    def _base_context(self, entity):
        return {"entity_name": entity.display_name, "entity_id": str(entity.id)}

    def get(self, request, entity_id):
        try:
            entity = _get_entity_for_upload(entity_id, request.user)
        except RegisteredEntity.DoesNotExist:
            return render(
                request,
                "issue_certificate.html",
                {"error": "Entity not found."},
                status=404,
            )
        return render(request, "issue_certificate.html", self._base_context(entity))

    def post(self, request, entity_id):
        try:
            entity = _get_entity_for_upload(entity_id, request.user)
        except RegisteredEntity.DoesNotExist:
            return render(
                request,
                "issue_certificate.html",
                {"error": "Entity not found."},
                status=404,
            )

        if entity.registration_status != RegistrationStatus.ACTIVE:
            ctx = self._base_context(entity)
            ctx["error"] = (
                f"Entity registration status is '{entity.registration_status}', "
                f"not 'active'."
            )
            return render(request, "issue_certificate.html", ctx, status=409)

        csr_value = request.POST.get("csr_pem", "")
        serializer = CSRSubmissionSerializer(
            data={"csr_pem": csr_value},
            context={"entity": entity},
        )

        ctx = self._base_context(entity)
        ctx["csr_value"] = csr_value

        if not serializer.is_valid():
            # Errors may sit under "csr_pem" (field) or "non_field_errors"
            # (entity eligibility, raised by the serializer's validate()).
            flat_errors = []
            for key in ("csr_pem", "non_field_errors"):
                for e in serializer.errors.get(key, []):
                    if isinstance(e, list):
                        flat_errors.extend(str(x) for x in e)
                    else:
                        flat_errors.append(str(e))
            ctx["errors"] = flat_errors or ["Invalid CSR."]
            return render(request, "issue_certificate.html", ctx, status=400)

        # Reuse the same issuance path as the JSON IssueCertificateView.
        from certificates.ca_integration import (
            CertificateIssuanceError,
            issue_access_certificate,
        )

        try:
            cert_record = issue_access_certificate(
                entity_id=str(entity_id),
                csr=serializer.validated_data["csr"],
            )
        except CertificateIssuanceError as e:
            ctx["errors"] = [_user_facing_issuance_error(e, entity_id)]
            return render(request, "issue_certificate.html", ctx, status=e.http_status)

        ctx["certificate"] = cert_record
        return render(request, "issue_certificate.html", ctx, status=201)


# ── Signing Certificate helpers ───────────────────────────────────────────────


def _store_signing_certificate(entity, cert, certificate_pem, entitlement_type):
    """
    Persist a new signing certificate, marking the previous current one
    as historical.
    """
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    fingerprint = hashlib.sha256(cert_der).hexdigest()
    serial = format(cert.serial_number, "x").upper()

    with transaction.atomic():
        EntitySigningCertificate.objects.filter(
            registered_entity=entity,
            entitlement_type=entitlement_type,
            is_current=True,
        ).update(is_current=False)

        return EntitySigningCertificate.objects.create(
            registered_entity=entity,
            entitlement_type=entitlement_type,
            certificate_pem=certificate_pem,
            certificate_serial=serial,
            certificate_fingerprint_sha256=fingerprint,
            subject_dn=cert.subject.rfc4514_string(),
            not_before=cert.not_valid_before_utc,
            not_after=cert.not_valid_after_utc,
            is_current=True,
        )


def _signing_cert_response(cert_record):
    return {
        "id": str(cert_record.id),
        "entitlement_type": cert_record.entitlement_type,
        "certificate_serial": cert_record.certificate_serial,
        "certificate_fingerprint_sha256": cert_record.certificate_fingerprint_sha256,
        "subject_dn": cert_record.subject_dn,
        "not_before": (
            cert_record.not_before.isoformat() if cert_record.not_before else None
        ),
        "not_after": (
            cert_record.not_after.isoformat() if cert_record.not_after else None
        ),
        "is_current": cert_record.is_current,
        "revoked_at": (
            cert_record.revoked_at.isoformat() if cert_record.revoked_at else None
        ),
        "created_at": cert_record.created_at.isoformat(),
    }


# ── Signing Certificate JSON API ──────────────────────────────────────────────


class SigningCertificateListCreateView(APIView):
    """
    GET  /certificates/signing/<entity_id>/   List all signing certs for entity.
    POST /certificates/signing/<entity_id>/   Upload a new signing cert.

    Request body (POST, JSON):
        {
            "entitlement_type": "PID_Provider",
            "certificate_pem": "-----BEGIN CERTIFICATE-----\\n..."
        }
    """

    permission_classes = [IsAuthenticated]

    def _get_entity(self, entity_id, user):
        # Scoped to the requesting operator — a signing certificate is bound to
        # the entity, so only its operators may list or upload one.
        return (
            RegisteredEntity.objects.filter(operators=user)
            .prefetch_related("entitlements")
            .get(id=entity_id)
        )

    def get(self, request, entity_id):
        try:
            entity = self._get_entity(entity_id, request.user)
        except RegisteredEntity.DoesNotExist:
            return Response(
                {"detail": "Entity not found."}, status=status.HTTP_404_NOT_FOUND
            )

        certs = EntitySigningCertificate.objects.filter(
            registered_entity=entity
        ).order_by("entitlement_type", "-created_at")

        return Response([_signing_cert_response(c) for c in certs])

    def post(self, request, entity_id):
        try:
            entity = self._get_entity(entity_id, request.user)
        except RegisteredEntity.DoesNotExist:
            return Response(
                {"detail": "Entity not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = SigningCertificateUploadSerializer(
            data=request.data, context={"entity": entity}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cert = serializer.validated_data["certificate_pem"]
        certificate_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        entitlement_type = serializer.validated_data["entitlement_type"]
        cert_record = _store_signing_certificate(
            entity, cert, certificate_pem, entitlement_type
        )

        return Response(
            _signing_cert_response(cert_record), status=status.HTTP_201_CREATED
        )


class SigningCertificateDetailView(APIView):
    """
    GET    /certificates/signing/<entity_id>/<cert_id>/   Retrieve a specific cert.
    DELETE /certificates/signing/<entity_id>/<cert_id>/   Revoke a cert.
    """

    permission_classes = [IsAuthenticated]

    def _get_cert(self, entity_id, cert_id, user):
        # Scoped to the requesting operator via the entity's operators M2M, so a
        # participant can only retrieve or revoke certs of entities they operate.
        return EntitySigningCertificate.objects.select_related("registered_entity").get(
            id=cert_id,
            registered_entity__id=entity_id,
            registered_entity__operators=user,
        )

    def get(self, request, entity_id, cert_id):
        try:
            cert_record = self._get_cert(entity_id, cert_id, request.user)
        except EntitySigningCertificate.DoesNotExist:
            return Response(
                {"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(_signing_cert_response(cert_record))

    def delete(self, request, entity_id, cert_id):
        try:
            cert_record = self._get_cert(entity_id, cert_id, request.user)
        except EntitySigningCertificate.DoesNotExist:
            return Response(
                {"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if cert_record.revoked_at:
            return Response(
                {"detail": "Certificate is already revoked."},
                status=status.HTTP_409_CONFLICT,
            )

        cert_record.revoked_at = timezone.now()
        cert_record.revocation_reason = request.data.get("revocation_reason", "")
        cert_record.is_current = False
        cert_record.save(
            update_fields=["revoked_at", "revocation_reason", "is_current"]
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Signing Certificate HTML page ─────────────────────────────────────────────


class SigningCertificatePageView(JWTLoginRequiredMixin, View):
    """
    GET  /certificates/signing/<entity_id>/view/
        Shows one section per issuer entitlement: current cert status + upload form.

    POST /certificates/signing/<entity_id>/view/
        Processes an upload for a single entitlement (entitlement_type in form data).
    """

    TEMPLATE = "upload_signing_certificate.html"

    def _get_entity(self, entity_id, user):
        # Scoped to the requesting operator (see IssueCertificateView).
        return (
            RegisteredEntity.objects.filter(operators=user)
            .prefetch_related("entitlements")
            .select_related(
                "legal_entity__legal_person", "legal_entity__natural_person"
            )
            .get(id=entity_id)
        )

    LABEL_MAP = {
        EntitlementType.PID_PROVIDER: "PID Provider",
        EntitlementType.QEAA_PROVIDER: "Qualified EAA Provider",
        EntitlementType.PUB_EAA_PROVIDER: "Public EAA Provider",
        EntitlementType.NON_Q_EAA_PROVIDER: "Non-Qualified EAA Provider",
    }

    def _build_sections(self, entity):
        """
        Returns a list of dicts, one per issuer entitlement the entity holds
        that still needs a certificate uploaded:
            { entitlement_type, label, errors, pem_value }

        An entitlement with a current certificate already on file is done -
        it drops off this list rather than sticking around as a completed card.
        """
        has_current_cert = set(
            EntitySigningCertificate.objects.filter(
                registered_entity=entity, is_current=True
            ).values_list("entitlement_type", flat=True)
        )
        sections = []
        for ent in entity.entitlements.filter(
            entitlement_type__in=list(_ISSUER_ENTITLEMENT_TYPES), is_active=True
        ):
            if ent.entitlement_type in has_current_cert:
                continue
            sections.append(
                {
                    "entitlement_type": ent.entitlement_type,
                    "label": self.LABEL_MAP.get(
                        ent.entitlement_type, ent.entitlement_type
                    ),
                    "errors": [],
                    "pem_value": "",
                }
            )
        return sections

    def get(self, request, entity_id):
        try:
            entity = self._get_entity(entity_id, request.user)
        except RegisteredEntity.DoesNotExist:
            return render(
                request, self.TEMPLATE, {"error": "Entity not found."}, status=404
            )

        sections = self._build_sections(entity)
        return render(
            request,
            self.TEMPLATE,
            {
                "entity": entity,
                "sections": sections,
                "all_uploaded": not sections,
            },
        )

    def post(self, request, entity_id):
        try:
            entity = self._get_entity(entity_id, request.user)
        except RegisteredEntity.DoesNotExist:
            return render(
                request, self.TEMPLATE, {"error": "Entity not found."}, status=404
            )

        entitlement_type = request.POST.get("entitlement_type", "")
        pem_value = request.POST.get("certificate_pem", "")

        serializer = SigningCertificateUploadSerializer(
            data={"certificate_pem": pem_value, "entitlement_type": entitlement_type},
            context={"entity": entity},
        )

        sections = self._build_sections(entity)

        if not serializer.is_valid():
            for section in sections:
                if section["entitlement_type"] == entitlement_type:
                    section["errors"] = (
                        serializer.errors.get("certificate_pem", [])
                        + serializer.errors.get("entitlement_type", [])
                        + serializer.errors.get("non_field_errors", [])
                    )
                    section["pem_value"] = pem_value
                    break
            return render(
                request,
                self.TEMPLATE,
                {
                    "entity": entity,
                    "sections": sections,
                    "all_uploaded": False,
                },
                status=400,
            )

        cert = serializer.validated_data["certificate_pem"]
        certificate_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        _store_signing_certificate(entity, cert, certificate_pem, entitlement_type)

        # The just-uploaded entitlement now has a current cert, so it no
        # longer appears in _build_sections() - the step is done, not shown.
        sections = self._build_sections(entity)

        return render(
            request,
            self.TEMPLATE,
            {
                "entity": entity,
                "sections": sections,
                "all_uploaded": not sections,
                "success_label": self.LABEL_MAP.get(entitlement_type, entitlement_type),
            },
        )
