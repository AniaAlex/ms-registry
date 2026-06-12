"""
Access certificate serializers.

Contains:
- CSRSubmissionSerializer: Validates CSRs for certificate issuance
- SigningCertificateUploadSerializer: Validates self-signed credential-signing certs

Validates against registered entity data per ETSI TS 119 411-8.
"""

from cryptography import x509
from django.utils import timezone
from rest_framework import serializers

# ──────────────────────────────────────────────────────────────────────────────
# CSR Submission Serializer (for certificate issuance)
# ──────────────────────────────────────────────────────────────────────────────


class CSRSubmissionSerializer(serializers.Serializer):
    """
    Validates a CSR submitted for access certificate issuance.

    The CSR subject DN is used as-is in the issued certificate and must
    therefore match the entity's registry data. Validation checks:
    1. Valid PEM-encoded CSR
    2. CSR signature is valid (proves possession of private key)
    3. Entity is eligible for certificate issuance (entitlements present)

    Subject DN matching against registry data is performed later in
    ca_integration.validate_csr_subject(). The CA adds authoritative
    extensions (SAN, policy OIDs, key usage) derived from registry data,
    but does not override the Subject DN supplied in the CSR.

    Required context:
        entity (RegisteredEntity): The registered entity requesting a certificate.

    After successful validation, ``validated_data["csr"]`` contains
    the parsed ``cryptography.x509.CertificateSigningRequest`` object.
    """

    csr_pem = serializers.CharField(
        help_text="PEM-encoded Certificate Signing Request (CSR).",
    )

    def validate_csr_pem(self, value: str) -> x509.CertificateSigningRequest:
        """Parse and validate CSR."""
        # Parse CSR
        try:
            csr = x509.load_pem_x509_csr(value.encode())
        except Exception as exc:
            raise serializers.ValidationError(f"Invalid PEM CSR: {exc}")

        # Verify CSR signature (proves private key possession)
        if not csr.is_signature_valid:
            raise serializers.ValidationError(
                "CSR signature is invalid. The CSR must be signed with the "
                "private key corresponding to the public key in the request."
            )

        return csr

    def validate(self, data: dict) -> dict:
        """
        Check entity eligibility. Subject DN matching against registry data
        is handled in ca_integration.validate_csr_subject() during issuance.
        """
        entity = self.context.get("entity")
        if not entity:
            raise serializers.ValidationError(
                "Internal error: entity context required."
            )

        # Entity must have at least one entitlement
        if not entity.entitlements.exists():
            raise serializers.ValidationError(
                "Entity has no entitlements registered. "
                "At least one entitlement is required for certificate issuance."
            )

        # Store parsed CSR
        data["csr"] = data["csr_pem"]

        return data


# ── Signing Certificate ───────────────────────────────────────────────────────

_ISSUER_ENTITLEMENT_TYPES = [
    "PID_Provider",
    "QEAA_Provider",
    "Non_Q_EAA_Provider",
    "PUB_EAA_Provider",
]


class SigningCertificateUploadSerializer(serializers.Serializer):
    """
    Validates a self-signed X.509 credential-signing certificate.

    After validation, certificate_pem holds the parsed cert object.
    """

    certificate_pem = serializers.CharField(
        help_text="PEM-encoded self-signed X.509 certificate"
    )
    entitlement_type = serializers.ChoiceField(
        choices=[(t, t) for t in _ISSUER_ENTITLEMENT_TYPES]
    )

    def validate_certificate_pem(self, value):
        try:
            cert = x509.load_pem_x509_certificate(value.encode())
        except Exception:
            raise serializers.ValidationError("Invalid PEM-encoded X.509 certificate.")

        if cert.issuer != cert.subject:
            raise serializers.ValidationError(
                "Signing certificate must be self-signed "
                "(issuer Distinguished Name must equal subject)."
            )

        now = timezone.now()
        if cert.not_valid_after_utc < now:
            raise serializers.ValidationError("Certificate has expired.")
        if cert.not_valid_before_utc > now:
            raise serializers.ValidationError("Certificate is not yet valid.")

        return cert

    def validate_entitlement_type(self, value):
        entity = self.context.get("entity")
        if (
            entity
            and not entity.entitlements.filter(
                entitlement_type=value, is_active=True
            ).exists()
        ):
            raise serializers.ValidationError(
                f"Entity does not hold an active {value} entitlement."
            )
        return value
