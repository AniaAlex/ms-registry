"""
Serializers for TSL Generator models
"""

from legal_entities.models import LegalEntity
from rest_framework import serializers

from .models import (SERVICE_STATUS_CHOICES, SERVICE_TYPE_CHOICES,
                     ServiceCertificate, ServiceName, TrustService,
                     TrustServiceProvider, TSLScheme, TSPElectronicAddress,
                     TSPName, TSPTradeName)


class TSPNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = TSPName
        fields = ["id", "language", "value"]
        read_only_fields = ["id"]


class TSPTradeNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = TSPTradeName
        fields = ["id", "language", "value"]
        read_only_fields = ["id"]


class TSPElectronicAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = TSPElectronicAddress
        fields = ["id", "uri"]
        read_only_fields = ["id"]


class TrustServiceProviderSerializer(serializers.ModelSerializer):
    """Serializer for listing/retrieving TSPs"""

    names = TSPNameSerializer(many=True, read_only=True)
    trade_names = TSPTradeNameSerializer(many=True, read_only=True)
    electronic_addresses = TSPElectronicAddressSerializer(many=True, read_only=True)
    legal_entity_name = serializers.CharField(
        source="legal_entity.display_name", read_only=True
    )
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)

    class Meta:
        model = TrustServiceProvider
        fields = [
            "id",
            "scheme",
            "scheme_name",
            "legal_entity",
            "legal_entity_name",
            "names",
            "trade_names",
            "electronic_addresses",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TrustServiceProviderCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a Trust Service Provider with nested data.
    """

    # Required: TSL Scheme
    scheme = serializers.PrimaryKeyRelatedField(queryset=TSLScheme.objects.all())

    # Required: Legal Entity
    legal_entity = serializers.PrimaryKeyRelatedField(
        queryset=LegalEntity.objects.all()
    )

    # TSP Name (at least one required)
    name = serializers.CharField(max_length=500)
    name_language = serializers.CharField(max_length=5, default="en")

    # Optional: Trade name
    trade_name = serializers.CharField(max_length=500, required=False, allow_blank=True)
    trade_name_language = serializers.CharField(max_length=5, default="en")

    # Optional: Electronic address (website, email)
    electronic_address = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )

    # Optional: Service type for initial service
    service_type = serializers.ChoiceField(
        choices=SERVICE_TYPE_CHOICES, required=False, allow_blank=True
    )
    service_name = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )

    def validate(self, data):
        """Validate uniqueness of scheme + legal_entity"""
        scheme = data.get("scheme")
        legal_entity = data.get("legal_entity")

        if TrustServiceProvider.objects.filter(
            scheme=scheme, legal_entity=legal_entity
        ).exists():
            raise serializers.ValidationError(
                {
                    "legal_entity": (
                        "This legal entity is already registered as a "
                        "Trust Service Provider in this TSL scheme."
                    )
                }
            )

        return data

    def create(self, validated_data):
        """Create TSP with related names and addresses"""
        # Extract nested data
        name = validated_data.pop("name")
        name_language = validated_data.pop("name_language", "en")
        trade_name = validated_data.pop("trade_name", None)
        trade_name_language = validated_data.pop("trade_name_language", "en")
        electronic_address = validated_data.pop("electronic_address", None)
        service_type = validated_data.pop("service_type", None)
        service_name = validated_data.pop("service_name", None)

        # Create TSP
        tsp = TrustServiceProvider.objects.create(
            scheme=validated_data["scheme"],
            legal_entity=validated_data["legal_entity"],
            is_active=True,
        )

        # Create TSP Name
        TSPName.objects.create(
            provider=tsp,
            language=name_language,
            value=name,
        )

        # Create Trade Name if provided
        if trade_name:
            TSPTradeName.objects.create(
                provider=tsp,
                language=trade_name_language,
                value=trade_name,
            )

        # Create Electronic Address if provided
        if electronic_address:
            TSPElectronicAddress.objects.create(
                provider=tsp,
                uri=electronic_address,
            )

        # Create initial Trust Service if service_type provided
        if service_type and service_name:
            TrustService.objects.create(
                provider=tsp,
                service_type=service_type,
                is_active=True,
            )

        return tsp


class TSLSchemeSerializer(serializers.ModelSerializer):
    """Serializer for listing TSL Schemes"""

    class Meta:
        model = TSLScheme
        fields = [
            "id",
            "name",
            "territory",
            "tsl_type",
            "sequence_number",
            "is_active",
        ]


# =============================================================================
# Trust Service Serializers
# =============================================================================
class ServiceNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceName
        fields = ["id", "language", "value"]
        read_only_fields = ["id"]


class ServiceCertificateSerializer(serializers.ModelSerializer):
    """Serializer for listing/retrieving Service Certificates"""

    class Meta:
        model = ServiceCertificate
        fields = [
            "id",
            "service",
            "certificate_pem",
            "subject_cn",
            "issuer_cn",
            "serial_number",
            "not_before",
            "not_after",
            "x509_subject_name",
            "x509_ski",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "subject_cn",
            "issuer_cn",
            "serial_number",
            "not_before",
            "not_after",
            "x509_subject_name",
            "x509_ski",
            "created_at",
            "updated_at",
        ]


class TrustServiceSerializer(serializers.ModelSerializer):
    """Serializer for listing/retrieving Trust Services"""

    names = ServiceNameSerializer(many=True, read_only=True)
    certificates = ServiceCertificateSerializer(many=True, read_only=True)
    provider_name = serializers.CharField(source="provider.__str__", read_only=True)
    scheme_name = serializers.CharField(source="provider.scheme.name", read_only=True)

    class Meta:
        model = TrustService
        fields = [
            "id",
            "provider",
            "provider_name",
            "scheme_name",
            "service_type",
            "status",
            "status_starting_time",
            "names",
            "certificates",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TrustServiceCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a Trust Service with optional inline TSP creation.
    """

    # TSL Scheme selection (required)
    scheme = serializers.PrimaryKeyRelatedField(queryset=TSLScheme.objects.all())

    # Trust Service Provider - either existing or create new
    provider = serializers.PrimaryKeyRelatedField(
        queryset=TrustServiceProvider.objects.all(),
        required=False,
        allow_null=True,
    )

    # Fields for creating new TSP (if provider not selected)
    create_new_provider = serializers.BooleanField(default=False)
    legal_entity = serializers.PrimaryKeyRelatedField(
        queryset=LegalEntity.objects.all(),
        required=False,
        allow_null=True,
    )
    provider_name = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    provider_name_language = serializers.CharField(max_length=5, default="en")
    trade_name = serializers.CharField(max_length=500, required=False, allow_blank=True)
    trade_name_language = serializers.CharField(max_length=5, default="en")
    electronic_address = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )

    # Service Information (required)
    service_name = serializers.CharField(max_length=500)
    service_name_language = serializers.CharField(max_length=5, default="en")
    service_type = serializers.ChoiceField(
        choices=SERVICE_TYPE_CHOICES,
        default="http://uri.etsi.org/TrstSvc/Svctype/CA/QC",
    )
    service_status = serializers.ChoiceField(
        choices=SERVICE_STATUS_CHOICES,
        default="http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted",
    )

    # Optional: Certificate (PEM format)
    certificate_pem = serializers.CharField(required=False, allow_blank=True)

    def validate_certificate_pem(self, value):
        """Validate certificate PEM format"""
        if not value:
            return value

        value = value.strip()
        if not value.startswith("-----BEGIN CERTIFICATE-----"):
            raise serializers.ValidationError(
                "Certificate must be in PEM format starting with "
                "'-----BEGIN CERTIFICATE-----'"
            )
        if not value.endswith("-----END CERTIFICATE-----"):
            raise serializers.ValidationError(
                "Certificate must be in PEM format ending with "
                "'-----END CERTIFICATE-----'"
            )
        return value

    def validate(self, data):
        """Validate that either provider is selected or new provider data is provided"""
        provider = data.get("provider")
        create_new_provider = data.get("create_new_provider", False)

        if not provider and not create_new_provider:
            raise serializers.ValidationError(
                {
                    "provider": "Please select an existing Trust Service Provider or create a new one."
                }
            )

        if create_new_provider:
            if not data.get("legal_entity"):
                raise serializers.ValidationError(
                    {
                        "legal_entity": "Legal entity is required when creating a new provider."
                    }
                )
            if not data.get("provider_name"):
                raise serializers.ValidationError(
                    {
                        "provider_name": "Provider name is required when creating a new provider."
                    }
                )

            # Check for duplicate TSP (same scheme + legal entity)
            scheme = data.get("scheme")
            legal_entity = data.get("legal_entity")
            if TrustServiceProvider.objects.filter(
                scheme=scheme, legal_entity=legal_entity
            ).exists():
                raise serializers.ValidationError(
                    {
                        "legal_entity": "This legal entity is already registered as a TSP in this TSL scheme."
                    }
                )

        return data

    def create(self, validated_data):
        """Create Trust Service with optional new TSP"""
        # Extract fields
        scheme = validated_data["scheme"]
        provider = validated_data.get("provider")
        create_new_provider = validated_data.get("create_new_provider", False)

        # Service data
        service_name = validated_data["service_name"]
        service_name_language = validated_data.get("service_name_language", "en")
        service_type = validated_data.get("service_type")
        service_status = validated_data.get("service_status")

        # Create new TSP if requested
        if create_new_provider and not provider:
            provider = TrustServiceProvider.objects.create(
                scheme=scheme,
                legal_entity=validated_data["legal_entity"],
                is_active=True,
            )

            # Create TSP Name
            TSPName.objects.create(
                provider=provider,
                language=validated_data.get("provider_name_language", "en"),
                value=validated_data["provider_name"],
            )

            # Create Trade Name if provided
            trade_name = validated_data.get("trade_name")
            if trade_name:
                TSPTradeName.objects.create(
                    provider=provider,
                    language=validated_data.get("trade_name_language", "en"),
                    value=trade_name,
                )

            # Create Electronic Address if provided
            electronic_address = validated_data.get("electronic_address")
            if electronic_address:
                TSPElectronicAddress.objects.create(
                    provider=provider,
                    uri=electronic_address,
                )

        # Create the Trust Service
        service = TrustService.objects.create(
            provider=provider,
            service_type=service_type,
            status=service_status,
            is_active=True,
        )

        # Create Service Name
        ServiceName.objects.create(
            service=service,
            language=service_name_language,
            value=service_name,
        )

        # Create Service Certificate if provided
        certificate_pem = validated_data.get("certificate_pem")
        if certificate_pem:
            cert = ServiceCertificate.objects.create(
                service=service,
                certificate_pem=certificate_pem,
            )
            # Extract metadata from PEM (if cryptography library is available)
            cert.extract_metadata_from_pem()
            cert.save()

        return service
