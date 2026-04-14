"""
Certificate views.

GET /certificates/cnf/<entity_id>/
    Returns a signed JWT containing the confirmed registry data (cnf) for an
    active registered entity. The CA or the entity uses this data to build and
    sign the X.509 access certificate.
"""

import time
import uuid

from core.models import RegistrationStatus
from core.signing import sign_jwt
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
        },
    )
    def get(self, request, entity_id, *args, **kwargs):
        try:
            uuid.UUID(str(entity_id))
        except ValueError:
            return Response(
                {"detail": "Invalid entity_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            entity = (
                RegisteredEntity.objects.select_related(
                    "legal_entity__legal_person",
                    "legal_entity__natural_person",
                    "legal_entity__primary_identifier",
                    "legal_entity__physical_address",
                )
                .prefetch_related("entitlements")
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

        primary_id = entity.legal_entity.primary_identifier
        now = int(time.time())
        issuer = request.build_absolute_uri("/").rstrip("/")

        payload = {
            "iss": issuer,
            "sub": str(entity.id),
            "iat": now,
            "exp": now + CNF_VALIDITY_SECONDS,
            "cnf": {
                "name": entity.display_name,
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
