"""
Core Domain Models for EUDI Wallet Registration System

Contains:
- Abstract base models (UUIDModel, TimestampedModel)
- Choice definitions (enumerations)
- Foundational domain models (Law, Identifier, Policy)
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

# ============================================================================
# SECTION 1: ABSTRACT BASE MODELS
# ============================================================================


class TimestampedModel(models.Model):
    """Abstract model with created/updated timestamps"""

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Abstract model with UUID primary key"""

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimestampedModel):
    """Abstract base model combining UUID and timestamps"""

    class Meta:
        abstract = True


# ============================================================================
# SECTION 2: CHOICE DEFINITIONS (Enumerations)
# ============================================================================


class EntitlementType(models.TextChoices):
    """Entitlement types as per TS5 / CIR for Relying Party Registration"""

    # Verifier role
    SERVICE_PROVIDER = "Service_Provider", "Service Provider"

    # Issuer roles
    PID_PROVIDER = "PID_Provider", "PID Provider"
    QEAA_PROVIDER = "QEAA_Provider", "Qualified EAA Provider"
    NON_Q_EAA_PROVIDER = "Non_Q_EAA_Provider", "Non-Qualified EAA Provider"
    PUB_EAA_PROVIDER = "PUB_EAA_Provider", "Public EAA Provider"

    # Qualified Trust Service Provider roles
    QCERT_ESIG_PROVIDER = (
        "QCert_for_ESig_Provider",
        "Qualified Certificate for E-Signature Provider",
    )
    QCERT_ESEAL_PROVIDER = (
        "QCert_for_ESeal_Provider",
        "Qualified Certificate for E-Seal Provider",
    )
    RQSIGCDS_PROVIDER = (
        "rQSigCDs_Provider",
        "Remote Qualified Signature Creation Device Provider",
    )
    RQSEALCDS_PROVIDER = (
        "rQSealCDs_Provider",
        "Remote Qualified Seal Creation Device Provider",
    )
    ESIG_ESEAL_CREATION_PROVIDER = (
        "ESig_ESeal_Creation_Provider",
        "E-Signature/E-Seal Creation Provider",
    )

    # Intermediary role
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
    """
    Policy type URI as defined in ETSI TS 119 475, B.2.8 Class Policy.
    The value is a URI per IETF RFC 8820 (URI Design and Ownership) —
    it is a stable machine-readable identifier, not a resolvable webpage.

    NOTE from spec: "In Context of WRP attributes only Privacy policy is present."
    Reference: ETSI TS 119 475 B.2.8, line:
      http://data.europa.eu/eudi/policy/privacy-policy - is a Privacy Policy.
    """

    PRIVACY_STATEMENT = (
        "http://data.europa.eu/eudi/policy/privacy-policy",
        "Privacy Policy",
    )


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
# SECTION 3: FOUNDATIONAL DOMAIN MODELS
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
        db_table = "core_law"
        verbose_name = "Law"
        verbose_name_plural = "Laws"

    def __str__(self):
        return f"{self.law_name} ({self.law_country_code or 'EU'})"


class Identifier(BaseModel):
    """
    Identifier (External class) - stores various identifier types per
    CIR Annex I (2)
    """

    identifier_type = models.CharField(
        max_length=50,
        choices=IdentifierType.choices,
        default=IdentifierType.EUID,
        help_text="Type of identifier",
    )
    identifier_value = models.CharField(
        max_length=500, help_text="The identifier value"
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
        db_table = "core_identifier"
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
        max_length=200, choices=PolicyType.choices, default=PolicyType.PRIVACY_STATEMENT
    )
    policy_uri = models.URLField(max_length=2048)
    locale = models.CharField(
        max_length=5, blank=True, null=True, help_text="Language/locale code"
    )
    version = models.CharField(max_length=50, blank=True, null=True)
    effective_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "core_policy"
        verbose_name = "Policy"
        verbose_name_plural = "Policies"
        indexes = [
            models.Index(fields=["policy_type"]),
            models.Index(fields=["policy_uri"]),
        ]

    def __str__(self):
        return f"{self.get_policy_type_display()} - {self.policy_uri[:50]}..."
