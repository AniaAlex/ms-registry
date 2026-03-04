from core.models import EntitlementType
from rest_framework import serializers

from .models import EntityEntitlement, RegisteredEntity, SupervisoryAuthority


class WRPQueryParameterSerializer(serializers.Serializer):
    """Query parameters for filtering WalletRelyingParty list endpoint."""

    entitlement = serializers.URLField(
        required=False,
        allow_null=True,
        help_text=(
            "Filter by entitlement URI. Example: "
            "http://data.europa.eu/eudi/entitlement/PUB_EAA_Provider"
        ),
    )
    isintermediary = serializers.BooleanField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Filter by intermediary status. Set to true or false.",
    )


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
            raise serializers.ValidationError("At least one entitlement is required.")
        return value

    def create(self, validated_data):
        """Create RegisteredEntity and associated EntityEntitlements"""
        entitlement_types = validated_data.pop("entitlements", [])

        # Create the registered entity
        registered_entity = RegisteredEntity.objects.create(**validated_data)

        # Create entitlements for the entity
        for entitlement_type in entitlement_types:
            entitlement_uri = (
                f"https://uri.etsi.org/19475/Entitlement/{entitlement_type}"
            )
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
                entitlement_uri = (
                    f"https://uri.etsi.org/19475/Entitlement/{entitlement_type}"
                )
                EntityEntitlement.objects.create(
                    registered_entity=instance,
                    entitlement_uri=entitlement_uri,
                    entitlement_type=entitlement_type,
                )

        return instance


