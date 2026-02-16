from rest_framework import serializers

from .models import RegisteredEntity, SupervisoryAuthority


class SupervisoryAuthoritySerializer(serializers.ModelSerializer):
    """Serializer for listing/retrieving supervisory authorities"""

    class Meta:
        model = SupervisoryAuthority
        fields = [
            "id",
            "legal_entity",
            "authority_name",
            "country_code",
            "email",
            "phone",
            "info_uri",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SupervisoryAuthorityCreateSerializer(serializers.Serializer):
    """Serializer for creating a supervisory authority"""

    # Required fields
    authority_name = serializers.CharField(max_length=500)
    country_code = serializers.CharField(max_length=2)

    # Optional: link to existing legal entity
    legal_entity = serializers.UUIDField(required=False, allow_null=True)

    # Contact info (at least one required)
    email = serializers.EmailField(
        max_length=320, required=False, allow_blank=True, allow_null=True
    )
    phone = serializers.CharField(
        max_length=50, required=False, allow_blank=True, allow_null=True
    )
    info_uri = serializers.URLField(
        max_length=2048, required=False, allow_blank=True, allow_null=True
    )

    def validate(self, data):
        """At least one contact method required"""
        email = data.get("email")
        phone = data.get("phone")
        info_uri = data.get("info_uri")

        if not any([email, phone, info_uri]):
            raise serializers.ValidationError(
                "At least one of email, phone, or info_uri must be provided."
            )

        return data

    def create(self, validated_data):
        from legal_entities.models import LegalEntity

        legal_entity_id = validated_data.pop("legal_entity", None)
        legal_entity = None

        if legal_entity_id:
            try:
                legal_entity = LegalEntity.objects.get(id=legal_entity_id)
            except LegalEntity.DoesNotExist:
                pass

        return SupervisoryAuthority.objects.create(
            legal_entity=legal_entity,
            authority_name=validated_data["authority_name"],
            country_code=validated_data["country_code"],
            email=validated_data.get("email") or None,
            phone=validated_data.get("phone") or None,
            info_uri=validated_data.get("info_uri") or None,
        )


class RegisteredEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RegisteredEntity
        fields = "__all__"
