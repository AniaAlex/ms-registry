"""
EUDI Wallet Registered Entity Registration - Django Models
Based on:
  - Trust Infrastructure Schema (WEBUILD WP4)
  - TS5 - Common Formats and API for RP Registration Information
  - TS6 - Common Set of Information to be Registered
  - ARF Topic 27 - Registration of PID Providers, Attestation Providers, and Relying Parties

Registered Entity Types (per Trust Infrastructure Schema Section 1.2):
  - PID Providers: Issue Person Identification Data
  - Attestation Providers: Issue attestations (QEAA, PuB-EAA, non-qualified EAA)
  - Relying Parties: Request attributes from Wallet Units

Version: 2.0 (refactored per Trust Infrastructure Schema)
Source: https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# ============================================================================
# SECTION 1: CHOICE DEFINITIONS (Enumerations)
# ============================================================================


class EntitlementType(models.TextChoices):
    """Entitlement types as per CIR for Relying Party Registration"""

    SERVICE_PROVIDER = "Service_Provider", "Service Provider"
    QEAA_PROVIDER = "QEAA_Provider", "Qualified EAA Provider"
    NON_Q_EAA_PROVIDER = "Non_Q_EAA_Provider", "Non-Qualified EAA Provider"
    PUB_EAA_PROVIDER = "PUB_EAA_Provider", "Public EAA Provider"
    PID_PROVIDER = "PID_Provider", "PID Provider"
    INTERMEDIARY = "Intermediary", "Intermediary"


class IdentifierType(models.TextChoices):
    """Identifier types as per CIR Annex I (2)"""

    EUID = "EUID", "European Unique Identifier"
    VAT_NUMBER = "VAT_NUMBER", "VAT Registration Number"
    LEI = "LEI", "Legal Entity Identifier"
    EORI = "EORI", "Economic Operators Registration and Identification"
    NATIONAL_BUSINESS_REG = "NATIONAL_BUSINESS_REG", "National Business Register Number"
    NATIONAL_TAX_REG = "NATIONAL_TAX_REG", "National Tax Registration Number"
    SERIAL_NUMBER = "SERIAL_NUMBER", "Serial Number (Natural Person)"
    OTHER = "OTHER", "Other National Identifier"


class CredentialFormat(models.TextChoices):
    """Credential format types as per OpenID4VP Appendix B"""

    SD_JWT_VC = "sd-jwt-vc", "SD-JWT Verifiable Credential"
    DC_SD_JWT = "dc+sd-jwt", "Digital Credential SD-JWT"
    MSO_MDOC = "mso_mdoc", "ISO mDL / mdoc Format"
    JWT_VC_JSON = "jwt_vc_json", "JWT VC JSON"
    LDP_VC = "ldp_vc", "JSON-LD VC with Data Integrity"


class PolicyType(models.TextChoices):
    """Policy types"""

    PRIVACY_STATEMENT = "Privacy_Statement", "Privacy Statement"
    TERMS_OF_SERVICE = "Terms_of_Service", "Terms of Service"
    DATA_PROCESSING_AGREEMENT = "Data_Processing_Agreement", "Data Processing Agreement"
    COOKIE_POLICY = "Cookie_Policy", "Cookie Policy"
    OTHER = "Other", "Other"


class RegistrationStatus(models.TextChoices):
    """Registration status"""

    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    REVOKED = "revoked", "Revoked"


class EntityType(models.TextChoices):
    """Legal entity type"""

    LEGAL_PERSON = "legal_person", "Legal Person"
    NATURAL_PERSON = "natural_person", "Natural Person"


class EntityRole(models.TextChoices):
    """
    Primary role in the EUDI Wallet ecosystem.
    Per Trust Infrastructure Schema Section 1.2 - Registered Entities:
    - PID Providers: Issue Person Identification Data
    - Attestation Providers: Issue attestations (QEAA, PuB-EAA, EAA)
    - Relying Parties: Request attributes from Wallet Units
    """

    RELYING_PARTY = "relying_party", "Relying Party (Verifier)"
    PID_PROVIDER = "pid_provider", "PID Provider (Issuer)"
    ATTESTATION_PROVIDER = "attestation_provider", "Attestation Provider (Issuer)"


# ============================================================================
# SECTION 2: ABSTRACT BASE MODEL
# ============================================================================


class BaseModel(models.Model):
    """Abstract base model with common fields"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ============================================================================