class WalletRelyingPartySerializer(serializers.Serializer):
    """
    Serializer for WalletRelyingParty per TS5 specification.

    This serializer follows the WalletRelyingParty schema from:
    https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/
    blob/main/docs/technical-specifications/ts5-common-formats-and-api-for-rp-registration-information.md

    The /wrp endpoint supports:
    - POST: Create a new WalletRelyingParty (returns 201)
    - PUT: Update an existing WalletRelyingParty (returns 200 or 404)
    - DELETE: Delete an existing WalletRelyingParty (returns 204)
    """

    # Identifier - required for PUT and DELETE, generated for POST
    id = serializers.UUIDField(
        required=False, help_text="Unique identifier for the WRP"
    )

    # Legal entity identifier (e.g., EUID, LEI)
    legal_entity_identifier = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Legal entity identifier (EUID, LEI, national ID)",
    )
    legal_entity_identifier_type = serializers.CharField(
        max_length=50,
        required=True,
        help_text="Type of identifier (EUID, LEI, NATIONAL_ID)",
    )

    # Legal name
    legal_name = serializers.CharField(
        max_length=500,
        required=True,
        help_text="Official legal name of the organization",
    )

    # Trade name (optional)
    trade_name = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Common/service name",
    )

    # Country code
    country_code = serializers.CharField(
        max_length=2,
        required=True,
        help_text="ISO 3166-1 alpha-2 country code",
    )

    # Entitlements [1..*]
    entitlements = serializers.ListField(
        child=serializers.URLField(),
        required=True,
        min_length=1,
        help_text="List of ETSI entitlement URIs",
    )

    # Support URIs [1..*]
    support_uris = serializers.ListField(
        child=serializers.URLField(),
        required=True,
        min_length=1,
        help_text="Support URIs for the relying party",
    )

    # isPSB - Public Sector Body flag
    is_psb = serializers.BooleanField(
        default=False,
        help_text="Indicates if entity is a public sector body",
    )

    # isIntermediary - Intermediary flag (only for RPs)
    is_intermediary = serializers.BooleanField(
        default=False,
        help_text="Indicates if entity acts as an intermediary",
    )

    # Registry URI (provided by registrar)
    registry_uri = serializers.URLField(
        max_length=2048,
        required=False,
        allow_blank=True,
        help_text="National registry API URI",
    )

    # Supervisory Authority
    supervisory_authority_name = serializers.CharField(
        max_length=500,
        required=True,
        help_text="Name of the supervisory authority (DPA)",
    )
    supervisory_authority_country = serializers.CharField(
        max_length=2,
        required=True,
        help_text="Country code of the supervisory authority",
    )

    # Service descriptions (optional, multilingual)
    service_descriptions = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of {lang: 'en', content: '...'} objects (MultiLangString)",
    )

    # Policies (optional)
    policies = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        help_text="List of policy URIs",
    )

    # Uses intermediaries (optional, for non-intermediary RPs)
    uses_intermediaries = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of intermediary WRP IDs this entity uses",
    )

    def validate(self, data):
        """Validate WalletRelyingParty data"""
        # Intermediary cannot use other intermediaries
        if data.get("is_intermediary") and data.get("uses_intermediaries"):
            raise serializers.ValidationError(
                "An intermediary cannot use other intermediaries"
            )
        return data

    def create(self, validated_data):
        """
        Create a new WalletRelyingParty.
        This creates the underlying LegalEntity and RegisteredEntity.
        """
        from core.models import EntityRole, IdentifierType
        from legal_entities.models import Identifier, LegalEntity

        # Extract nested data
        entitlement_uris = validated_data.pop("entitlements", [])
        support_uri_list = validated_data.pop("support_uris", [])
        service_descriptions = validated_data.pop("service_descriptions", [])
        policy_uris = validated_data.pop("policies", [])
        intermediary_ids = validated_data.pop("uses_intermediaries", [])

        # Get or create supervisory authority
        from .models import SupervisoryAuthority

        supervisory_authority, _ = SupervisoryAuthority.objects.get_or_create(
            authority_name=validated_data.pop("supervisory_authority_name"),
            country_code=validated_data.pop("supervisory_authority_country"),
            defaults={"info_uri": "https://example.com"},  # Placeholder
        )

        # Create or get legal entity
        legal_entity, created = LegalEntity.objects.get_or_create(
            display_name=validated_data["legal_name"],
            defaults={
                "country_code": validated_data["country_code"],
            },
        )

        # Create identifier for legal entity
        if created:
            Identifier.objects.create(
                legal_entity=legal_entity,
                identifier_type=validated_data.get(
                    "legal_entity_identifier_type", IdentifierType.EUID
                ),
                value=validated_data["legal_entity_identifier"],
                is_primary=True,
            )

        # Create registered entity (WRP)
        from .models import (
            EntityEntitlement,
            EntityServiceDescription,
            EntitySupportURI,
            EntityUsesIntermediary,
            RegisteredEntity,
            RegisteredEntityPolicy,
        )

        registered_entity = RegisteredEntity.objects.create(
            legal_entity=legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            trade_name=validated_data.get("trade_name"),
            is_psb=validated_data.get("is_psb", False),
            is_intermediary=validated_data.get("is_intermediary", False),
            registry_uri=validated_data.get("registry_uri", ""),
            supervisory_authority=supervisory_authority,
        )

        # Create entitlements
        for uri in entitlement_uris:
            # Extract type from URI
            entitlement_type = uri.split("/")[-1] if "/" in uri else "Service_Provider"
            EntityEntitlement.objects.create(
                registered_entity=registered_entity,
                entitlement_uri=uri,
                entitlement_type=entitlement_type,
            )

        # Create support URIs
        for idx, uri in enumerate(support_uri_list):
            EntitySupportURI.objects.create(
                registered_entity=registered_entity,
                support_uri=uri,
                is_primary=(idx == 0),
            )

        # Create service descriptions
        for desc in service_descriptions:
            EntityServiceDescription.objects.create(
                registered_entity=registered_entity,
                lang=desc.get("lang", "en"),
                content=desc.get("content", ""),
            )

        # Create policy links
        from core.models import Policy

        for uri in policy_uris:
            policy, _ = Policy.objects.get_or_create(uri=uri)
            RegisteredEntityPolicy.objects.create(
                registered_entity=registered_entity,
                policy=policy,
            )

        # Create intermediary relationships
        for intermediary_id in intermediary_ids:
            try:
                intermediary = RegisteredEntity.objects.get(
                    id=intermediary_id, is_intermediary=True
                )
                EntityUsesIntermediary.objects.create(
                    registered_entity=registered_entity,
                    intermediary=intermediary,
                )
            except RegisteredEntity.DoesNotExist:
                pass  # Skip invalid intermediary references

        return registered_entity

    def update(self, instance, validated_data):
        """Update an existing WalletRelyingParty"""
        from .models import (
            EntityEntitlement,
            EntityServiceDescription,
            EntitySupportURI,
        )

        # Update basic fields
        if "trade_name" in validated_data:
            instance.trade_name = validated_data["trade_name"]
        if "is_psb" in validated_data:
            instance.is_psb = validated_data["is_psb"]
        if "is_intermediary" in validated_data:
            instance.is_intermediary = validated_data["is_intermediary"]
        if "registry_uri" in validated_data:
            instance.registry_uri = validated_data["registry_uri"]

        instance.save()

        # Update entitlements if provided
        if "entitlements" in validated_data:
            instance.entitlements.all().delete()
            for uri in validated_data["entitlements"]:
                entitlement_type = (
                    uri.split("/")[-1] if "/" in uri else "Service_Provider"
                )
                EntityEntitlement.objects.create(
                    registered_entity=instance,
                    entitlement_uri=uri,
                    entitlement_type=entitlement_type,
                )

        # Update support URIs if provided
        if "support_uris" in validated_data:
            instance.support_uris.all().delete()
            for idx, uri in enumerate(validated_data["support_uris"]):
                EntitySupportURI.objects.create(
                    registered_entity=instance,
                    support_uri=uri,
                    is_primary=(idx == 0),
                )

        # Update service descriptions if provided
        if "service_descriptions" in validated_data:
            instance.service_descriptions.all().delete()
            for desc in validated_data["service_descriptions"]:
                EntityServiceDescription.objects.create(
                    registered_entity=instance,
                    lang=desc.get("lang", "en"),
                    content=desc.get("content", ""),
                )

        return instance

    def to_representation(self, instance):
        """
        Convert RegisteredEntity to WalletRelyingParty schema per TS5.
        Reference: https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/  # noqa: E501
        blob/main/docs/technical-specifications/api/ts5-json-common-rp-data-model.json
        """
        # Build identifier array (TS5: array of {identifier, type})
        identifiers = []
        if instance.legal_entity.primary_identifier:
            primary_id = instance.legal_entity.primary_identifier
            identifiers.append(
                {
                    "identifier": primary_id.identifier_value,
                    "type": primary_id.identifier_type,
                }
            )
        # Add additional identifiers
        for link in instance.legal_entity.entity_identifiers.exclude(
            identifier=instance.legal_entity.primary_identifier
        ):
            identifiers.append(
                {
                    "identifier": link.identifier.identifier_value,
                    "type": link.identifier.identifier_type,
                }
            )

        # Build supervisoryAuthority object (TS5: nested object)
        supervisory_authority = None
        if instance.supervisory_authority:
            sa = instance.supervisory_authority
            supervisory_authority = {
                "name": sa.authority_name,
                "country": sa.country_code,
            }
            if sa.email:
                supervisory_authority["email"] = [sa.email]
            if sa.phone:
                supervisory_authority["phone"] = [sa.phone]
            if sa.info_uri:
                supervisory_authority["formURI"] = [sa.info_uri]

        # Build intendedUse array (TS5: array with purpose, credentials, claims)
        intended_use = []
        for iu in instance.intended_uses.all():
            # Build purpose array (multilingual)
            purposes = [
                {"lang": p.lang, "content": p.content} for p in iu.purposes.all()
            ]

            # Build credentials array with claims
            credentials = []
            for cred_link in iu.credential_links.select_related("credential"):
                cred = cred_link.credential
                cred_data = {
                    "format": cred.format,
                    "meta": cred.meta,
                }
                # Add claims for this credential
                claims = [
                    {"path": claim.path, "values": claim.values}
                    for claim in cred.claims.all()
                ]
                if claims:
                    cred_data["claims"] = claims
                credentials.append(cred_data)

            # Build privacyPolicy: single Policy object {policyURI, type}
            privacy_policy = None
            primary_pp = iu.privacy_policies.filter(is_primary=True).first()
            if not primary_pp:
                primary_pp = iu.privacy_policies.first()
            if primary_pp:
                privacy_policy = {
                    "policyURI": primary_pp.policy.policy_uri,
                    "type": primary_pp.policy.policy_type,
                }

            intended_use.append(
                {
                    "intendedUseIdentifier": iu.intended_use_identifier,
                    "purpose": purposes,
                    "credentials": credentials,
                    "privacyPolicy": privacy_policy,
                    "createdAt": iu.validity_start.isoformat(),
                    "revokedAt": (
                        iu.validity_end.isoformat() if iu.validity_end else None
                    ),
                }
            )

        # Build srvDescription (TS5: array of arrays of MultiLangString)
        srv_descriptions = list(instance.service_descriptions.all())
        srv_description = (
            [[{"lang": d.lang, "content": d.content} for d in srv_descriptions]]
            if srv_descriptions
            else None
        )

        # Build usesIntermediary (TS5: array of full WRP objects)
        uses_intermediary = [
            self.to_representation(ui.intermediary)
            for ui in instance.used_intermediaries.select_related("intermediary")
        ]

        # Build providesAttestations (TS5: [{format, meta}])
        provides_attestations = [
            {"format": pa.credential.format, "meta": pa.credential.meta}
            for pa in instance.provided_attestations.select_related("credential")
        ]

        # Build policy list (Provider base: [{policyURI, type}])
        policy = [
            {"policyURI": pl.policy.policy_uri, "type": pl.policy.policy_type}
            for pl in instance.policy_links.select_related("policy")
        ]

        # TS5 compliant response
        return {
            "id": str(instance.id),
            "identifier": identifiers,
            "legalName": instance.legal_entity.display_name,
            "tradeName": instance.trade_name,
            "entitlements": [e.entitlement_uri for e in instance.entitlements.all()],
            "intendedUse": intended_use if intended_use else None,
            "srvDescription": srv_description,
            "supervisoryAuthority": supervisory_authority,
            "supportURI": [s.support_uri for s in instance.support_uris.all()],
            "registryURI": instance.registry_uri or None,
            "isIntermediary": instance.is_intermediary,
            "usesIntermediary": uses_intermediary if uses_intermediary else None,
            "isPSB": instance.is_psb,
            "providesAttestations": (
                provides_attestations if provides_attestations else None
            ),
            "policy": policy if policy else None,
        }


