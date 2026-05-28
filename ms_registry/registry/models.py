"""
Registry Models for EUDI Wallet Registration System (TS5 Implementation)

Contains:
- SupervisoryAuthority: DPA records
- RegisteredEntity: WalletRelyingParty per TS5 (covers all entity types)
- EntitySupportURI: Support URIs [1..*]
- EntityEntitlement: Authorization entitlements [1..*]
- EntityServiceDescription: Multilingual descriptions
- RegisteredEntityPolicy: Policy links
- EntityUsesIntermediary: RP → Intermediary relationships

Note: IntendedUse, Credential, and Claim models are in the credentials app.
"""

from core.models import (
    BaseModel,
    EntitlementType,
    EntityRole,
    Policy,
    RegistrationStatus,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from legal_entities.models import LegalEntity


class SupervisoryAuthority(BaseModel):
    """Data Protection Authority / Supervisory Authority"""

    legal_entity = models.ForeignKey(
        LegalEntity,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="supervised_authorities",
    )
    authority_name = models.CharField(max_length=500)
    country_code = models.CharField(max_length=2, help_text="Member State")
    email = models.EmailField(max_length=320, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    info_uri = models.URLField(max_length=2048, blank=True, null=True)

    class Meta:
        db_table = "registry_supervisory_authority"
        verbose_name = "Supervisory Authority (DPA)"
        verbose_name_plural = "Supervisory Authorities (DPAs)"
        indexes = [
            models.Index(fields=["country_code"]),
        ]

    def clean(self):
        """At least one contact method required"""
        if not any([self.email, self.phone, self.info_uri]):
            raise ValidationError(
                "At least one of email, phone, or info_uri must be provided"
            )

    def __str__(self):
        return f"{self.authority_name} ({self.country_code})"


class RegisteredEntity(BaseModel):
    """
    WalletRelyingParty per TS5 specification.

    NOTE: This model is equivalent to the WalletRelyingParty class defined in TS5
    (Common Formats and API for Relying Party Registration Information).
    The name "WalletRelyingParty" in TS5 is misleading - it covers ALL entities
    that interact with EUDI Wallets, not just verifiers:

    - Service Providers (verifiers) - entitlement: Service_Provider
    - PID Providers - entitlement: PID_Provider
    - Attestation Providers - entitlements: QEAA_Provider,
      Non_Q_EAA_Provider, PUB_EAA_Provider
    - QTSPs - entitlements: QCert_for_ESig_Provider,
      QCert_for_ESeal_Provider, etc.

    The entity's capabilities are defined by their entitlements, not by a role field.
    The entity_role field is kept for internal classification convenience.

    A LegalEntity can have multiple RegisteredEntity instances (e.g., dev, staging,
    production environments). Each instance has its own registry_uri and receives
    its own access certificate per Reg_10a.

    TS5 Reference:
    https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/blob/main/docs/technical-specifications/ts5-common-formats-and-api-for-rp-registration-information.md
    """

    legal_entity = models.ForeignKey(
        LegalEntity, on_delete=models.CASCADE, related_name="registered_entities"
    )

    # Entity role in the ecosystem (ARF Topic 27)
    entity_role = models.CharField(
        max_length=30,
        choices=EntityRole.choices,
        help_text="Primary role: RP (verifier), PID Provider, or Attestation Provider",
    )

    # RegisteredEntity specific attributes (Section 2.1)
    trade_name = models.CharField(
        max_length=500, blank=True, null=True, help_text="Common/service name [0..1]"
    )

    # isPSB: indicates if entity is public sector body
    is_psb = models.BooleanField(
        default=False,
        verbose_name="Is Public Sector Body",
        help_text=(
            "Indicates whether the entity is a public sector body "
            "(relevant for PuB-EAA Providers)"
        ),
    )

    # isIntermediary: indicates if entity acts on behalf of other entities (RPs only)
    is_intermediary = models.BooleanField(
        default=False,
        help_text=(
            "Indicates whether the entity acts as an intermediary. "
            "Only applicable to Relying Parties."
        ),
    )

    # registryURI: URI for national registry API (provided by Registrar).
    # Auto-generated on creation as <host>/registry/wrp/<uuid>/
    # (per Reg_03, Reg_04). Alternatively, can be set manually in a second
    # step by the Registrar if a different URI is required.
    registry_uri = models.URLField(
        max_length=2048,
        blank=True,
        help_text=(
            "National registry API URI, auto-generated on creation "
            "(per Reg_03, Reg_04)"
        ),
    )

    # supervisoryAuthority: DPA in charge
    supervisory_authority = models.ForeignKey(
        SupervisoryAuthority,
        on_delete=models.PROTECT,
        related_name="registered_entities",
    )

    # Status tracking
    registration_status = models.CharField(
        max_length=50,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.PENDING,
    )
    registered_at = models.DateTimeField(blank=True, null=True)

    # Audit fields
    created_by = models.CharField(max_length=200, blank=True, null=True)
    updated_by = models.CharField(max_length=200, blank=True, null=True)

    # Many-to-many relationships
    policies = models.ManyToManyField(
        Policy, through="RegisteredEntityPolicy", related_name="registered_entities"
    )

    class Meta:
        db_table = "registry_registered_entity"
        verbose_name = "Registered Entity"
        verbose_name_plural = "Registered Entities"
        indexes = [
            models.Index(fields=["entity_role"]),
            models.Index(fields=["trade_name"]),
            models.Index(fields=["registry_uri"]),
            models.Index(fields=["is_psb"]),
            models.Index(fields=["is_intermediary"]),
            models.Index(fields=["registration_status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["registry_uri"],
                condition=~Q(registry_uri=""),
                name="unique_registered_entity_registry_uri",
            ),
        ]

    def clean(self):
        """Business rules validation"""
        # isIntermediary only applies to Relying Parties
        if self.is_intermediary and self.entity_role != EntityRole.RELYING_PARTY:
            raise ValidationError("Only Relying Parties can act as intermediaries")
        # Intermediary cannot use other intermediaries
        if self.is_intermediary and hasattr(self, "id") and self.id:
            if self.used_intermediaries.exists():
                raise ValidationError("An intermediary cannot use other intermediaries")

    def __str__(self):
        name = self.trade_name or self.legal_entity.display_name
        role = self.get_entity_role_display() if self.entity_role else "Unknown Role"
        return f"{name} ({role} - {self.get_registration_status_display()})"

    @property
    def display_name(self):
        return self.trade_name or self.legal_entity.display_name

    @property
    def primary_identifier(self):
        return self.legal_entity.primary_identifier

    @property
    def is_issuer(self):
        """Returns True if entity is a PID or Attestation Provider (issuer role)"""
        return self.entity_role in [
            EntityRole.PID_PROVIDER,
            EntityRole.ATTESTATION_PROVIDER,
        ]

    @property
    def is_verifier(self):
        """Returns True if entity is a Relying Party (verifier role)"""
        return self.entity_role == EntityRole.RELYING_PARTY


class EntitySupportURI(BaseModel):
    """Support URI for Registered Entity [1..*]"""

    registered_entity = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="support_uris"
    )
    support_uri = models.URLField(max_length=2048)
    support_type = models.CharField(
        max_length=100, blank=True, null=True, help_text="website, email, phone"
    )
    description = models.TextField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "registry_entity_support_uri"
        verbose_name = "Support URI"
        verbose_name_plural = "Support URIs"
        indexes = [
            models.Index(fields=["registered_entity"]),
        ]

    def __str__(self):
        return f"{self.support_type or 'Support'}: {self.support_uri[:50]}..."


class EntityEntitlement(BaseModel):
    """
    Entitlement for Registered Entity [1..*]
    Specifies what the entity is authorized to do per TS5.

    An entity can have multiple entitlements. For example, an attestation
    provider that needs to verify identity before issuance registers with
    both Service_Provider and their provider entitlement.
    """

    registered_entity = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="entitlements"
    )
    entitlement_uri = models.URLField(
        max_length=2048,
        help_text=(
            "ETSI Entitlement URIs per TS5: "
            "https://uri.etsi.org/19475/Entitlement/Service_Provider, "
            "https://uri.etsi.org/19475/Entitlement/PID_Provider, "
            "https://uri.etsi.org/19475/Entitlement/QEAA_Provider, "
            "https://uri.etsi.org/19475/Entitlement/PUB_EAA_Provider, "
            "https://uri.etsi.org/19475/Entitlement/Non_Q_EAA_Provider, "
            "https://uri.etsi.org/19475/Entitlement/QCert_for_ESig_Provider, "
            "https://uri.etsi.org/19475/Entitlement/QCert_for_ESeal_Provider, "
            "https://uri.etsi.org/19475/Entitlement/rQSigCDs_Provider, "
            "https://uri.etsi.org/19475/Entitlement/rQSealCDs_Provider, "
            "https://uri.etsi.org/19475/Entitlement/ESig_ESeal_Creation_Provider"
        ),
    )
    entitlement_type = models.CharField(max_length=50, choices=EntitlementType.choices)
    granted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "registry_entity_entitlement"
        verbose_name = "Entitlement"
        verbose_name_plural = "Entitlements"
        unique_together = ["registered_entity", "entitlement_uri"]
        indexes = [
            models.Index(fields=["registered_entity"]),
            models.Index(fields=["entitlement_type"]),
        ]

    def __str__(self):
        return f"{self.get_entitlement_type_display()} - {self.registered_entity}"


class EntityServiceDescription(BaseModel):
    """Multilingual service description [1..*]"""

    registered_entity = models.ForeignKey(
        RegisteredEntity,
        on_delete=models.CASCADE,
        related_name="service_descriptions",
    )
    lang = models.CharField(
        max_length=5, help_text="Language code per ETSI TS 119 612 Annex E"
    )
    content = models.TextField(help_text="Localized description")

    class Meta:
        db_table = "registry_entity_service_description"
        verbose_name = "Service Description"
        verbose_name_plural = "Service Descriptions"
        unique_together = ["registered_entity", "lang"]
        indexes = [
            models.Index(fields=["registered_entity"]),
        ]

    def __str__(self):
        return f"{self.lang}: {self.content[:50]}..."


class RegisteredEntityPolicy(BaseModel):
    """Junction table for Registered Entity to Policies"""

    registered_entity = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="policy_links"
    )
    policy = models.ForeignKey(
        Policy, on_delete=models.CASCADE, related_name="entity_links"
    )

    class Meta:
        db_table = "registry_entity_policy"
        verbose_name = "Entity Policy"
        verbose_name_plural = "Entity Policies"
        unique_together = ["registered_entity", "policy"]

    def __str__(self):
        return f"{self.registered_entity} - {self.policy}"


