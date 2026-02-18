"""
Credentials Models for EUDI Wallet Registration System

Contains:
- Credential: Attestation format definitions (SD-JWT, mDL, etc.)
- Claim: Claim paths within credentials
- IntendedUse: Data request use cases
- IntendedUsePurpose: Multilingual purposes
- IntendedUsePrivacyPolicy: Privacy policy links
- IntendedUseCredential: Requested credentials M2M
- EntityProvidesAttestation: Attestations provided by issuers
"""

from datetime import date

from core.models import BaseModel, CredentialFormat, Policy
from django.core.exceptions import ValidationError
from django.db import models
from registry.models import RegisteredEntity


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
        db_table = "credentials_credential"
        verbose_name = "Credential"
        verbose_name_plural = "Credentials"
        indexes = [
            models.Index(fields=["format"]),
        ]

    def __str__(self):
        type_info = self.attestation_type or self.catalogue_schema_uri or "Custom"
        return f"{self.get_format_display()} - {type_info}"


class Claim(BaseModel):
    """
    Claim class for specific attributes within credentials.
    SHALL NOT be present for providesAttestations credentials.
    """

    credential = models.ForeignKey(
        Credential, on_delete=models.CASCADE, related_name="claims"
    )
    path = models.JSONField(
        help_text=(
            "JSON path pointer to claim within credential per " "OpenID4VP Section 6.3"
        )
    )
    values = models.JSONField(
        blank=True, null=True, help_text="Optional expected values for matching"
    )

    class Meta:
        db_table = "credentials_claim"
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
        help_text=(
            "Registrar-provided unique identifier, may match "
            "Registration Certificate ID"
        ),
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
        db_table = "credentials_intended_use"
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
        today = date.today()
        if self.validity_end and self.validity_end <= today:
            return False
        return self.validity_start <= today


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
        db_table = "credentials_intended_use_purpose"
        verbose_name = "Intended Use Purpose"
        verbose_name_plural = "Intended Use Purposes"
        unique_together = ["intended_use", "lang"]
        indexes = [
            models.Index(fields=["intended_use"]),
        ]

    def __str__(self):
        return f"{self.lang}: {self.content[:50]}..."


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
        db_table = "credentials_intended_use_privacy_policy"
        verbose_name = "Intended Use Privacy Policy"
        verbose_name_plural = "Intended Use Privacy Policies"
        unique_together = ["intended_use", "policy"]
        indexes = [
            models.Index(fields=["intended_use"]),
        ]

    def __str__(self):
        return f"{self.intended_use} - {self.policy}"


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
        db_table = "credentials_intended_use_credential"
        verbose_name = "Intended Use Credential"
        verbose_name_plural = "Intended Use Credentials"
        unique_together = ["intended_use", "credential"]
        indexes = [
            models.Index(fields=["intended_use"]),
        ]

    def __str__(self):
        return f"{self.intended_use} - {self.credential}"


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
        db_table = "credentials_entity_provides_attestation"
        verbose_name = "Provided Attestation"
        verbose_name_plural = "Provided Attestations"
        unique_together = ["registered_entity", "credential"]
        indexes = [
            models.Index(fields=["registered_entity"]),
        ]

    def __str__(self):
        return f"{self.registered_entity} provides {self.credential}"