# SECTION 3: BASE TABLES (Provider Information Specification Dependencies)
# ============================================================================


class Law(BaseModel):
    """Law reference (External class from Provider Information Specification)"""

    law_uri = models.URLField(max_length=2048, help_text="URI reference to the law")
    law_name = models.CharField(max_length=500, help_text="Name of the law")
    law_country_code = models.CharField(
        max_length=2, blank=True, null=True, help_text="ISO 3166-1 alpha-2 country code"
    )
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "rp_law"
        verbose_name = "Law"
        verbose_name_plural = "Laws"

    def __str__(self):
        return f"{self.law_name} ({self.law_country_code or 'EU'})"


class Identifier(BaseModel):
    """Identifier (External class) - stores various identifier types per CIR Annex I (2)"""

    identifier_type = models.CharField(
        max_length=50,
        choices=IdentifierType.choices,
        default=IdentifierType.EUID,
        help_text="Type of identifier",
    )
    identifier_value = models.CharField(
        max_length=500, unique=True, help_text="The identifier value"
    )
    identifier_uri = models.URLField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="Full URI (e.g., http://data.europa.eu/eudi/id/EUID)",
    )
    issuing_authority = models.CharField(max_length=500, blank=True, null=True)
    country_code = models.CharField(
        max_length=2, blank=True, null=True, help_text="ISO 3166-1 alpha-2"
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "rp_identifier"
        verbose_name = "Identifier"
        verbose_name_plural = "Identifiers"
        unique_together = ["identifier_type", "identifier_value"]
        indexes = [
            models.Index(fields=["identifier_type"]),
            models.Index(fields=["identifier_value"]),
        ]

    def __str__(self):
        return f"{self.get_identifier_type_display()}: {self.identifier_value}"


class Policy(BaseModel):
    """Policy (External class)"""

    policy_type = models.CharField(
        max_length=50, choices=PolicyType.choices, default=PolicyType.PRIVACY_STATEMENT
    )
    policy_uri = models.URLField(max_length=2048)
    locale = models.CharField(
        max_length=5, blank=True, null=True, help_text="Language/locale code"
    )
    version = models.CharField(max_length=50, blank=True, null=True)
    effective_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "rp_policy"
        verbose_name = "Policy"
        verbose_name_plural = "Policies"
        indexes = [
            models.Index(fields=["policy_type"]),
            models.Index(fields=["policy_uri"]),
        ]

    def __str__(self):
        return f"{self.get_policy_type_display()} - {self.policy_uri[:50]}..."


# ============================================================================
# SECTION 4: LEGAL ENTITY HIERARCHY
# ============================================================================


class LegalPerson(BaseModel):
    """Legal Person (External class)"""

    legal_name = models.CharField(max_length=500, help_text="Official legal name")
    legal_form = models.CharField(
        max_length=200, blank=True, null=True, help_text="e.g., LLC, GmbH, AB, etc."
    )
    legal_form_uri = models.URLField(
        max_length=2048, blank=True, null=True, help_text="URI to legal form definition"
    )
    registration_date = models.DateField(blank=True, null=True)
    governing_law = models.ForeignKey(
        Law,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="legal_persons",
    )

    class Meta:
        db_table = "rp_legal_person"
        verbose_name = "Legal Person"
        verbose_name_plural = "Legal Persons"
        indexes = [
            models.Index(fields=["legal_name"]),
        ]

    def __str__(self):
        return self.legal_name


class NaturalPerson(BaseModel):
    """Natural Person (External class - for RP that is a natural person)"""

    given_name = models.CharField(max_length=200)
    family_name = models.CharField(max_length=200)
    date_of_birth = models.DateField(blank=True, null=True)
    nationality = models.CharField(
        max_length=2, blank=True, null=True, help_text="ISO 3166-1 alpha-2"
    )

    class Meta:
        db_table = "rp_natural_person"
        verbose_name = "Natural Person"
        verbose_name_plural = "Natural Persons"

    def __str__(self):
        return f"{self.given_name} {self.family_name}"


class PhysicalAddress(BaseModel):
    """Physical Address"""

    street_address = models.CharField(max_length=500, blank=True, null=True)
    locality = models.CharField(
        max_length=200, blank=True, null=True, help_text="City/Town"
    )
    region = models.CharField(
        max_length=200, blank=True, null=True, help_text="State/Province"
    )
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country_code = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    address_type = models.CharField(
        max_length=50, default="registered", help_text="registered, operational, etc."
    )

    class Meta:
        db_table = "rp_physical_address"
        verbose_name = "Physical Address"
        verbose_name_plural = "Physical Addresses"

    def __str__(self):
        parts = [self.street_address, self.locality, self.country_code]
        return ", ".join(filter(None, parts))


class LegalEntity(BaseModel):
    """Legal Entity (Superclass)"""

    entity_type = models.CharField(
        max_length=20, choices=EntityType.choices, help_text="Type of legal entity"
    )
    legal_person = models.OneToOneField(
        LegalPerson,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="legal_entity",
    )
    natural_person = models.OneToOneField(
        NaturalPerson,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="legal_entity",
    )
    primary_identifier = models.ForeignKey(
        Identifier,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="primary_for_entities",
    )
    identifiers = models.ManyToManyField(
        Identifier, through="LegalEntityIdentifier", related_name="legal_entities"
    )
    physical_address = models.ForeignKey(
        PhysicalAddress,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="legal_entities",
    )
    email = models.EmailField(max_length=320, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    info_uri = models.URLField(max_length=2048, blank=True, null=True)

    class Meta:
        db_table = "rp_legal_entity"
        verbose_name = "Legal Entity"
        verbose_name_plural = "Legal Entities"
        indexes = [
            models.Index(fields=["entity_type"]),
        ]

    def clean(self):
        """Validate entity type matches the related object"""
        if self.entity_type == EntityType.LEGAL_PERSON:
            if not self.legal_person or self.natural_person:
                raise ValidationError(
                    "Legal person entity type requires legal_person and no natural_person"
                )
        elif self.entity_type == EntityType.NATURAL_PERSON:
            if not self.natural_person or self.legal_person:
                raise ValidationError(
                    "Natural person entity type requires natural_person and no legal_person"
                )

    def __str__(self):
        if self.legal_person:
            return self.legal_person.legal_name
        elif self.natural_person:
            return str(self.natural_person)
        return f"Legal Entity {self.id}"

    @property
    def display_name(self):
        """Return the display name based on entity type"""
        if self.legal_person:
            return self.legal_person.legal_name
        elif self.natural_person:
            return f"{self.natural_person.given_name} {self.natural_person.family_name}"
        return str(self.id)


class LegalEntityIdentifier(BaseModel):
    """Link table for Legal Entity to multiple Identifiers"""

    legal_entity = models.ForeignKey(
        LegalEntity, on_delete=models.CASCADE, related_name="entity_identifiers"
    )
    identifier = models.ForeignKey(
        Identifier, on_delete=models.CASCADE, related_name="entity_links"
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "rp_legal_entity_identifier"
        verbose_name = "Legal Entity Identifier"
        verbose_name_plural = "Legal Entity Identifiers"
        unique_together = ["legal_entity", "identifier"]


# ============================================================================
# SECTION 5: SUPERVISORY AUTHORITY (DPA)
# ============================================================================


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
        db_table = "rp_supervisory_authority"
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


# ============================================================================
# SECTION 6: MAIN REGISTERED ENTITY MODEL
# ============================================================================


class RegisteredEntity(BaseModel):
    """
    Main table for EUDI Wallet Registered Entity data.
    Per Trust Infrastructure Schema Section 1.2, registered entities include:
    - PID Providers (issue Person Identification Data)
    - Attestation Providers (issue QEAA, PuB-EAA, non-qualified EAA)
    - Relying Parties (request/verify attributes from Wallet Units)

    All entity types share the same registration process with Member State Registrars
    but have different roles in the ecosystem.

    Since eIDAS 2.0 (Regulation 2024/1183), wallet entities are integrated into
    Trusted Lists as Trust Service Providers with wallet-specific service types:
    - EudiWallet/PIDProvider
    - EudiWallet/QEAAProvider, EAAProvider, PuB-EAAProvider
    - EudiWallet/RelyingParty
    - EudiWallet/WalletProvider
    """

    legal_entity = models.OneToOneField(
        LegalEntity, on_delete=models.CASCADE, related_name="registered_entity"
    )

    # Note: TrustServiceProvider(s) link to LegalEntity directly.
    # Access TSPs via: self.legal_entity.trust_service_providers.all()

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
        help_text="Indicates whether the entity is a public sector body (relevant for PuB-EAA Providers)",
    )

    # isIntermediary: indicates if entity acts on behalf of other entities (RPs only)
    is_intermediary = models.BooleanField(
        default=False,
        help_text="Indicates whether the entity acts as an intermediary. Only applicable to Relying Parties.",
    )

    # registryURI: URI for national registry API (provided by Registrar)
    registry_uri = models.URLField(
        max_length=2048,
        help_text="National registry API URI, provided by Registrar (per Reg_03, Reg_04)",
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
        db_table = "rp_registered_entity"
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


# ============================================================================
# SECTION 7: SUPPORT URIs (1..* required)
# ============================================================================


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
        db_table = "rp_entity_support_uri"
        verbose_name = "Support URI"
        verbose_name_plural = "Support URIs"
        indexes = [
            models.Index(fields=["registered_entity"]),
        ]

    def __str__(self):
        return f"{self.support_type or 'Support'}: {self.support_uri[:50]}..."


# ============================================================================
# SECTION 8: ENTITLEMENTS (1..* required)
# ============================================================================


class EntityEntitlement(BaseModel):
    """
    Entitlement for Registered Entity [1..*]
    Specifies what the entity is authorized to do:
    - For Relying Parties: Service_Provider, Intermediary
    - For PID Providers: PID_Provider
    - For Attestation Providers: QEAA_Provider, PUB_EAA_Provider, Non_Q_EAA_Provider
    """

    registered_entity = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="entitlements"
    )
    entitlement_uri = models.URLField(
        max_length=2048,
        help_text="e.g., https://uri.etsi.org/19475/Entitlement/Service_Provider",
    )
    entitlement_type = models.CharField(max_length=50, choices=EntitlementType.choices)
    granted_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "rp_entity_entitlement"
        verbose_name = "Entitlement"
        verbose_name_plural = "Entitlements"
        unique_together = ["registered_entity", "entitlement_uri"]
        indexes = [
            models.Index(fields=["registered_entity"]),
            models.Index(fields=["entitlement_type"]),
        ]

    def __str__(self):
        return f"{self.get_entitlement_type_display()} - {self.registered_entity}"


# ============================================================================
# SECTION 9: SERVICE DESCRIPTIONS (1..* MultiLangString)
# ============================================================================


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
        db_table = "rp_entity_service_description"
        verbose_name = "Service Description"
        verbose_name_plural = "Service Descriptions"
        unique_together = ["registered_entity", "lang"]
        indexes = [
            models.Index(fields=["registered_entity"]),
        ]

    def __str__(self):
        return f"{self.lang}: {self.content[:50]}..."


# ============================================================================
# SECTION 10: CREDENTIAL TABLE (Section 2.4.4)
# ============================================================================


class Credential(BaseModel):
    """
    Credential class for attestation types per OpenID4VP.
    Used for both requested credentials (IntendedUse) and provided credentials.
    """

    format = models.CharField(
        max_length=50, choices=CredentialFormat.choices, help_text="Attestation format"
    )
    meta = models.JSONField(
        help_text="Format-specific metadata per OpenID4VP Section 6.1"
    )
    catalogue_schema_uri = models.URLField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="Reference to attestation catalogue",
    )
    attestation_rulebook_uri = models.URLField(
        max_length=2048, blank=True, null=True, help_text="URI to Attestation Rulebook"
    )
    attestation_type = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Self-declared attestation type (if not in catalogue)",
    )

    class Meta:
        db_table = "rp_credential"
        verbose_name = "Credential"
        verbose_name_plural = "Credentials"
        indexes = [
            models.Index(fields=["format"]),
        ]

    def __str__(self):
        type_info = self.attestation_type or self.catalogue_schema_uri or "Custom"
        return f"{self.get_format_display()} - {type_info}"