class EntityUsesIntermediary(BaseModel):
    """
    Self-referencing relationship for Relying Parties using intermediaries.
    Per Trust Infrastructure Schema, only Relying Parties can use intermediaries.
    """

    registered_entity = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="used_intermediaries"
    )
    intermediary = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="clients_using"
    )
    # Cached for quick access
    intermediary_identifier = models.CharField(max_length=500)
    intermediary_trade_name = models.CharField(max_length=500, blank=True, null=True)
    intermediary_registry_uri = models.URLField(max_length=2048)
    relationship_start_date = models.DateField(default=timezone.now)
    relationship_end_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "registry_entity_uses_intermediary"
        verbose_name = "Uses Intermediary"
        verbose_name_plural = "Uses Intermediaries"
        unique_together = ["registered_entity", "intermediary"]
        indexes = [
            models.Index(fields=["registered_entity"]),
            models.Index(fields=["intermediary"]),
        ]

    def clean(self):
        """Validate intermediary relationship"""
        if self.registered_entity_id == self.intermediary_id:
            raise ValidationError("An entity cannot be its own intermediary")
        if self.registered_entity.entity_role != EntityRole.RELYING_PARTY:
            raise ValidationError("Only Relying Parties can use intermediaries")
        if self.registered_entity.is_intermediary:
            raise ValidationError(
                "An entity that is an intermediary cannot use other intermediaries"
            )

    def __str__(self):
        return f"{self.registered_entity} uses {self.intermediary}"