# ---------------------------------------------------------------------------
# TS5 Response Serializers (for Swagger / drf-spectacular schema generation)
# These mirror the to_representation output of WalletRelyingPartySerializer.
# ---------------------------------------------------------------------------


class _MultiLangStringSerializer(serializers.Serializer):
    lang = serializers.CharField()
    content = serializers.CharField()


class _IdentifierSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    type = serializers.CharField()


class _PolicyResponseSerializer(serializers.Serializer):
    policyURI = serializers.URLField()
    type = serializers.CharField()


class _ClaimResponseSerializer(serializers.Serializer):
    path = serializers.CharField()


class _CredentialResponseSerializer(serializers.Serializer):
    format = serializers.CharField()
    meta = serializers.JSONField()
    claims = _ClaimResponseSerializer(many=True, required=False)


class _IntendedUseResponseSerializer(serializers.Serializer):
    intendedUseIdentifier = serializers.CharField()
    purpose = _MultiLangStringSerializer(many=True)
    credentials = _CredentialResponseSerializer(many=True)
    privacyPolicy = _PolicyResponseSerializer(allow_null=True, required=False)
    createdAt = serializers.CharField()
    revokedAt = serializers.CharField(allow_null=True)


class _SupervisoryAuthorityResponseSerializer(serializers.Serializer):
    name = serializers.CharField()
    country = serializers.CharField()
    email = serializers.ListField(child=serializers.CharField(), required=False)
    phone = serializers.ListField(child=serializers.CharField(), required=False)
    formURI = serializers.ListField(child=serializers.URLField(), required=False)