# ============================================================================
# SECTION 11: CLAIM TABLE (Section 2.4.1)
# ============================================================================


class Claim(BaseModel):
    """
    Claim class for specific attributes within credentials.
    SHALL NOT be present for providesAttestations credentials.
    """

    credential = models.ForeignKey(
        Credential, on_delete=models.CASCADE, related_name="claims"
    )
    path = models.JSONField(
        help_text="JSON path pointer to claim within credential per OpenID4VP Section 6.3"
    )
    values = models.JSONField(
        blank=True, null=True, help_text="Optional expected values for matching"
    )

    class Meta:
        db_table = "rp_claim"
        verbose_name = "Claim"
        verbose_name_plural = "Claims"
        indexes = [
            models.Index(fields=["credential"]),
        ]

    def clean(self):
        """Validate path is non-empty array"""
        if not self.path or not isinstance(self.path, list) or len(self.path) == 0:
            raise ValidationError("Path must be a non-empty array")

    def __str__(self):
        path_str = (
            ".".join(str(p) for p in self.path)
            if isinstance(self.path, list)
            else str(self.path)
        )
        return f"{path_str}"


# ============================================================================
# SECTION 12: INTENDED USE TABLE (Section 2.4.3)
# ============================================================================


class IntendedUse(BaseModel):
    """
    Intended Use class for data request use cases.
    Per CIR Annex I paragraphs (8), (9) and (10).
    Applicable primarily to Relying Parties (verifiers) who request attributes.
    """

    registered_entity = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="intended_uses"
    )

    # intendedUseIdentifier: [1..1] Registrar-provided unique ID
    intended_use_identifier = models.CharField(
        max_length=500,
        unique=True,
        help_text="Registrar-provided unique identifier, may match Registration Certificate ID",
    )

    # createdAt: [1..1] Validity start date
    validity_start = models.DateField(help_text="Validity start date")

    # revokedAt: [0..1] End date for validity
    validity_end = models.DateField(
        blank=True, null=True, help_text="End date for validity (revoked or expired)"
    )

    # Credentials requested
    credentials = models.ManyToManyField(
        Credential, through="IntendedUseCredential", related_name="intended_uses"
    )

    class Meta:
        db_table = "rp_intended_use"
        verbose_name = "Intended Use"
        verbose_name_plural = "Intended Uses"
        indexes = [
            models.Index(fields=["registered_entity"]),
            models.Index(fields=["intended_use_identifier"]),
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.intended_use_identifier} ({status})"

    @property
    def is_active(self):
        """Computed property for active status"""
        from datetime import date

        today = date.today()
        if self.validity_end and self.validity_end <= today:
            return False
        return self.validity_start <= today


