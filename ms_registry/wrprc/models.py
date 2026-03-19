"""
WRPRC (Wallet Relying Party Registration Certificate) Models

Per ETSI TS 119 475:
- WRPRC is a signed JWT containing RP registration information
- Used by RPs to present their entitlements to Wallets
- Includes revocation via Status List mechanism
"""

from core.models import BaseModel
from django.db import models


class StatusList(BaseModel):
    """
    Manages revocation status lists for WRPRCs.

    Uses bitstring-based status list (like SD-JWT Status List).
    Each bit represents one WRPRC: 0 = valid, 1 = revoked.
    """

    class Purpose(models.TextChoices):
        REVOCATION = "revocation", "Revocation"
        SUSPENSION = "suspension", "Suspension"

    # Unique identifier for this status list
    list_id = models.CharField(max_length=100, unique=True)

    # Purpose of this status list
    purpose = models.CharField(
        max_length=20, choices=Purpose.choices, default=Purpose.REVOCATION
    )

    # Bitstring stored as bytes (compressed)
    bits = models.BinaryField(default=b"\x00" * 128)  # 1024 bits initial

    # Current allocation index
    current_index = models.PositiveIntegerField(default=0)

    # Maximum capacity (bits)
    capacity = models.PositiveIntegerField(default=1024)

    class Meta:
        db_table = "wrprc_status_list"
        verbose_name = "Status List"
        verbose_name_plural = "Status Lists"

    def __str__(self):
        return f"StatusList {self.list_id} ({self.purpose})"

    def allocate_index(self):
        """Allocate and return the next available index."""
        if self.current_index >= self.capacity:
            raise ValueError("Status list capacity exceeded")

        idx = self.current_index
        self.current_index += 1
        self.save(update_fields=["current_index", "updated_at"])
        return idx

    def set_status(self, index, revoked=True):
        """Set the status bit at the given index."""
        if index >= self.capacity:
            raise ValueError(f"Index {index} exceeds capacity {self.capacity}")

        bits = bytearray(self.bits)
        byte_index = index // 8
        bit_index = index % 8

        # Ensure we have enough bytes
        while len(bits) <= byte_index:
            bits.append(0)

        if revoked:
            bits[byte_index] |= 1 << bit_index  # Set bit to 1
        else:
            bits[byte_index] &= ~(1 << bit_index)  # Set bit to 0

        self.bits = bytes(bits)
        self.save(update_fields=["bits", "updated_at"])

    def get_status(self, index):
        """Get the status at the given index. Returns True if revoked."""
        if index >= self.capacity:
            raise ValueError(f"Index {index} exceeds capacity {self.capacity}")

        bits = bytearray(self.bits)
        byte_index = index // 8
        bit_index = index % 8

        if byte_index >= len(bits):
            return False  # Not yet allocated = valid

        return bool(bits[byte_index] & (1 << bit_index))

    def get_uri(self):
        """Get the public URI for this status list."""
        from django.conf import settings

        base_url = getattr(settings, "WRPRC_BASE_URL", "https://ms-registry.se")
        return f"{base_url}/api/wrprc/status/{self.list_id}"


class IssuedWRPRC(BaseModel):
    """
    Tracks issued WRPRCs for audit and revocation.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    # Link to registered entity
    registered_entity = models.ForeignKey(
        "registry.RegisteredEntity",
        on_delete=models.CASCADE,
        related_name="issued_wrprcs",
    )

    # Link to specific intended use (optional - WRPRC can cover all uses)
    intended_use = models.ForeignKey(
        "credentials.IntendedUse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wrprcs",
    )

    # Status list tracking
    status_list = models.ForeignKey(
        StatusList, on_delete=models.PROTECT, related_name="wrprcs"
    )
    status_list_index = models.PositiveIntegerField()

    # Current status
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    # Lifecycle timestamps
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    # Revocation details
    revocation_reason = models.CharField(max_length=255, blank=True)

    # Hash of the JWT for integrity/audit (SHA-256)
    jwt_hash = models.CharField(max_length=64)

    # JWT ID (jti claim) for tracking
    jti = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "wrprc_issued"
        verbose_name = "Issued WRPRC"
        verbose_name_plural = "Issued WRPRCs"
        indexes = [
            models.Index(fields=["jti"]),
            models.Index(fields=["registered_entity", "status"]),
            models.Index(fields=["status_list", "status_list_index"]),
        ]

    def __str__(self):
        return f"WRPRC {self.jti} for {self.registered_entity}"

    def revoke(self, reason=""):
        """Revoke this WRPRC."""
        from django.utils import timezone

        if self.status == self.Status.REVOKED:
            return  # Already revoked

        self.status = self.Status.REVOKED
        self.revoked_at = timezone.now()
        self.revocation_reason = reason
        self.save(
            update_fields=["status", "revoked_at", "revocation_reason", "updated_at"]
        )

        # Update status list
        self.status_list.set_status(self.status_list_index, revoked=True)

    def is_valid(self):
        """Check if this WRPRC is currently valid."""
        from django.utils import timezone

        if self.status == self.Status.REVOKED:
            return False

        if timezone.now() > self.expires_at:
            return False

        return True


class SigningKey(BaseModel):
    """
    Metadata about signing keys used for WRPRC issuance.

    Note: The actual private key should be stored in HSM/KMS,
    not in the database. This model tracks metadata only.
    """

    class KeyStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ROTATED = "rotated", "Rotated"
        REVOKED = "revoked", "Revoked"

    # Key identifier (matches kid in JWT header)
    kid = models.CharField(max_length=100, unique=True)

    # Key algorithm
    algorithm = models.CharField(max_length=20, default="ES256")

    # Status
    status = models.CharField(
        max_length=20, choices=KeyStatus.choices, default=KeyStatus.ACTIVE
    )

    # Public key in JWK format (for verification)
    public_key_jwk = models.JSONField()

    # X.509 certificate chain (base64-encoded DER)
    x5c = models.JSONField(default=list, help_text="Certificate chain for x5c header")

    # Reference to key in external system (HSM/KMS)
    external_key_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reference to key in HSM/KMS (e.g., AWS KMS key ARN)",
    )

    # Validity period
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()

    # Rotation tracking
    rotated_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaces",
    )

    class Meta:
        db_table = "wrprc_signing_key"
        verbose_name = "Signing Key"
        verbose_name_plural = "Signing Keys"

    def __str__(self):
        return f"SigningKey {self.kid} ({self.status})"

    @classmethod
    def get_active_key(cls):
        """Get the currently active signing key."""
        from django.utils import timezone

        now = timezone.now()

        return cls.objects.filter(
            status=cls.KeyStatus.ACTIVE, valid_from__lte=now, valid_until__gte=now
        ).first()
