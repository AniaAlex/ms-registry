from core.models import EntitlementType, EntityRole, Identifier, IdentifierType, Policy
from credentials.serializers import IntendedUseInputSerializer, create_intended_use
from legal_entities.models import LegalEntity, LegalEntityIdentifier, LegalPerson
from rest_framework import serializers

from .models import (
    EntityEntitlement,
    EntityServiceDescription,
    EntitySupportURI,
    EntityUsesIntermediary,
    RegisteredEntity,
    RegisteredEntityPolicy,
    SupervisoryAuthority,
)


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

    # Accept entitlements as a list of entitlement type values [1..*]
    entitlements = serializers.ListField(
        child=serializers.ChoiceField(choices=EntitlementType.choices),
        write_only=True,
        required=True,
        min_length=1,
        help_text="List of entitlement types (e.g., Service_Provider, PID_Provider)",
    )
    # For reading, return the full entitlement objects
    entity_entitlements = EntityEntitlementSerializer(
        source="entitlements", many=True, read_only=True
    )

    # domain_uri is optional at the model level (blank/null) but obligatory at
    # registration time, since it is the SAN dNSName base for access certificates
    # and a registered entity must be representable as a valid TS5 WalletRelyingParty.
    domain_uri = serializers.URLField(
        max_length=2048,
        required=True,
        help_text="Domain/host of the entity's service (SAN dNSName for certificates)",
    )

    # instance_uri is optional at the model level (blank/null) but obligatory at
    # registration time: it is the full per-instance endpoint (incl. port) that
    # becomes the SAN uniformResourceIdentifier and uniquely locates this
    # instance among others sharing the same domain.
    instance_uri = serializers.URLField(
        max_length=2048,
        required=True,
        help_text=(
            "Full service endpoint of this instance, incl. port "
            "(SAN uniformResourceIdentifier for certificates)"
        ),
    )

    # Support URIs [1..*] — required by TS5 but not a field on RegisteredEntity;
    # accepted here as input and materialized into EntitySupportURI rows.
    support_uris = serializers.ListField(
        child=serializers.URLField(),
        write_only=True,
        required=True,
        min_length=1,
        help_text="Support URIs for the entity (at least one required)",
    )
    # For reading, return the stored support URIs
    entity_support_uris = serializers.SerializerMethodField()

    def get_entity_support_uris(self, obj):
        return [s.support_uri for s in obj.support_uris.all()]

    class Meta:
        model = RegisteredEntity
        fields = [
            "id",
            "legal_entity",
            "participant",
            "entity_role",
            "trade_name",
            "domain_uri",
            "instance_uri",
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
            "support_uris",  # write-only input
            "entity_support_uris",  # read-only output
        ]
        read_only_fields = [
            "id",
            "participant",
            "registration_status",
            "registered_at",
            "created_at",
            "updated_at",
        ]

    def validate_registry_uri(self, value):
        # Blank means not yet assigned; skip the uniqueness check.
        if not value:
            return value
        qs = RegisteredEntity.objects.filter(registry_uri=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A registered entity with this registry URI already exists."
            )
        return value

    def validate_entitlements(self, value):
        """Validate that at least one entitlement is provided"""
        if not value:
            raise serializers.ValidationError("At least one entitlement is required.")
        return value

    def validate(self, attrs):
        """Reject a domain_uri already registered to a *different* legal entity.

        Cheap guard against domain impersonation: a single legal entity may
        reuse its own service domain across several registrations (e.g. one
        per role), but two distinct legal entities must not both claim the
        same domain, since domain_uri is the SAN dNSName base for access
        certificates. This is an exact-match, first-come check and is NOT a
        substitute for proving domain control (DNS/HTTP challenge) — see the
        follow-up ticket for that.
        """
        domain_uri = attrs.get("domain_uri")
        legal_entity = attrs.get("legal_entity")
        # On partial update, fall back to the stored values.
        if self.instance is not None:
            if domain_uri is None:
                domain_uri = self.instance.domain_uri
            if legal_entity is None:
                legal_entity = self.instance.legal_entity

        if domain_uri and legal_entity is not None:
            clash = RegisteredEntity.objects.filter(domain_uri=domain_uri).exclude(
                legal_entity=legal_entity
            )
            if self.instance is not None:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {
                        "domain_uri": (
                            "This domain URI is already registered to a "
                            "different legal entity."
                        )
                    }
                )
        return attrs

    def create(self, validated_data):
        """Create RegisteredEntity and associated EntityEntitlements"""
        entitlement_types = validated_data.pop("entitlements", [])
        support_uri_list = validated_data.pop("support_uris", [])

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

        # Create support URIs [1..*]
        for idx, uri in enumerate(support_uri_list):
            EntitySupportURI.objects.create(
                registered_entity=registered_entity,
                support_uri=uri,
                is_primary=(idx == 0),
            )

        return registered_entity

    def update(self, instance, validated_data):
        """Update RegisteredEntity and associated EntityEntitlements"""
        entitlement_types = validated_data.pop("entitlements", None)
        support_uri_list = validated_data.pop("support_uris", None)

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

        # Replace support URIs if provided
        if support_uri_list is not None:
            instance.support_uris.all().delete()
            for idx, uri in enumerate(support_uri_list):
                EntitySupportURI.objects.create(
                    registered_entity=instance,
                    support_uri=uri,
                    is_primary=(idx == 0),
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

    # Domain URI (entity's own service domain)
    domain_uri = serializers.URLField(
        max_length=2048,
        required=True,
        help_text="URL of the entity's own domain/service (used for certificate SANs)",
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

    # Intended uses [0..*] — declared by the entity, verified by registrar
    intended_use = IntendedUseInputSerializer(
        many=True,
        required=False,
        help_text="Intended use declarations per Annex B WalletRelyingParty [0..*]",
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
        # Extract nested data
        entitlement_uris = validated_data.pop("entitlements", [])
        support_uri_list = validated_data.pop("support_uris", [])
        service_descriptions = validated_data.pop("service_descriptions", [])
        policy_uris = validated_data.pop("policies", [])
        intermediary_ids = validated_data.pop("uses_intermediaries", [])
        intended_uses_data = validated_data.pop("intended_use", [])

        # Get or create supervisory authority
        supervisory_authority, _ = SupervisoryAuthority.objects.get_or_create(
            authority_name=validated_data.pop("supervisory_authority_name"),
            country_code=validated_data.pop("supervisory_authority_country"),
            defaults={"info_uri": "https://example.com"},  # Placeholder
        )

        # Create or get legal person + legal entity
        legal_name = validated_data["legal_name"]
        identifier_value = validated_data["legal_entity_identifier"]
        identifier_type = validated_data.get(
            "legal_entity_identifier_type", IdentifierType.EUID
        )
        country_code = validated_data["country_code"]

        legal_entity = LegalEntity.objects.filter(
            primary_identifier__identifier_type=identifier_type,
            primary_identifier__identifier_value=identifier_value,
        ).first()

        if legal_entity is None:
            legal_person = LegalPerson.objects.create(legal_name=legal_name)
            legal_entity = LegalEntity.objects.create(
                legal_person=legal_person,
                entity_type="legal_person",
            )
            identifier, _ = Identifier.objects.get_or_create(
                identifier_type=identifier_type,
                identifier_value=identifier_value,
                defaults={"country_code": country_code, "is_primary": True},
            )
            LegalEntityIdentifier.objects.get_or_create(
                legal_entity=legal_entity,
                identifier=identifier,
                defaults={"is_primary": True},
            )
            legal_entity.primary_identifier = identifier
            legal_entity.save(update_fields=["primary_identifier"])

        # Create registered entity (WRP)
        registered_entity = RegisteredEntity.objects.create(
            legal_entity=legal_entity,
            participant=validated_data.get("participant"),
            entity_role=EntityRole.RELYING_PARTY,
            trade_name=validated_data.get("trade_name"),
            domain_uri=validated_data.get("domain_uri"),
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
        for uri in policy_uris:
            policy, _ = Policy.objects.get_or_create(policy_uri=uri)
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

        # Create intended uses [0..*]
        for iu_data in intended_uses_data:
            create_intended_use(registered_entity, iu_data)

        return registered_entity

    def update(self, instance, validated_data):
        """Update an existing WalletRelyingParty"""
        # Update basic fields
        if "trade_name" in validated_data:
            instance.trade_name = validated_data["trade_name"]
        if "is_psb" in validated_data:
            instance.is_psb = validated_data["is_psb"]
        if "is_intermediary" in validated_data:
            instance.is_intermediary = validated_data["is_intermediary"]
        if "domain_uri" in validated_data:
            instance.domain_uri = validated_data["domain_uri"]
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
            "domainURI": instance.domain_uri or None,
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
    domainURI = serializers.URLField(allow_null=True)
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