# ============================================================================
# SECTION 13: INTENDED USE - PURPOSE (1..* MultiLangString)
# ============================================================================


class IntendedUsePurpose(BaseModel):
    """Multilingual purpose descriptions [1..*]"""

    intended_use = models.ForeignKey(
        IntendedUse, on_delete=models.CASCADE, related_name="purposes"
    )
    lang = models.CharField(
        max_length=5, help_text="Language code per ETSI TS 119 612 Annex E"
    )
    content = models.TextField(help_text="Localized purpose description")

    class Meta:
        db_table = "rp_intended_use_purpose"
        verbose_name = "Intended Use Purpose"
        verbose_name_plural = "Intended Use Purposes"
        unique_together = ["intended_use", "lang"]
        indexes = [
            models.Index(fields=["intended_use"]),
        ]

    def __str__(self):
        return f"{self.lang}: {self.content[:50]}..."


# ============================================================================
# SECTION 14: INTENDED USE - PRIVACY POLICY (1..* Policy)
# ============================================================================


class IntendedUsePrivacyPolicy(BaseModel):
    """Privacy policy for intended use [1..*]"""

    intended_use = models.ForeignKey(
        IntendedUse, on_delete=models.CASCADE, related_name="privacy_policies"
    )
    policy = models.ForeignKey(
        Policy, on_delete=models.CASCADE, related_name="intended_use_links"
    )
    locale = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        help_text="Language/locale for this policy version",
    )
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "rp_intended_use_privacy_policy"
        verbose_name = "Intended Use Privacy Policy"
        verbose_name_plural = "Intended Use Privacy Policies"
        unique_together = ["intended_use", "policy"]
        indexes = [
            models.Index(fields=["intended_use"]),
        ]

    def __str__(self):
        return f"{self.intended_use} - {self.policy}"


