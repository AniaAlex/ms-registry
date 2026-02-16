from core.models import EntitlementType
from rest_framework import serializers

from .models import EntityEntitlement, RegisteredEntity, SupervisoryAuthority


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


class EntityEntitlementSerializer(serializers.ModelSerializer):
    """Serializer for entity entitlements"""

    class Meta:
        model = EntityEntitlement
        fields = [
            "id",
            "entitlement_uri",
            "entitlement_type",
            "granted_at",
            "expires_at",
            "is_active",
        ]
        read_only_fields = ["id", "granted_at"]


class RegisteredEntitySerializer(serializers.ModelSerializer):
    """Serializer for creating and listing registered entities"""

    # Accept entitlements as a list of entitlement type values
    entitlements = serializers.ListField(
        child=serializers.ChoiceField(choices=EntitlementType.choices),
        write_only=True,
        required=False,
        help_text="List of entitlement types (e.g., Service_Provider, PID_Provider)",
    )
    # For reading, return the full entitlement objects
    entity_entitlements = EntityEntitlementSerializer(
        source="entitlements", many=True, read_only=True
    )

    class Meta:
        model = RegisteredEntity
        fields = [
            "id",
            "legal_entity",
            "entity_role",
            "trade_name",
            "is_psb",
            "is_intermediary",
            "registry_uri",
            "supervisory_authority",
            "registration_status",
            "registered_at",
            "created_at",
            "updated_at",
            "entitlements",  # write-only input
            "entity_entitlements",  # read-only output
        ]
        read_only_fields = [
            "id",
            "registration_status",
            "registered_at",
            "created_at",
            "updated_at",
        ]

    def validate_entitlements(self, value):
        """Validate that at least one entitlement is provided"""
        if not value:
            raise serializers.ValidationError(
                "At least one entitlement is required."
            )
        return value

    def create(self, validated_data):
        """Create RegisteredEntity and associated EntityEntitlements"""
        entitlement_types = validated_data.pop("entitlements", [])

        # Create the registered entity
        registered_entity = RegisteredEntity.objects.create(**validated_data)

        # Create entitlements for the entity
        for entitlement_type in entitlement_types:
            entitlement_uri = f"https://uri.etsi.org/19475/Entitlement/{entitlement_type}"
            EntityEntitlement.objects.create(
                registered_entity=registered_entity,
                entitlement_uri=entitlement_uri,
                entitlement_type=entitlement_type,
            )

        return registered_entity

    def update(self, instance, validated_data):
        """Update RegisteredEntity and associated EntityEntitlements"""
        entitlement_types = validated_data.pop("entitlements", None)

        # Update entity fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update entitlements if provided
        if entitlement_types is not None:
            # Remove existing entitlements
            instance.entitlements.all().delete()

            # Create new entitlements
            for entitlement_type in entitlement_types:
                entitlement_uri = f"https://uri.etsi.org/19475/Entitlement/{entitlement_type}"
                EntityEntitlement.objects.create(
                    registered_entity=instance,
                    entitlement_uri=entitlement_uri,
                    entitlement_type=entitlement_type,
                )

        return instance
