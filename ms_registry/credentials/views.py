from datetime import date

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from registry.models import RegisteredEntity
from rest_framework import status
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

    permission_classes = []

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

    permission_classes = []

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
