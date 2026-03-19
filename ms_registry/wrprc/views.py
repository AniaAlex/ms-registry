"""
WRPRC Views

API endpoints for WRPRC issuance, status checking, and management.
"""

from rest_framework import generics, mixins, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import IssuedWRPRC, SigningKey, StatusList
from .serializers import (
    IssuedWRPRCSerializer,
    IssueWRPRCSerializer,
    RevokeWRPRCRequestSerializer,
    SigningKeySerializer,
    StatusListSerializer,
    StatusListTokenSerializer,
)


class IssueWRPRCView(mixins.CreateModelMixin, generics.GenericAPIView):
    """
    Issue a WRPRC for a registered entity.

    POST /api/wrprc/issue/
    """

    serializer_class = IssueWRPRCSerializer
    permission_classes = []  # TODO: Add authentication/authorization

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)


class EntityWRPRCListView(generics.ListAPIView):
    """
    List all WRPRCs issued to a specific entity.

    GET /api/wrprc/entity/<entity_id>/
    """

    serializer_class = IssuedWRPRCSerializer
    permission_classes = []

    def get_queryset(self):
        entity_id = self.kwargs["entity_id"]
        return IssuedWRPRC.objects.filter(registered_entity_id=entity_id).order_by(
            "-issued_at"
        )


class WRPRCDetailView(generics.RetrieveAPIView):
    """
    Get details of a specific WRPRC.

    GET /api/wrprc/<jti>/
    """

    serializer_class = IssuedWRPRCSerializer
    permission_classes = []
    lookup_field = "jti"
    queryset = IssuedWRPRC.objects.all()


class RevokeWRPRCView(APIView):
    """
    Revoke a WRPRC.

    POST /api/wrprc/<jti>/revoke/
    """

    permission_classes = []  # TODO: Add admin-only permission

    def post(self, request, jti):
        try:
            wrprc = IssuedWRPRC.objects.get(jti=jti)
        except IssuedWRPRC.DoesNotExist:
            return Response(
                {"error": "WRPRC not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if wrprc.status == IssuedWRPRC.Status.REVOKED:
            return Response(
                {"error": "WRPRC is already revoked"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RevokeWRPRCRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wrprc.revoke(reason=serializer.validated_data.get("reason", ""))

        return Response(IssuedWRPRCSerializer(wrprc).data, status=status.HTTP_200_OK)


class StatusListView(APIView):
    """
    Get a status list for revocation checking.

    GET /api/wrprc/status/<list_id>/

    Returns the status list in a format suitable for status list token verification.
    """

    permission_classes = []  # Public endpoint

    def get(self, request, list_id):
        try:
            status_list = StatusList.objects.get(list_id=list_id)
        except StatusList.DoesNotExist:
            return Response(
                {"error": "Status list not found"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            StatusListTokenSerializer(status_list).data, status=status.HTTP_200_OK
        )


class StatusListDetailView(generics.RetrieveAPIView):
    """
    Get metadata about a status list.

    GET /api/wrprc/status/<list_id>/meta/
    """

    serializer_class = StatusListSerializer
    permission_classes = []
    lookup_field = "list_id"
    queryset = StatusList.objects.all()


class SigningKeysView(generics.ListAPIView):
    """
    List public signing keys (for verification).

    GET /api/wrprc/keys/
    """

    serializer_class = SigningKeySerializer
    permission_classes = []

    def get_queryset(self):
        # Only return active and recently rotated keys
        return SigningKey.objects.filter(
            status__in=[SigningKey.KeyStatus.ACTIVE, SigningKey.KeyStatus.ROTATED]
        ).order_by("-valid_from")


class JWKSView(APIView):
    """
    Return signing keys in JWKS format.

    GET /api/wrprc/.well-known/jwks.json
    """

    permission_classes = []

    def get(self, request):
        keys = SigningKey.objects.filter(
            status__in=[SigningKey.KeyStatus.ACTIVE, SigningKey.KeyStatus.ROTATED]
        )

        jwks = {
            "keys": [
                {
                    **key.public_key_jwk,
                    "kid": key.kid,
                    "use": "sig",
                    "alg": key.algorithm,
                }
                for key in keys
            ]
        }

        return Response(jwks, status=status.HTTP_200_OK)
