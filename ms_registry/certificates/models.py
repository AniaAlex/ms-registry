"""
Certificates Models for EUDI Wallet Registration System

Contains:
- EntityAccessCertificate: Access certificate history with CT logs
- EntityRegistrationCertificate: Optional registration certificates
- AuditLog: Change tracking
"""

import uuid

from core.models import BaseModel
from credentials.models import IntendedUse
from django.db import models
from registry.models import RegisteredEntity


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
