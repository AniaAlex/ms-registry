"""
Serializers for Legal Entity models
"""

from core.models import Identifier, IdentifierType
from rest_framework import serializers

from .models import (
    LegalEntity,
    LegalEntityIdentifier,
    LegalPerson,
    NaturalPerson,
    PhysicalAddress,
)


class PhysicalAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhysicalAddress
        fields = [
            "id",
            "street_address",
            "locality",
            "region",
            "postal_code",
            "country_code",
            "address_type",
        ]
        read_only_fields = ["id"]


class LegalPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalPerson
        fields = [
            "id",
            "legal_name",
            "legal_form",
            "legal_form_uri",
            "registration_date",
            "governing_law",
        ]
        read_only_fields = ["id"]


class NaturalPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = NaturalPerson
        fields = [
            "id",
            "given_name",
            "family_name",
            "date_of_birth",
            "nationality",
        ]
        read_only_fields = ["id"]


class IdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Identifier
        fields = [
            "id",
            "identifier_type",
            "identifier_value",
            "issuing_authority",
            "issuing_authority_uri",
            "issuing_country",
        ]
        read_only_fields = ["id"]


class LegalEntityIdentifierSerializer(serializers.ModelSerializer):
    identifier = IdentifierSerializer(read_only=True)

    class Meta:
        model = LegalEntityIdentifier
        fields = ["id", "identifier", "is_primary"]


class LegalEntitySerializer(serializers.ModelSerializer):
    """Basic serializer for listing/retrieving legal entities"""

    legal_person = LegalPersonSerializer(read_only=True)
    natural_person = NaturalPersonSerializer(read_only=True)
    physical_address = PhysicalAddressSerializer(read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = LegalEntity
        fields = [
            "id",
            "entity_type",
            "legal_person",
            "natural_person",
            "physical_address",
            "email",
            "phone",
            "info_uri",
            "display_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LegalEntityCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a legal entity with all nested data in one request.
    Handles creating LegalPerson/NaturalPerson, PhysicalAddress, and Identifier.
    """

    # Entity type selection
    entity_type = serializers.ChoiceField(choices=["legal_person", "natural_person"])

    # Legal Person fields (required if entity_type == 'legal_person')
    legal_name = serializers.CharField(max_length=500, required=False, allow_blank=True)
    legal_form = serializers.CharField(
        max_length=200, required=False, allow_blank=True, allow_null=True
    )
    legal_form_uri = serializers.URLField(
        max_length=2048, required=False, allow_blank=True, allow_null=True
    )
    registration_date = serializers.DateField(required=False, allow_null=True)

    # Natural Person fields (required if entity_type == 'natural_person')
    given_name = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    family_name = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    nationality = serializers.CharField(
        max_length=2, required=False, allow_blank=True, allow_null=True
    )

    # Physical Address fields
    street_address = serializers.CharField(
        max_length=500, required=False, allow_blank=True, allow_null=True
    )
    locality = serializers.CharField(
        max_length=200, required=False, allow_blank=True, allow_null=True
    )
    region = serializers.CharField(
        max_length=200, required=False, allow_blank=True, allow_null=True
    )
    postal_code = serializers.CharField(
        max_length=20, required=False, allow_blank=True, allow_null=True
    )
    country_code = serializers.CharField(max_length=2, required=True)

    # Primary Identifier fields
    identifier_type = serializers.ChoiceField(
        choices=IdentifierType.choices, required=False
    )
    identifier_value = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    issuing_authority = serializers.CharField(
        max_length=500, required=False, allow_blank=True, allow_null=True
    )
    identifier_country_code = serializers.CharField(
        max_length=2, required=False, allow_blank=True, allow_null=True,
        help_text="Country code for the identifier (ISO 3166-1 alpha-2)"
    )

    # Contact info
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
        """Validate that required fields are present based on entity_type"""
        entity_type = data.get("entity_type")

        if entity_type == "legal_person":
            if not data.get("legal_name"):
                raise serializers.ValidationError(
                    {"legal_name": "Legal name is required for legal persons."}
                )
        elif entity_type == "natural_person":
            if not data.get("given_name"):
                raise serializers.ValidationError(
                    {"given_name": "Given name is required for natural persons."}
                )
            if not data.get("family_name"):
                raise serializers.ValidationError(
                    {"family_name": "Family name is required for natural persons."}
                )

        return data

    def create(self, validated_data):
        """Create all related objects and the legal entity"""
        entity_type = validated_data["entity_type"]

        # Create Physical Address
        address = None
        if validated_data.get("country_code"):
            address = PhysicalAddress.objects.create(
                street_address=validated_data.get("street_address") or None,
                locality=validated_data.get("locality") or None,
                region=validated_data.get("region") or None,
                postal_code=validated_data.get("postal_code") or None,
                country_code=validated_data["country_code"],
            )

        # Create Primary Identifier
        primary_identifier = None
        if validated_data.get("identifier_type") and validated_data.get(
            "identifier_value"
        ):
            primary_identifier = Identifier.objects.create(
                identifier_type=validated_data["identifier_type"],
                identifier_value=validated_data["identifier_value"],
                issuing_authority=validated_data.get("issuing_authority") or None,
                country_code=validated_data.get("identifier_country_code") or None,
            )

        # Create Legal Person or Natural Person
        legal_person = None
        natural_person = None

        if entity_type == "legal_person":
            legal_person = LegalPerson.objects.create(
                legal_name=validated_data["legal_name"],
                legal_form=validated_data.get("legal_form") or None,
                legal_form_uri=validated_data.get("legal_form_uri") or None,
                registration_date=validated_data.get("registration_date"),
            )
        else:
            natural_person = NaturalPerson.objects.create(
                given_name=validated_data["given_name"],
                family_name=validated_data["family_name"],
                date_of_birth=validated_data.get("date_of_birth"),
                nationality=validated_data.get("nationality") or None,
            )

        # Create Legal Entity
        legal_entity = LegalEntity.objects.create(
            entity_type=entity_type,
            legal_person=legal_person,
            natural_person=natural_person,
            physical_address=address,
            primary_identifier=primary_identifier,
            email=validated_data.get("email") or None,
            phone=validated_data.get("phone") or None,
            info_uri=validated_data.get("info_uri") or None,
        )

        # Link primary identifier through M2M
        if primary_identifier:
            LegalEntityIdentifier.objects.create(
                legal_entity=legal_entity,
                identifier=primary_identifier,
                is_primary=True,
            )

        return legal_entity