# ============================================================================
# SECTION 15: INTENDED USE - CREDENTIALS (1..* Credential)
# ============================================================================


class IntendedUseCredential(BaseModel):
    """Junction table for Intended Use to Credentials [1..*]"""

    intended_use = models.ForeignKey(
        IntendedUse, on_delete=models.CASCADE, related_name="credential_links"
    )
    credential = models.ForeignKey(
        Credential, on_delete=models.CASCADE, related_name="intended_use_links"
    )
    is_mandatory = models.BooleanField(
        default=False, help_text="Whether this credential is required"
    )
    request_order = models.PositiveIntegerField(
        blank=True, null=True, help_text="Order in presentation request"
    )

    class Meta:
        db_table = "rp_intended_use_credential"
        verbose_name = "Intended Use Credential"
        verbose_name_plural = "Intended Use Credentials"
        unique_together = ["intended_use", "credential"]
        indexes = [
            models.Index(fields=["intended_use"]),
        ]

    def __str__(self):
        return f"{self.intended_use} - {self.credential}"


# ============================================================================
# SECTION 16: PROVIDES ATTESTATIONS (For PID/Attestation Providers - Issuers)
# ============================================================================


class EntityProvidesAttestation(BaseModel):
    """
    Attestations provided by PID Providers and Attestation Providers (issuers).
    Per Trust Infrastructure Schema Section 2.1:
    - PID Providers: Attestation type(s) they intend to issue (e.g., national PID)
    - QEAA Providers: Attestation type(s) (e.g., diplomas, professional qualifications)
    - PuB-EAA Providers: Attestation type(s) (e.g., mDLs, vehicle registration cards)
    - Non-qualified EAA Providers: Attestation type(s)

    Note: Claims SHALL NOT be present for these credentials.
    """

    registered_entity = models.ForeignKey(
        RegisteredEntity,
        on_delete=models.CASCADE,
        related_name="provided_attestations",
    )
    credential = models.ForeignKey(
        Credential, on_delete=models.CASCADE, related_name="provided_by"
    )

    class Meta:
        db_table = "rp_entity_provides_attestation"
        verbose_name = "Provided Attestation"
        verbose_name_plural = "Provided Attestations"
        unique_together = ["registered_entity", "credential"]
        indexes = [
            models.Index(fields=["registered_entity"]),
        ]

    def __str__(self):
        return f"{self.registered_entity} provides {self.credential}"


