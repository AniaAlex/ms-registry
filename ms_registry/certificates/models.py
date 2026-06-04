"""
Certificates Models for EUDI Wallet Registration System

Contains:
- EntityAccessCertificate: Access certificate history with CT logs
- EntityRegistrationCertificate: Optional registration certificates
- EntitySigningCertificate: Self-signed credential-signing certs for issuers
- AuditLog: Change tracking
"""

import uuid

from core.models import BaseModel, EntitlementType
from credentials.models import IntendedUse
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from registry.models import RegisteredEntity

ISSUER_ENTITLEMENT_CHOICES = [
    (EntitlementType.PID_PROVIDER, "PID Provider"),
    (EntitlementType.QEAA_PROVIDER, "Qualified EAA Provider"),
    (EntitlementType.PUB_EAA_PROVIDER, "Public EAA Provider"),
    (EntitlementType.NON_Q_EAA_PROVIDER, "Non-Qualified EAA Provider"),
]


class EntityAccessCertificate(BaseModel):
    """
    Access Certificate history per Trust Infrastructure Schema Section 2.2.
    Access CA issues certificates to all registered entities
    (PID Providers, Attestation Providers, Relying Parties).

    Links to django-ca's Certificate model for lifecycle management (OCSP, CRL).
    Duplicate certificate data stored locally for future-proofing if django-ca
    becomes a separate service.
    """

    registered_entity = models.ForeignKey(
        RegisteredEntity, on_delete=models.CASCADE, related_name="access_certificates"
    )

    # Link to django-ca Certificate (for OCSP/CRL integration)
    # SET_NULL allows local record to survive if django-ca cert is removed
    django_ca_certificate = models.OneToOneField(
        "django_ca.Certificate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registry_access_certificate",
        help_text="Link to django-ca Certificate for lifecycle management",
    )

    # Certificate details (duplicate storage for future-proofing)
    certificate_serial = models.CharField(max_length=100)
    certificate_fingerprint_sha256 = models.CharField(
        max_length=64, blank=True, null=True
    )
    issuer_dn = models.CharField(max_length=500, blank=True, null=True)
    subject_dn = models.CharField(max_length=500, blank=True, null=True)
    not_before = models.DateTimeField()
    not_after = models.DateTimeField()

    # TODO: Add a proper CT log implementation, e.g. using the python-ct library
    # ct_log_id = models.CharField(max_length=200, blank=True, null=True)
    # ct_log_timestamp = models.DateTimeField(blank=True, null=True)
    # ct_sct = models.BinaryField(
    #     blank=True, null=True, help_text="Signed Certificate Timestamp"
    # )

    # Certificate status
    is_current = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    revocation_reason = models.CharField(max_length=100, blank=True, null=True)

    # Full certificate (PEM encoded)
    certificate_pem = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "certificates_entity_access_certificate"
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


class EntityRegistrationCertificate(BaseModel):
    """
    Registration Certificate (optional per Member State).
    Per Trust Infrastructure Schema Section 2.3:
    - RPRC_09: Registrar MAY decide to issue registration certificates to
      Relying Parties
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
        db_table = "certificates_entity_registration_certificate"
        verbose_name = "Registration Certificate"
        verbose_name_plural = "Registration Certificates"
        indexes = [
            models.Index(fields=["intended_use"]),
            models.Index(fields=["certificate_identifier"]),
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Revoked"
        return f"{self.certificate_identifier} ({status})"


class EntitySigningCertificate(BaseModel):
    """
    Self-signed credential-signing certificate for issuer entities.

    Issuers (PID Providers, EAA Providers) generate their own key pair and
    upload a self-signed X.509 certificate. They use the corresponding private
    key to sign credentials issued to citizens.

    This cert is published in the national TSL as a ServiceCertificate so
    Relying Parties can verify credential signatures against it.

    Distinct from EntityAccessCertificate (WRPAC), which is CA-issued and
    authenticates the entity when connecting to Wallet Units.

    One record per (registered_entity, entitlement_type) because different
    entitlement types require different cert profiles (id-etsi-qct-pid for
    PID_Provider, qualified seal for QEAA_Provider, etc.).
    """

    registered_entity = models.ForeignKey(
        RegisteredEntity,
        on_delete=models.CASCADE,
        related_name="signing_certificates",
    )
    entitlement_type = models.CharField(
        max_length=50,
        choices=ISSUER_ENTITLEMENT_CHOICES,
        help_text="Issuer entitlement this signing cert covers",
    )

    # The entity's own self-signed certificate — no CA involvement
    certificate_pem = models.TextField(
        help_text="PEM-encoded self-signed X.509 certificate provided by the entity",
    )
    certificate_serial = models.CharField(max_length=100, blank=True, null=True)
    certificate_fingerprint_sha256 = models.CharField(
        max_length=64, blank=True, null=True
    )
    subject_dn = models.CharField(max_length=500, blank=True, null=True)
    not_before = models.DateTimeField(blank=True, null=True)
    not_after = models.DateTimeField(blank=True, null=True)

    is_current = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    revocation_reason = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "certificates_entity_signing_certificate"
        verbose_name = "Signing Certificate"
        verbose_name_plural = "Signing Certificates"
        indexes = [
            models.Index(fields=["registered_entity", "entitlement_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["registered_entity", "entitlement_type"],
                condition=Q(is_current=True),
                name="unique_current_signing_cert_per_entitlement",
            )
        ]

    def clean(self):
        if not self.registered_entity_id:
            return
        has_entitlement = self.registered_entity.entitlements.filter(
            entitlement_type=self.entitlement_type, is_active=True
        ).exists()
        if not has_entitlement:
            raise ValidationError(
                f"Entity does not hold an active {self.entitlement_type} entitlement."
            )

    def __str__(self):
        status = "current" if self.is_current else "historical"
        return (
            f"{self.registered_entity.display_name} – "
            f"{self.entitlement_type} signing cert ({status})"
        )


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
        db_table = "certificates_audit_log"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["table_name"]),
            models.Index(fields=["record_id"]),
            models.Index(fields=["changed_at"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.table_name} at {self.changed_at}"
