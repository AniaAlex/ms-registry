"""
Django Models for ETSI TS 119612 Trust Status Lists (TSL)

This module provides Django models that mirror the go-trust example-tsl structure.
Use Django Admin to manage TSL data and generate ETSI-compliant XML output.

Directory structure reference:
    example-tsl/
    ├── scheme.yaml           -> TSLScheme model
    └── providers/
        └── provider1/
            ├── provider.yaml -> TrustServiceProvider model
            ├── cert1.pem     -> ServiceCertificate model
            └── cert1.yaml    -> TrustService model

Usage:
    1. Add 'tsl_generator' to INSTALLED_APPS
    2. Run migrations: python manage.py makemigrations && python manage.py migrate
    3. Use TSLScheme.to_xml() to generate ETSI TS 119612 compliant XML
"""

from django.db import models
from django.utils import timezone

# =============================================================================
# Language Choices - ISO 639-1 codes commonly used in ETSI TSLs
# =============================================================================
LANGUAGE_CHOICES = [
    ("en", "English"),
    ("sv", "Swedish"),
    ("de", "German"),
    ("fr", "French"),
    ("es", "Spanish"),
    ("it", "Italian"),
    ("nl", "Dutch"),
    ("da", "Danish"),
    ("fi", "Finnish"),
    ("no", "Norwegian"),
    ("pl", "Polish"),
    ("pt", "Portuguese"),
    ("cs", "Czech"),
    ("el", "Greek"),
    ("hu", "Hungarian"),
    ("ro", "Romanian"),
    ("sk", "Slovak"),
    ("sl", "Slovenian"),
    ("bg", "Bulgarian"),
    ("et", "Estonian"),
    ("lv", "Latvian"),
    ("lt", "Lithuanian"),
    ("mt", "Maltese"),
    ("hr", "Croatian"),
]

# =============================================================================
# TSL Type URIs - Common ETSI TSL types
# =============================================================================
TSL_TYPE_CHOICES = [
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUlistofthelists",
        "EU List of Trusted Lists (LOTL)",
    ),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric",
        "EU Generic Trusted List",
    ),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/CClist",
        "Country Code Trusted List",
    ),
]

# =============================================================================
# Service Type URIs - ETSI Trust Service types
# =============================================================================
SERVICE_TYPE_CHOICES = [
    # Traditional eIDAS Trust Services
    ("http://uri.etsi.org/TrstSvc/Svctype/CA/QC", "Qualified Certificate Authority"),
    ("http://uri.etsi.org/TrstSvc/Svctype/CA/PKC", "Public Key Certificate Authority"),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/TSA/QTST",
        "Qualified Time Stamping Authority",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/TSA/TSS-QC",
        "Time Stamping Service - Qualified",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/Certstatus/OCSP/QC",
        "Qualified OCSP Service",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/Certstatus/CRL",
        "CRL Service",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/EDS/Q",
        "Qualified Electronic Delivery Service",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/EDS/REM/Q",
        "Qualified Registered Electronic Mail",
    ),
    ("http://uri.etsi.org/TrstSvc/Svctype/PSES/Q", "Qualified Preservation Service"),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/QESValidation/Q",
        "Qualified Validation Service",
    ),
    ("http://uri.etsi.org/TrstSvc/Svctype/IdV", "Identity Verification Service"),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/IdV/nothavingPKIid",
        "Identity Verification (non-PKI)",
    ),
    # EUDI Wallet Services (eIDAS 2.0 / Regulation 2024/1183)
    (
        "http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/PIDProvider",
        "PID Provider - Person Identification Data Issuer",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/QEAAProvider",
        "QEAA Provider - Qualified Electronic Attestation of Attributes Issuer",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/EAAProvider",
        "EAA Provider - Electronic Attestation of Attributes Issuer",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/WalletProvider",
        "EUDI Wallet Provider",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/RelyingParty",
        "EUDI Wallet Relying Party",
    ),
    (
        "http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/PuB-EAAProvider",
        "PuB-EAA Provider - Public Body Attestation Issuer",
    ),
]