class _ProvidedAttestationResponseSerializer(serializers.Serializer):
    format = serializers.CharField()
    meta = serializers.JSONField()


class WalletRelyingPartyResponseSerializer(serializers.Serializer):
    """Read-only serializer matching WalletRelyingPartySerializer.to_representation output."""  # noqa: E501

    id = serializers.UUIDField()
    identifier = _IdentifierSerializer(many=True)
    legalName = serializers.CharField()
    tradeName = serializers.CharField(allow_null=True)
    entitlements = serializers.ListField(child=serializers.CharField())
    intendedUse = _IntendedUseResponseSerializer(many=True, allow_null=True)
    srvDescription = serializers.ListField(
        child=_MultiLangStringSerializer(many=True), allow_null=True
    )
    supervisoryAuthority = _SupervisoryAuthorityResponseSerializer(allow_null=True)
    supportURI = serializers.ListField(child=serializers.CharField())
    registryURI = serializers.URLField(allow_null=True)
    isIntermediary = serializers.BooleanField()
    usesIntermediary = serializers.ListField(
        child=serializers.DictField(), allow_null=True
    )
    isPSB = serializers.BooleanField()
    providesAttestations = _ProvidedAttestationResponseSerializer(
        many=True, allow_null=True
    )
    policy = _PolicyResponseSerializer(many=True, allow_null=True)
