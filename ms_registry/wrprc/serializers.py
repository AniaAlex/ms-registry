"""
WRPRC Serializers

Serializers for WRPRC API endpoints.
"""

from credentials.models import IntendedUse
from registry.models import RegisteredEntity
from rest_framework import serializers

from .issuer import WRPRCIssuer
from .models import IssuedWRPRC, SigningKey, StatusList


class StatusListSerializer(serializers.ModelSerializer):
    """Serializer for StatusList model."""

    uri = serializers.SerializerMethodField()

    class Meta:
        model = StatusList
        fields = [
            "id",
            "list_id",
            "purpose",
            "current_index",
            "capacity",
            "uri",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "current_index", "uri", "created_at", "updated_at"]

    def get_uri(self, obj):
        return obj.get_uri()


class IssuedWRPRCSerializer(serializers.ModelSerializer):
    """Serializer for IssuedWRPRC model."""

    entity_name = serializers.CharField(
        source="registered_entity.legal_entity.legal_name", read_only=True
    )
    status_list_uri = serializers.CharField(
        source="status_list.get_uri", read_only=True
    )
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = IssuedWRPRC
        fields = [
            "id",
            "jti",
            "registered_entity",
            "entity_name",
            "intended_use",
            "status",
            "status_list_uri",
            "status_list_index",
            "issued_at",
            "expires_at",
            "revoked_at",
            "revocation_reason",
            "is_valid",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "jti",
            "entity_name",
            "status_list_uri",
            "status_list_index",
            "issued_at",
            "revoked_at",
            "is_valid",
            "created_at",
            "updated_at",
        ]

    def get_is_valid(self, obj):
        return obj.is_valid()


class IssueWRPRCSerializer(serializers.Serializer):
    """
    Serializer for WRPRC issuance.

    Handles validation of input and creation of WRPRC via the issuer.
    Used with CreateModelMixin.
    """

    # Input fields
    registered_entity_id = serializers.UUIDField(
        write_only=True, help_text="UUID of the registered entity"
    )
    intended_use_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        write_only=True,
        help_text="UUID of specific intended use (optional)",
    )
    validity_days = serializers.IntegerField(
        default=365,
        min_value=1,
        max_value=730,
        write_only=True,
        help_text="Validity period in days (default: 365)",
    )

    # Output fields
    jwt = serializers.CharField(read_only=True, help_text="The signed WRPRC JWT")
    jti = serializers.CharField(read_only=True, help_text="JWT ID for tracking")
    expires_at = serializers.DateTimeField(
        read_only=True, help_text="Expiration timestamp"
    )
    status_list_uri = serializers.URLField(
        read_only=True, help_text="URI for revocation checking"
    )
    status_list_index = serializers.IntegerField(
        read_only=True, help_text="Index in status list"
    )

    def validate_registered_entity_id(self, value):
        """Validate that the entity exists and is active."""
        try:
            entity = RegisteredEntity.objects.get(id=value)
        except RegisteredEntity.DoesNotExist:
            raise serializers.ValidationError("Registered entity not found")

        if entity.status != "active":
            raise serializers.ValidationError(
                f"Cannot issue WRPRC for entity with status: {entity.status}"
            )

        return value

    def validate(self, attrs):
        """Cross-field validation for intended_use."""
        entity_id = attrs.get("registered_entity_id")
        intended_use_id = attrs.get("intended_use_id")

        if intended_use_id:
            try:
                IntendedUse.objects.get(
                    id=intended_use_id,
                    registered_entity_id=entity_id,
                )
            except IntendedUse.DoesNotExist:
                raise serializers.ValidationError(
                    {"intended_use_id": "Intended use not found for this entity"}
                )

        return attrs

    def create(self, validated_data):
        """Issue the WRPRC and return result data."""
        entity = RegisteredEntity.objects.get(id=validated_data["registered_entity_id"])

        intended_use = None
        if validated_data.get("intended_use_id"):
            intended_use = IntendedUse.objects.get(id=validated_data["intended_use_id"])

        issuer = WRPRCIssuer()
        result = issuer.issue(
            registered_entity=entity,
            intended_use=intended_use,
            validity_days=validated_data["validity_days"],
        )

        # Return a dict that matches our output fields
        return {
            "jwt": result["jwt"],
            "jti": result["record"].jti,
            "expires_at": result["expires_at"],
            "status_list_uri": result["record"].status_list.get_uri(),
            "status_list_index": result["record"].status_list_index,
        }


# Keep for backwards compatibility
IssueWRPRCRequestSerializer = IssueWRPRCSerializer
IssueWRPRCResponseSerializer = IssueWRPRCSerializer


class RevokeWRPRCRequestSerializer(serializers.Serializer):
    """Serializer for WRPRC revocation request."""

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Reason for revocation",
    )


class SigningKeySerializer(serializers.ModelSerializer):
    """Serializer for SigningKey model (public info only)."""

    class Meta:
        model = SigningKey
        fields = [
            "id",
            "kid",
            "algorithm",
            "status",
            "public_key_jwk",
            "valid_from",
            "valid_until",
            "created_at",
        ]
        read_only_fields = fields


class StatusListTokenSerializer(serializers.Serializer):
    """
    Serializer for Status List Token response.

    Returns the status list in the format expected by verifiers.
    """

    status_list = serializers.SerializerMethodField()

    def get_status_list(self, obj):
        import base64
        import zlib

        # Compress and base64 encode the bits
        compressed = zlib.compress(obj.bits)
        encoded = base64.urlsafe_b64encode(compressed).decode().rstrip("=")

        return {
            "bits": encoded,
            "lst": encoded,  # Alternative field name used in some specs
        }
