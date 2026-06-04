import time
from datetime import date

from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from registry.models import RegisteredEntity
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import IntendedUse
from .serializers import IntendedUseInputSerializer, create_intended_use


def _serialize_intended_use(iu: IntendedUse) -> dict:
    """
    TS5-compliant representation of a single IntendedUse — mirrors to_representation().
    """
    purposes = [{"lang": p.lang, "content": p.content} for p in iu.purposes.all()]

    credentials = []
    for link in iu.credential_links.select_related("credential"):
        cred = link.credential
        cred_data = {"format": cred.format, "meta": cred.meta}
        claims = [{"path": c.path, "values": c.values} for c in cred.claims.all()]
        if claims:
            cred_data["claims"] = claims
        credentials.append(cred_data)

    privacy_policy = None
    pp = (
        iu.privacy_policies.filter(is_primary=True).first()
        or iu.privacy_policies.first()
    )
    if pp:
        privacy_policy = {
            "policyURI": pp.policy.policy_uri,
            "type": pp.policy.policy_type,
        }

    return {
        "id": str(iu.pk),
        "intendedUseIdentifier": iu.intended_use_identifier,
        "purpose": purposes,
        "credentials": credentials,
        "privacyPolicy": privacy_policy,
        "createdAt": iu.validity_start.isoformat(),
        "revokedAt": iu.validity_end.isoformat() if iu.validity_end else None,
    }


class IntendedUseListCreateView(APIView):
    """
    GET  /registry/wrp/{entity_pk}/intended-use/  — list all intended uses for entity
    POST /registry/wrp/{entity_pk}/intended-use/  — add a new intended use
    """

    permission_classes = (IsAuthenticated,)

    def _get_entity(self, entity_pk):
        return get_object_or_404(RegisteredEntity, pk=entity_pk)

    @extend_schema(
        description="List all intended uses for a registered entity.",
    )
    def get(self, request, entity_pk):
        entity = self._get_entity(entity_pk)
        ius = entity.intended_uses.prefetch_related(
            "purposes",
            "privacy_policies__policy",
            "credential_links__credential__claims",
        )
        return Response([_serialize_intended_use(iu) for iu in ius])

    @extend_schema(
        request=IntendedUseInputSerializer,
        description=(
            "Add a new intended use declaration to an existing registered entity. "
            "intendedUseIdentifier is assigned by the registrar."
        ),
    )
    def post(self, request, entity_pk):
        entity = self._get_entity(entity_pk)
        serializer = IntendedUseInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )
        iu = create_intended_use(entity, serializer.validated_data)
        return Response(_serialize_intended_use(iu), status=status.HTTP_201_CREATED)


class IntendedUseDetailView(APIView):
    """
    GET    /registry/wrp/{entity_pk}/intended-use/{iu_id}/  — retrieve
    DELETE /registry/wrp/{entity_pk}/intended-use/{iu_id}/  — revoke (sets revokedAt)
    """

    permission_classes = (IsAuthenticated,)

    def _get_intended_use(self, entity_pk, iu_id):
        return get_object_or_404(
            IntendedUse,
            pk=iu_id,
            registered_entity__pk=entity_pk,
        )

    @extend_schema(description="Retrieve a specific intended use.")
    def get(self, request, entity_pk, iu_id):
        iu = self._get_intended_use(entity_pk, iu_id)
        return Response(_serialize_intended_use(iu))

    @extend_schema(
        description="Revoke an intended use — sets revokedAt to today. Idempotent.",
    )
    def delete(self, request, entity_pk, iu_id):
        iu = self._get_intended_use(entity_pk, iu_id)
        if iu.validity_end is None:
            iu.validity_end = date.today()
            iu.save(update_fields=["validity_end", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckIntendedUseView(APIView):
    """
    GET /registry/wrp/check-intended-use/

    Checks whether a Wallet Relying Party has a registered intended use
    matching the given criteria. Returns a JWS-signed result per TS5.
    Falls back to plain JSON when REGISTRY_SIGNING_KEY_PEM is not set.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Check intended use (TS5)",
        description=(
            "Returns a JWS-signed result indicating whether the specified "
            "Wallet Relying Party has a registered active intended use "
            "matching the given criteria."
        ),
        parameters=[
            OpenApiParameter(
                "rpidentifier",
                str,
                required=True,
                description="Legal entity identifier of the WRP",
            ),
            OpenApiParameter(
                "intendeduseidentifier",
                str,
                required=False,
                description="Registrar-assigned intended use identifier",
            ),
            OpenApiParameter(
                "credentialformat",
                str,
                required=False,
                description="Credential format to check (e.g. dc+sd-jwt)",
            ),
            OpenApiParameter(
                "claimpath",
                str,
                required=False,
                description="Claim path element to check (e.g. given_name)",
            ),
            OpenApiParameter(
                "credentialmeta",
                str,
                required=False,
                description="Text to match within the credential meta JSON",
            ),
            OpenApiParameter(
                "policyurl",
                str,
                required=False,
                description="Privacy policy URL to check",
            ),
        ],
        responses={
            200: {
                "type": "string",
                "description": "JWS compact serialization (application/jwt)",
            }
        },
    )
    def get(self, request):
        rpidentifier = request.query_params.get("rpidentifier")
        if not rpidentifier:
            return Response(
                {"detail": "rpidentifier is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entity = RegisteredEntity.objects.filter(
            legal_entity__identifiers__identifier_value=rpidentifier
        ).first()
        if not entity:
            return self._build_response(request, False, "Entity not found")

        ius = IntendedUse.objects.filter(
            registered_entity=entity,
            validity_end__isnull=True,
        )

        intendeduseidentifier = request.query_params.get("intendeduseidentifier")
        if intendeduseidentifier:
            ius = ius.filter(intended_use_identifier=intendeduseidentifier)

        credentialformat = request.query_params.get("credentialformat")
        if credentialformat:
            ius = ius.filter(credential_links__credential__format=credentialformat)

        claimpath = request.query_params.get("claimpath")
        if claimpath:
            ius = ius.filter(
                credential_links__credential__claims__path__contains=[claimpath]
            )

        credentialmeta = request.query_params.get("credentialmeta")
        if credentialmeta:
            ius = ius.filter(
                credential_links__credential__meta__icontains=credentialmeta
            )

        policyurl = request.query_params.get("policyurl")
        if policyurl:
            ius = ius.filter(privacy_policies__policy__policy_uri=policyurl)

        is_registered = ius.distinct().exists()
        details = (
            "Intended use is registered"
            if is_registered
            else "No matching intended use found"
        )
        return self._build_response(request, is_registered, details)

    def _build_response(self, request, is_registered: bool, details: str):
        payload = {
            "iss": request.build_absolute_uri("/"),
            "iat": int(time.time()),
            "data": {"isRegistered": is_registered, "details": details},
        }
        try:
            from core.signing import KeyNotConfiguredError, sign_jwt

            token = sign_jwt(payload)
            response = Response(token, content_type="application/jwt")
            response["x-jku-url"] = request.build_absolute_uri(reverse("jwks"))
            return response
        except KeyNotConfiguredError:
            return Response(payload)