# ============================================================================
# SECTION 17: USES INTERMEDIARY (Self-referencing relationship for RPs)
# ============================================================================


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
        db_table = "rp_entity_uses_intermediary"
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


# ============================================================================
# SECTION 18: ACCESS CERTIFICATE HISTORY (Certificate Transparency)
# ============================================================================


class EntityAccessCertificate(BaseModel):
    """
    Access Certificate history with CT log info per RFC 9162.
    Per Trust Infrastructure Schema Section 2.2:
    Access CA issues certificates to all registered entities
    (PID Providers, Attestation Providers, Relying Parties).
    """

    registered_entity = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="access_certificates"
    )

    # Certificate details
    certificate_serial = models.CharField(max_length=100)
    certificate_fingerprint_sha256 = models.CharField(
        max_length=64, blank=True, null=True
    )
    issuer_dn = models.CharField(max_length=500, blank=True, null=True)
    subject_dn = models.CharField(max_length=500, blank=True, null=True)
    not_before = models.DateTimeField()
    not_after = models.DateTimeField()

    # Certificate Transparency Log info (RFC 9162)
    ct_log_id = models.CharField(max_length=200, blank=True, null=True)
    ct_log_timestamp = models.DateTimeField(blank=True, null=True)
    ct_sct = models.BinaryField(
        blank=True, null=True, help_text="Signed Certificate Timestamp"
    )

    # Certificate status
    is_current = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    revocation_reason = models.CharField(max_length=100, blank=True, null=True)

    # Full certificate (PEM encoded)
    certificate_pem = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "rp_entity_access_certificate"
        verbose_name = "Access Certificate"
        verbose_name_plural = "Access Certificates"
        indexes = [
            models.Index(fields=["registered_entity"]),
            models.Index(fields=["is_current"]),
            models.Index(fields=["not_before", "not_after"]),
        ]

    def __str__(self):
        status = "Current" if self.is_current else "Historical"
        return f"{self.certificate_serial} ({status})"