# =============================================================================
# Service Status URIs - ETSI Trust Service statuses
# =============================================================================
SERVICE_STATUS_CHOICES = [
    ("http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted", "Granted"),
    ("http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/withdrawn", "Withdrawn"),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/recognisedatnationallevel",
        "Recognised at National Level",
    ),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/deprecatedatnationallevel",
        "Deprecated at National Level",
    ),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/undersupervision",
        "Under Supervision",
    ),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/supervisionincessation",
        "Supervision in Cessation",
    ),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/supervisionceased",
        "Supervision Ceased",
    ),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/supervisionrevoked",
        "Supervision Revoked",
    ),
    ("http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/accredited", "Accredited"),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/accreditationceased",
        "Accreditation Ceased",
    ),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/accreditationrevoked",
        "Accreditation Revoked",
    ),
]


# =============================================================================
# Abstract Base Models for Multi-Language Support
# =============================================================================
class MultiLangName(models.Model):
    """Abstract base model for multi-language name fields."""

    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")
    value = models.CharField(max_length=500)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.value} ({self.language})"


class MultiLangURI(models.Model):
    """Abstract base model for multi-language URI fields."""

    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")
    uri = models.URLField(max_length=500)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.uri} ({self.language})"


# =============================================================================
# TSL Scheme Model (scheme.yaml equivalent)
# =============================================================================
class TSLScheme(models.Model):
    """
    TSL Scheme Information - equivalent to scheme.yaml

    This is the root of a Trust Status List containing scheme-level metadata.
    """

    # Basic identification
    name = models.CharField(max_length=200, help_text="Internal name for this scheme")
    tsl_type = models.CharField(
        max_length=200,
        choices=TSL_TYPE_CHOICES,
        default="http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric",
        help_text="TSL Type URI",
    )
    sequence_number = models.PositiveIntegerField(
        default=1, help_text="TSL sequence number (increments with each update)"
    )

    # Scheme territory (ISO 3166-1 alpha-2)
    territory = models.CharField(
        max_length=2,
        default="SE",
        help_text="Two-letter country code (ISO 3166-1 alpha-2)",
    )

    # Timestamps
    issue_date = models.DateTimeField(
        default=timezone.now, help_text="TSL issue date/time"
    )
    next_update = models.DateTimeField(
        null=True, blank=True, help_text="Expected next update date/time"
    )

    # Distribution points
    distribution_points = models.TextField(
        blank=True, help_text="Distribution point URIs (one per line)"
    )

    # Historical information period (in days)
    historical_information_period = models.PositiveIntegerField(
        default=65535, help_text="Historical information period in days"
    )

    # Status determination approach
    status_determination_approach = models.URLField(
        max_length=500,
        default="http://uri.etsi.org/TrstSvc/TrustedList/TSLType/StatusDetn/EUappropriate",
        help_text="Status determination approach URI",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "TSL Scheme"
        verbose_name_plural = "TSL Schemes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.territory}) - Seq #{self.sequence_number}"

    def get_distribution_points_list(self):
        """Return distribution points as a list."""
        if not self.distribution_points:
            return []
        return [dp.strip() for dp in self.distribution_points.split("\n") if dp.strip()]

    def to_xml(self):
        """Generate ETSI TS 119612 compliant XML."""
        from .xml_generator import generate_tsl_xml

        return generate_tsl_xml(self)

    def to_xml_gotrust(self):
        """Generate XML in go-trust compatible format (tsl: prefix)."""
        from .xml_generator import generate_tsl_xml_gotrust_format

        return generate_tsl_xml_gotrust_format(self)

    def to_xml_etsi(self):
        """Generate XML in full ETSI TS 119612 format with all namespaces."""
        from .xml_generator import generate_tsl_xml_etsi_format

        return generate_tsl_xml_etsi_format(self)

    def export_to_file(self, filepath: str, use_gotrust_format: bool = True):
        """Export this TSL to a file."""
        from .xml_generator import export_tsl_to_file

        return export_tsl_to_file(self, filepath, use_gotrust_format)


class TSLSchemeOperatorName(MultiLangName):
    """Multi-language operator names for TSL Scheme."""

    scheme = models.ForeignKey(
        TSLScheme, on_delete=models.CASCADE, related_name="operator_names"
    )

    class Meta:
        verbose_name = "Operator Name"
        verbose_name_plural = "Operator Names"


class TSLSchemeName(MultiLangName):
    """Multi-language scheme names for TSL Scheme."""

    scheme = models.ForeignKey(
        TSLScheme, on_delete=models.CASCADE, related_name="scheme_names"
    )

    class Meta:
        verbose_name = "Scheme Name"
        verbose_name_plural = "Scheme Names"


class TSLSchemeInformationURI(MultiLangURI):
    """Multi-language scheme information URIs."""

    scheme = models.ForeignKey(
        TSLScheme, on_delete=models.CASCADE, related_name="information_uris"
    )

    class Meta:
        verbose_name = "Scheme Information URI"
        verbose_name_plural = "Scheme Information URIs"


class TSLSchemeCommunityRule(MultiLangURI):
    """Multi-language scheme type/community rules URIs."""

    scheme = models.ForeignKey(
        TSLScheme, on_delete=models.CASCADE, related_name="community_rules"
    )

    class Meta:
        verbose_name = "Community Rule"
        verbose_name_plural = "Community Rules"


class TSLPolicyOrLegalNotice(models.Model):
    """Multi-language policy or legal notice for TSL Scheme."""

    scheme = models.ForeignKey(
        TSLScheme, on_delete=models.CASCADE, related_name="legal_notices"
    )
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")
    notice = models.TextField(help_text="Legal notice or policy text")

    class Meta:
        verbose_name = "Legal Notice"
        verbose_name_plural = "Legal Notices"

    def __str__(self):
        return f"Notice ({self.language})"


# =============================================================================
# Pointer to Other TSL (for LOTL)
# =============================================================================
class TSLPointer(models.Model):
    """
    Pointer to another TSL - used in List of Trusted Lists (LOTL).

    This represents OtherTSLPointer elements in ETSI TS 119612.
    """

    scheme = models.ForeignKey(
        TSLScheme, on_delete=models.CASCADE, related_name="pointers"
    )
    tsl_location = models.URLField(
        max_length=500, help_text="URL of the referenced TSL"
    )
    tsl_type = models.CharField(
        max_length=200,
        choices=TSL_TYPE_CHOICES,
        default="http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric",
        help_text="Type of the referenced TSL",
    )
    scheme_territory = models.CharField(
        max_length=2, help_text="Territory of the referenced TSL"
    )
    mime_type = models.CharField(
        max_length=100,
        default="application/vnd.etsi.tsl+xml",
        help_text="MIME type of the TSL",
    )

    class Meta:
        verbose_name = "TSL Pointer"
        verbose_name_plural = "TSL Pointers"
        ordering = ["scheme_territory"]

    def __str__(self):
        return f"Pointer to {self.scheme_territory} TSL"


class TSLPointerOperatorName(MultiLangName):
    """Multi-language operator names for TSL Pointer."""

    pointer = models.ForeignKey(
        TSLPointer, on_delete=models.CASCADE, related_name="operator_names"
    )

    class Meta:
        verbose_name = "Pointer Operator Name"
        verbose_name_plural = "Pointer Operator Names"


class TSLPointerCertificate(models.Model):
    """Digital identity certificate for TSL Pointer (signature verification)."""

    pointer = models.ForeignKey(
        TSLPointer, on_delete=models.CASCADE, related_name="certificates"
    )
    certificate_data = models.TextField(
        help_text="Base64-encoded X.509 certificate (PEM content without headers)"
    )

    class Meta:
        verbose_name = "Pointer Certificate"
        verbose_name_plural = "Pointer Certificates"

    def __str__(self):
        return f"Certificate for {self.pointer}"


# =============================================================================
# Trust Service Provider Model (provider.yaml equivalent)
# =============================================================================
class TrustServiceProvider(models.Model):
    """
    Trust Service Provider (TSP) - equivalent to provider.yaml

    Represents an organization that provides trust services.
    
    Under eIDAS 2.0, wallet entities (PID Providers, Attestation Providers,
    Relying Parties, Wallet Providers) are TSPs with wallet-specific service types.
    
    Organization data (name, address, contact) is stored in LegalEntity to avoid
    duplication. One LegalEntity can have multiple TSP entries (in different TSL schemes).
    """

    scheme = models.ForeignKey(
        TSLScheme, on_delete=models.CASCADE, related_name="providers"
    )

    # Link to LegalEntity for organization data (name, address, contact)
    # ForeignKey allows one organization to be in multiple TSL schemes
    legal_entity = models.ForeignKey(
        "rp_registration.LegalEntity",
        on_delete=models.CASCADE,
        related_name="trust_service_providers",
        help_text="Organization providing the trust services",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Trust Service Provider"
        verbose_name_plural = "Trust Service Providers"
        ordering = ["pk"]
        # One organization can only appear once per scheme
        unique_together = ["scheme", "legal_entity"]

    def __str__(self):
        primary_name = self.names.first()
        if primary_name:
            return primary_name.value
        # Fallback to LegalEntity name
        return self.legal_entity.display_name if self.legal_entity else f"TSP #{self.pk}"

    @property
    def street_address(self):
        """Get street address from LegalEntity's PhysicalAddress."""
        if self.legal_entity and self.legal_entity.physical_address:
            return self.legal_entity.physical_address.street_address or ""
        return ""

    @property
    def locality(self):
        """Get locality from LegalEntity's PhysicalAddress."""
        if self.legal_entity and self.legal_entity.physical_address:
            return self.legal_entity.physical_address.locality or ""
        return ""

    @property
    def state_or_province(self):
        """Get region from LegalEntity's PhysicalAddress."""
        if self.legal_entity and self.legal_entity.physical_address:
            return self.legal_entity.physical_address.region or ""
        return ""

    @property
    def postal_code(self):
        """Get postal code from LegalEntity's PhysicalAddress."""
        if self.legal_entity and self.legal_entity.physical_address:
            return self.legal_entity.physical_address.postal_code or ""
        return ""

    @property
    def country_name(self):
        """Get country code from LegalEntity's PhysicalAddress."""
        if self.legal_entity and self.legal_entity.physical_address:
            return self.legal_entity.physical_address.country_code or "SE"
        return "SE"


class TSPName(MultiLangName):
    """Multi-language names for Trust Service Provider."""

    provider = models.ForeignKey(
        TrustServiceProvider, on_delete=models.CASCADE, related_name="names"
    )

    class Meta:
        verbose_name = "TSP Name"
        verbose_name_plural = "TSP Names"


class TSPTradeName(MultiLangName):
    """Multi-language trade names for Trust Service Provider."""

    provider = models.ForeignKey(
        TrustServiceProvider, on_delete=models.CASCADE, related_name="trade_names"
    )

    class Meta:
        verbose_name = "TSP Trade Name"
        verbose_name_plural = "TSP Trade Names"


class TSPElectronicAddress(models.Model):
    """Electronic address (URI) for Trust Service Provider."""

    provider = models.ForeignKey(
        TrustServiceProvider,
        on_delete=models.CASCADE,
        related_name="electronic_addresses",
    )
    uri = models.CharField(
        max_length=500, help_text="Electronic address URI (https://, mailto:, tel:)"
    )
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")

    class Meta:
        verbose_name = "Electronic Address"
        verbose_name_plural = "Electronic Addresses"

    def __str__(self):
        return self.uri


class TSPInformationURI(MultiLangURI):
    """Multi-language information URIs for Trust Service Provider."""

    provider = models.ForeignKey(
        TrustServiceProvider, on_delete=models.CASCADE, related_name="information_uris"
    )

    class Meta:
        verbose_name = "TSP Information URI"
        verbose_name_plural = "TSP Information URIs"


class TSPCertificate(models.Model):
    """
    X.509 Certificate for Trust Service Provider.

    Stores certificates that identify the TSP organization itself
    (e.g., signing certificates, identity certificates).
    """

    provider = models.ForeignKey(
        TrustServiceProvider, on_delete=models.CASCADE, related_name="certificates"
    )

    # Certificate data - store as PEM content
    certificate_pem = models.TextField(
        help_text="PEM-encoded X.509 certificate (including BEGIN/END markers)"
    )

    # Certificate type
    CERTIFICATE_TYPE_CHOICES = [
        ("signing", "Signing Certificate"),
        ("identity", "Identity Certificate"),
        ("tls", "TLS Certificate"),
        ("other", "Other"),
    ]
    certificate_type = models.CharField(
        max_length=50,
        choices=CERTIFICATE_TYPE_CHOICES,
        default="identity",
        help_text="Type/purpose of this certificate",
    )

    # Metadata extracted from certificate
    subject_dn = models.CharField(
        max_length=1000, blank=True, help_text="Subject Distinguished Name"
    )
    subject_cn = models.CharField(
        max_length=500, blank=True, help_text="Subject Common Name"
    )
    issuer_dn = models.CharField(
        max_length=1000, blank=True, help_text="Issuer Distinguished Name"
    )
    issuer_cn = models.CharField(
        max_length=500, blank=True, help_text="Issuer Common Name"
    )
    serial_number = models.CharField(
        max_length=100, blank=True, help_text="Certificate serial number (hex)"
    )
    fingerprint_sha256 = models.CharField(
        max_length=64, blank=True, help_text="SHA-256 fingerprint (hex, no colons)"
    )
    not_before = models.DateTimeField(
        null=True, blank=True, help_text="Certificate validity start"
    )
    not_after = models.DateTimeField(
        null=True, blank=True, help_text="Certificate validity end"
    )

    # Key usage info
    key_usage = models.CharField(
        max_length=500, blank=True, help_text="Key usage extensions (comma-separated)"
    )
    extended_key_usage = models.CharField(
        max_length=500,
        blank=True,
        help_text="Extended key usage OIDs (comma-separated)",
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TSP Certificate"
        verbose_name_plural = "TSP Certificates"
        ordering = ["-created_at"]

    def __str__(self):
        if self.subject_cn:
            return f"{self.subject_cn} ({self.get_certificate_type_display()})"
        return f"Certificate #{self.pk} ({self.get_certificate_type_display()})"

    def get_base64_der(self):
        """Extract base64-encoded DER from PEM content."""
        pem = self.certificate_pem.strip()
        # Remove PEM headers/footers
        lines = pem.split("\n")
        der_lines = [line for line in lines if not line.startswith("-----")]
        return "".join(der_lines)

    def extract_metadata_from_pem(self):
        """
        Extract certificate metadata from PEM content.
        Requires the cryptography library.
        """
        try:
            import hashlib

            from cryptography import x509
            from cryptography.hazmat.backends import default_backend

            cert = x509.load_pem_x509_certificate(
                self.certificate_pem.encode(), default_backend()
            )

            # Subject info
            self.subject_dn = cert.subject.rfc4514_string()
            try:
                self.subject_cn = cert.subject.get_attributes_for_oid(
                    x509.oid.NameOID.COMMON_NAME
                )[0].value
            except (IndexError, KeyError):
                pass

            # Issuer info
            self.issuer_dn = cert.issuer.rfc4514_string()
            try:
                self.issuer_cn = cert.issuer.get_attributes_for_oid(
                    x509.oid.NameOID.COMMON_NAME
                )[0].value
            except (IndexError, KeyError):
                pass

            # Serial and validity
            self.serial_number = format(cert.serial_number, "x").upper()
            self.not_before = cert.not_valid_before_utc
            self.not_after = cert.not_valid_after_utc

            # Fingerprint
            self.fingerprint_sha256 = (
                hashlib.sha256(cert.public_bytes(x509.encoding.Encoding.DER))
                .hexdigest()
                .upper()
            )

            # Key usage
            try:
                ku = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.KEY_USAGE
                )
                usages = []
                if ku.value.digital_signature:
                    usages.append("digitalSignature")
                if ku.value.key_encipherment:
                    usages.append("keyEncipherment")
                if ku.value.content_commitment:
                    usages.append("nonRepudiation")
                if ku.value.data_encipherment:
                    usages.append("dataEncipherment")
                if ku.value.key_agreement:
                    usages.append("keyAgreement")
                if ku.value.key_cert_sign:
                    usages.append("keyCertSign")
                if ku.value.crl_sign:
                    usages.append("cRLSign")
                self.key_usage = ", ".join(usages)
            except x509.ExtensionNotFound:
                pass

            # Extended key usage
            try:
                eku = cert.extensions.get_extension_for_oid(
                    x509.oid.ExtensionOID.EXTENDED_KEY_USAGE
                )
                self.extended_key_usage = ", ".join(
                    str(usage.dotted_string) for usage in eku.value
                )
            except x509.ExtensionNotFound:
                pass

            return True
        except ImportError:
            return False
        except Exception:
            return False

    def save(self, *args, **kwargs):
        """Auto-extract metadata when saving if PEM is provided."""
        if self.certificate_pem and not self.subject_dn:
            self.extract_metadata_from_pem()
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """Check if certificate is currently valid based on dates."""
        from django.utils import timezone

        now = timezone.now()
        if self.not_before and self.not_after:
            return self.not_before <= now <= self.not_after
        return None

    @property
    def days_until_expiry(self):
        """Return days until certificate expires."""
        from django.utils import timezone

        if self.not_after:
            delta = self.not_after - timezone.now()
            return delta.days
        return None


# =============================================================================
# Trust Service Model (service.yaml + certificate.pem equivalent)
# =============================================================================
class TrustService(models.Model):
    """
    Trust Service - equivalent to service.yaml files

    Represents a specific trust service offered by a TSP.
    """

    provider = models.ForeignKey(
        TrustServiceProvider, on_delete=models.CASCADE, related_name="services"
    )

    service_type = models.CharField(
        max_length=200,
        choices=SERVICE_TYPE_CHOICES,
        default="http://uri.etsi.org/TrstSvc/Svctype/CA/QC",
        help_text="Service type identifier URI",
    )

    status = models.CharField(
        max_length=200,
        choices=SERVICE_STATUS_CHOICES,
        default="http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted",
        help_text="Current service status",
    )

    status_starting_time = models.DateTimeField(
        default=timezone.now, help_text="When this status became effective"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Trust Service"
        verbose_name_plural = "Trust Services"
        ordering = ["pk"]

    def __str__(self):
        primary_name = self.names.first()
        return primary_name.value if primary_name else f"Service #{self.pk}"


class ServiceName(MultiLangName):
    """Multi-language names for Trust Service."""

    service = models.ForeignKey(
        TrustService, on_delete=models.CASCADE, related_name="names"
    )

    class Meta:
        verbose_name = "Service Name"
        verbose_name_plural = "Service Names"


class ServiceCertificate(models.Model):
    """
    Digital identity certificate for Trust Service - equivalent to .pem files

    Stores X.509 certificates that identify a trust service.
    """

    service = models.ForeignKey(
        TrustService, on_delete=models.CASCADE, related_name="certificates"
    )

    # Certificate data - store as base64-encoded DER or PEM content
    certificate_pem = models.TextField(
        help_text="PEM-encoded X.509 certificate (including BEGIN/END markers)"
    )

    # Optional metadata extracted from certificate
    subject_cn = models.CharField(
        max_length=500, blank=True, help_text="Subject Common Name"
    )
    issuer_cn = models.CharField(
        max_length=500, blank=True, help_text="Issuer Common Name"
    )
    serial_number = models.CharField(max_length=100, blank=True)
    not_before = models.DateTimeField(null=True, blank=True)
    not_after = models.DateTimeField(null=True, blank=True)

    # X.509 Subject Distinguished Name (for ServiceDigitalIdentity output)
    x509_subject_name = models.CharField(
        max_length=1000,
        blank=True,
        help_text="X.509 Subject Distinguished Name (e.g., CN=..., O=..., C=...)",
    )

    # X.509 Subject Key Identifier (for ServiceDigitalIdentity output)
    x509_ski = models.CharField(
        max_length=200,
        blank=True,
        help_text="X.509 Subject Key Identifier (Base64 encoded)",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Service Certificate"
        verbose_name_plural = "Service Certificates"

    def __str__(self):
        return self.subject_cn or f"Certificate #{self.pk}"

    def get_base64_der(self):
        """Extract base64-encoded DER from PEM content."""
        pem = self.certificate_pem.strip()
        # Remove PEM headers/footers
        lines = pem.split("\n")
        der_lines = [line for line in lines if not line.startswith("-----")]
        return "".join(der_lines)


class ServiceSupplyPoint(models.Model):
    """Service supply point URI for Trust Service."""

    service = models.ForeignKey(
        TrustService, on_delete=models.CASCADE, related_name="supply_points"
    )
    uri = models.URLField(max_length=500, help_text="Service supply point URI")

    class Meta:
        verbose_name = "Service Supply Point"
        verbose_name_plural = "Service Supply Points"

    def __str__(self):
        return self.uri


class ServiceDefinitionURI(MultiLangURI):
    """Multi-language service definition URIs."""

    service = models.ForeignKey(
        TrustService, on_delete=models.CASCADE, related_name="definition_uris"
    )

    class Meta:
        verbose_name = "Service Definition URI"
        verbose_name_plural = "Service Definition URIs"


# =============================================================================
# Service History (for status changes over time)
# =============================================================================
class ServiceHistoryInstance(models.Model):
    """
    Historical status record for a Trust Service.

    ETSI TS 119612 requires maintaining history of status changes.
    """

    service = models.ForeignKey(
        TrustService, on_delete=models.CASCADE, related_name="history"
    )

    service_type = models.CharField(
        max_length=200,
        choices=SERVICE_TYPE_CHOICES,
        help_text="Service type at this point in history",
    )

    status = models.CharField(
        max_length=200,
        choices=SERVICE_STATUS_CHOICES,
        help_text="Status at this point in history",
    )

    status_starting_time = models.DateTimeField(
        help_text="When this historical status became effective"
    )

    class Meta:
        verbose_name = "Service History Instance"
        verbose_name_plural = "Service History Instances"
        ordering = ["-status_starting_time"]

    def __str__(self):
        return f"{self.service} - {self.status} ({self.status_starting_time})"


class ServiceHistoryName(MultiLangName):
    """Multi-language names for Service History Instance."""

    history = models.ForeignKey(
        ServiceHistoryInstance, on_delete=models.CASCADE, related_name="names"
    )

    class Meta:
        verbose_name = "History Service Name"
        verbose_name_plural = "History Service Names"


class ServiceHistoryDigitalId(models.Model):
    """
    Digital identity for Service History Instance.

    Used to specify X509SubjectName and X509SKI in service history.
    This is different from the main certificate as history may only reference
    the subject name and SKI without the full certificate.
    """

    history = models.ForeignKey(
        ServiceHistoryInstance, on_delete=models.CASCADE, related_name="digital_ids"
    )

    x509_subject_name = models.CharField(
        max_length=1000,
        blank=True,
        help_text="X.509 Subject Distinguished Name (e.g., CN=..., O=..., C=...)",
    )

    x509_ski = models.CharField(
        max_length=200,
        blank=True,
        help_text="X.509 Subject Key Identifier (Base64 encoded)",
    )

    class Meta:
        verbose_name = "History Digital ID"
        verbose_name_plural = "History Digital IDs"

    def __str__(self):
        if self.x509_subject_name:
            return f"DN: {self.x509_subject_name[:50]}..."
        return f"SKI: {self.x509_ski}"


class ServiceHistoryQualification(models.Model):
    """
    Qualification element for Service History Instance.

    Used to specify historical QC qualifications per ETSI TS 119612.
    """

    history = models.ForeignKey(
        ServiceHistoryInstance, on_delete=models.CASCADE, related_name="qualifications"
    )

    qualifier_uri = models.CharField(
        max_length=200, help_text="Qualifier URI (e.g., QCNoQSCD)"
    )

    criteria_assert = models.CharField(
        max_length=20, default="none", help_text="Criteria list assertion type"
    )

    # Key Usage bits for CriteriaList
    key_usage = models.BooleanField(default=False)
    key_usage_digital_signature = models.BooleanField(default=False)
    key_usage_non_repudiation = models.BooleanField(default=True)
    key_usage_key_encipherment = models.BooleanField(default=False)
    key_usage_data_encipherment = models.BooleanField(default=False)
    key_usage_key_agreement = models.BooleanField(default=False)
    key_usage_key_cert_sign = models.BooleanField(default=False)
    key_usage_crl_sign = models.BooleanField(default=False)
    key_usage_encipher_only = models.BooleanField(default=False)
    key_usage_decipher_only = models.BooleanField(default=False)

    class Meta:
        verbose_name = "History Qualification"
        verbose_name_plural = "History Qualifications"

    def __str__(self):
        return f"Qualification for {self.history}"


class ServiceHistoryAdditionalInfo(models.Model):
    """
    Additional Service Information for Service History Instance.

    Used to specify historical additional service info per ETSI TS 119612.
    """

    history = models.ForeignKey(
        ServiceHistoryInstance, on_delete=models.CASCADE, related_name="additional_info"
    )

    uri = models.CharField(
        max_length=200, help_text="Additional service information URI"
    )

    language = models.CharField(max_length=5, default="en")

    critical = models.BooleanField(
        default=True, help_text="Whether this extension is critical"
    )

    class Meta:
        verbose_name = "History Additional Info"
        verbose_name_plural = "History Additional Info"

    def __str__(self):
        return f"AdditionalInfo for {self.history}"


# =============================================================================
# Service Information Extensions (ETSI TS 119612 Qualifications & Additional Info)
# =============================================================================
QUALIFIER_URI_CHOICES = [
    ("http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/QCNoSSCD", "QC No SSCD"),
    ("http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/QCNoQSCD", "QC No QSCD"),
    ("http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/QCWithSSCD", "QC With SSCD"),
    ("http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/QCWithQSCD", "QC With QSCD"),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/QCQSCDManagedOnBehalf",
        "QC QSCD Managed On Behalf",
    ),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/QCQSCDStatusAsInCert",
        "QC QSCD Status As In Cert",
    ),
    ("http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/QCForESig", "QC For ESig"),
    ("http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/QCForESeal", "QC For ESeal"),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/QCForWSA",
        "QC For Web Site Authentication",
    ),
]

CRITERIA_ASSERT_CHOICES = [
    ("all", "All"),
    ("atLeastOne", "At Least One"),
    ("none", "None"),
]


class ServiceQualification(models.Model):
    """
    Qualification element for Trust Service (ns5:Qualifications).

    Used to specify QC qualifications and criteria lists per ETSI TS 119612.
    """

    service = models.ForeignKey(
        TrustService, on_delete=models.CASCADE, related_name="qualifications"
    )

    qualifier_uri = models.CharField(
        max_length=200,
        choices=QUALIFIER_URI_CHOICES,
        help_text="Qualifier URI (e.g., QCNoQSCD)",
    )

    criteria_assert = models.CharField(
        max_length=20,
        choices=CRITERIA_ASSERT_CHOICES,
        default="none",
        help_text="Criteria list assertion type",
    )

    # Key Usage bits for CriteriaList
    key_usage = models.BooleanField(
        default=False, help_text="Include key usage criteria"
    )
    key_usage_digital_signature = models.BooleanField(default=False)
    key_usage_non_repudiation = models.BooleanField(default=True)
    key_usage_key_encipherment = models.BooleanField(default=False)
    key_usage_data_encipherment = models.BooleanField(default=False)
    key_usage_key_agreement = models.BooleanField(default=False)
    key_usage_key_cert_sign = models.BooleanField(default=False)
    key_usage_crl_sign = models.BooleanField(default=False)
    key_usage_encipher_only = models.BooleanField(default=False)
    key_usage_decipher_only = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Service Qualification"
        verbose_name_plural = "Service Qualifications"

    def __str__(self):
        return f"{self.get_qualifier_uri_display()} for {self.service}"


ADDITIONAL_SERVICE_INFO_CHOICES = [
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/ForeSignatures",
        "For e-Signatures",
    ),
    ("http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/ForeSeals", "For e-Seals"),
    (
        "http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/ForWebSiteAuthentication",
        "For Web Site Authentication",
    ),
    ("http://uri.etsi.org/TrstSvc/TrustedList/SvcInfoExt/RootCA-QC", "Root CA QC"),
]


class AdditionalServiceInformation(models.Model):
    """
    Additional Service Information extension for Trust Service.

    Used to specify additional service information URIs per ETSI TS 119612.
    """

    service = models.ForeignKey(
        TrustService, on_delete=models.CASCADE, related_name="additional_service_info"
    )

    uri = models.CharField(
        max_length=200,
        choices=ADDITIONAL_SERVICE_INFO_CHOICES,
        help_text="Additional service information URI",
    )

    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")

    critical = models.BooleanField(
        default=True, help_text="Whether this extension is critical"
    )

    class Meta:
        verbose_name = "Additional Service Information"
        verbose_name_plural = "Additional Service Information"

    def __str__(self):
        return f"{self.get_uri_display()} for {self.service}"