# ============================================================================
# SECTION 19: REGISTRATION CERTIFICATE (Optional per Member State)
# ============================================================================


class EntityRegistrationCertificate(BaseModel):
    """
    Registration Certificate (optional per Member State).
    Per Trust Infrastructure Schema Section 2.3:
    - RPRC_09: Registrar MAY decide to issue registration certificates to Relying Parties
    - RPRC_13: Registrar MAY decide to issue registration certificates to Providers

    Contains (a subset of) the data registered for that entity.
    """

    intended_use = models.OneToOneField(
        IntendedUse, on_delete=models.CASCADE, related_name="registration_certificate"
    )

    # Certificate identifier (same as intendedUseIdentifier if provided)
    certificate_identifier = models.CharField(max_length=500)

    # Certificate details
    certificate_serial = models.CharField(max_length=100, blank=True, null=True)
    issuer_dn = models.CharField(max_length=500, blank=True, null=True)
    subject_dn = models.CharField(max_length=500, blank=True, null=True)
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField(blank=True, null=True)

    # Certificate status
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    revocation_reason = models.CharField(max_length=100, blank=True, null=True)

    # Full certificate
    certificate_pem = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "rp_wrp_registration_certificate"
        verbose_name = "Registration Certificate"
        verbose_name_plural = "Registration Certificates"
        indexes = [
            models.Index(fields=["intended_use"]),
            models.Index(fields=["certificate_identifier"]),
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Revoked"
        return f"{self.certificate_identifier} ({status})"


# ============================================================================
# SECTION 20: REGISTERED ENTITY POLICIES LINK TABLE
# ============================================================================


class RegisteredEntityPolicy(BaseModel):
    """Junction table for Registered Entity to Policies"""

    registered_entity = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="policy_links"
    )
    policy = models.ForeignKey(
        Policy, on_delete=models.CASCADE, related_name="entity_links"
    )

    class Meta:
        db_table = "rp_entity_policy"
        verbose_name = "Entity Policy"
        verbose_name_plural = "Entity Policies"
        unique_together = ["registered_entity", "policy"]

    def __str__(self):
        return f"{self.registered_entity} - {self.policy}"


# ============================================================================
# SECTION 21: AUDIT LOG TABLE
# ============================================================================


class AuditLog(models.Model):
    """Audit log for tracking changes"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table_name = models.CharField(max_length=100)
    record_id = models.UUIDField()
    action = models.CharField(
        max_length=20,
        choices=[
            ("INSERT", "Insert"),
            ("UPDATE", "Update"),
            ("DELETE", "Delete"),
        ],
    )
    old_values = models.JSONField(blank=True, null=True)
    new_values = models.JSONField(blank=True, null=True)
    changed_by = models.CharField(max_length=200, blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "rp_audit_log"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["table_name"]),
            models.Index(fields=["record_id"]),
            models.Index(fields=["changed_at"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.table_name} at {self.changed_at}"
