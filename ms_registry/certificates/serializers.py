"""
Access certificate upload serializer.

Validates an X.509 PEM certificate against registered entity data per
ETSI TS 119 411-8 and the simplified flow requirements.

Checks performed:
  1. Valid PEM-encoded X.509 certificate
  2. Validity period (not expired, not yet valid)
  3. Subject DN matches registry data (C, O, organizationIdentifier)
     — organizationIdentifier mandatory per GEN-6.6.1-05
     — CN is optional (GEN-6.1.1-04 uses "may")
  4. KeyUsage: digitalSignature, critical
     — deferred to ETSI EN 319 411-1 §6.6.1; digitalSignature is standard
       for both electronic signatures (NCP/QCP-n) and seals (NCP/QCP-l)
  5. CertificatePolicies: at least one eudiwrp policy OID (§5.3)
  6. SAN RegisteredID OIDs cover all registered entitlements (TS 119 475)
  7. SAN contact info: at least one of uniformResourceIdentifier, rfc822Name,
     or otherName/id-at-telephoneNumber (GEN-6.6.1-07 [CHOICE])

Not checked (not required by TS 119 411-8):
  — ExtendedKeyUsage id-kp-clientAuth: spec explicitly excludes website auth
    certificates (GEN-6.6.1-01 NOTE)
  — CN value match: CN is optional ("may") per GEN-6.1.1-04
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from django.utils import timezone
from rest_framework import serializers

# ── ETSI TS 119 411-8 §5.3 – eudiwrp certificate policy OIDs ─────────────────
_EUDIWRP_POLICY_OIDS = {
    "0.4.0.194118.1.1",  # NCP-n-eudiwrp  (natural person)
    "0.4.0.194118.1.2",  # NCP-l-eudiwrp  (legal person)
    "0.4.0.194118.1.3",  # QCP-n-eudiwrp  (qualified, natural person)
    "0.4.0.194118.1.4",  # QCP-l-eudiwrp  (qualified, legal person)
}

# ── ETSI EN 319 412-1 – organizationIdentifier scheme prefixes ────────────────
_ORG_ID_PREFIX = {
    "EUID": "EUID",
    "VAT_NUMBER": "VAT",
    "LEI": "LEI",
    "EORI": "EORI",
    "NATIONAL_BUSINESS_REG": "NTR",
    "NATIONAL_TAX_REG": "TAX",
    "SERIAL_NUMBER": "PAS",
    "OTHER": "OTH",
}

# ── ETSI TS 119 475 – entitlement OIDs ───────────────────────────────────────
_ENTITLEMENT_OID = {
    "Service_Provider": "0.4.0.19475.1.1",
    "QEAA_Provider": "0.4.0.19475.1.2",
    "Non_Q_EAA_Provider": "0.4.0.19475.1.3",
    "PUB_EAA_Provider": "0.4.0.19475.1.4",
    "PID_Provider": "0.4.0.19475.1.5",
}

# ── ITU-T X.520 §6.7.1 – id-at-telephoneNumber OID ───────────────────────────
_TELEPHONE_NUMBER_OID = x509.ObjectIdentifier("2.5.4.20")


def _format_org_identifier(
    identifier_value: str, identifier_type: str, country: str
) -> str:
    """Format per ETSI EN 319 412-1. Example: NTR+SE+5568002755 → NTRSE-5568002755"""
    prefix = _ORG_ID_PREFIX.get(identifier_type, "OTH")
    return f"{prefix}{country}-{identifier_value}"


class AccessCertificateUploadSerializer(serializers.Serializer):
    """
    Validates an X.509 access certificate for upload in the simplified flow.

    Required context:
        entity (RegisteredEntity): The registered entity the certificate is for.

    After successful validation, ``validated_data["certificate_pem"]`` contains
    the parsed ``cryptography.x509.Certificate`` object.
    """

    certificate_pem = serializers.CharField(
        help_text="PEM-encoded X.509 access certificate.",
    )

    def validate_certificate_pem(self, value: str) -> x509.Certificate:
        """Parse PEM; return the Certificate object or raise ValidationError."""
        try:
            return x509.load_pem_x509_certificate(value.encode())
        except Exception as exc:
            raise serializers.ValidationError(f"Invalid PEM certificate: {exc}")

    def validate(self, data: dict) -> dict:
        cert: x509.Certificate = data["certificate_pem"]
        entity = self.context["entity"]
        errors: list[str] = []

        self._check_validity_period(cert, errors)
        self._check_subject_dn(cert, entity, errors)
        self._check_key_usage(cert, errors)
        self._check_policy_oids(cert, errors)
        self._check_entitlements(cert, entity, errors)
        self._check_san_contact_info(cert, errors)

        if errors:
            raise serializers.ValidationError({"certificate_pem": errors})

        return data

    # ── individual checks ─────────────────────────────────────────────────────

    def _check_validity_period(self, cert: x509.Certificate, errors: list) -> None:
        now = timezone.now()
        if now < cert.not_valid_before_utc:
            errors.append("Certificate is not yet valid.")
        if now > cert.not_valid_after_utc:
            errors.append("Certificate has expired.")

    def _check_subject_dn(self, cert: x509.Certificate, entity, errors: list) -> None:
        subject = cert.subject
        entity_type = entity.legal_entity.entity_type
        primary_id = entity.primary_identifier

        # C – mandatory for all entity types (ISO 3166-1 alpha-2 Member State)
        country_attrs = subject.get_attributes_for_oid(NameOID.COUNTRY_NAME)
        if not country_attrs:
            errors.append("Subject DN missing country (C).")
        else:
            expected_country = (primary_id.country_code if primary_id else None) or (
                entity.legal_entity.physical_address.country_code
                if entity.legal_entity.physical_address
                else None
            )
            if expected_country and country_attrs[0].value != expected_country:
                errors.append(
                    f"Subject DN country '{country_attrs[0].value}' does not match "
                    f"registry country '{expected_country}'."
                )

        cert_country = country_attrs[0].value if country_attrs else "XX"

        if entity_type == "natural_person":
            # Natural person (ETSI EN 319 412-2): Subject DN uses GN + SN, not O.
            # O (organizationName) is reserved for legal persons.
            np = entity.legal_entity.natural_person
            gn_attrs = subject.get_attributes_for_oid(NameOID.GIVEN_NAME)
            sn_attrs = subject.get_attributes_for_oid(NameOID.SURNAME)
            if not gn_attrs:
                errors.append("Subject DN missing given name (GN) for natural person.")
            elif np and gn_attrs[0].value != np.given_name:
                errors.append(
                    f"Subject DN given name '{gn_attrs[0].value}' does not match "
                    f"registry given name '{np.given_name}'."
                )
            if not sn_attrs:
                errors.append("Subject DN missing surname (SN) for natural person.")
            elif np and sn_attrs[0].value != np.family_name:
                errors.append(
                    f"Subject DN surname '{sn_attrs[0].value}' does not match "
                    f"registry family name '{np.family_name}'."
                )
            # Natural persons use serialNumber for their identifier
            # (ETSI EN 319 412-1 §5.1.3), not organizationIdentifier
            if primary_id:
                sn_id_attrs = subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)
                if not sn_id_attrs:
                    errors.append(
                        "Subject DN missing serialNumber for natural person identifier "
                        "(ETSI EN 319 412-1 §5.1.3)."
                    )
                else:
                    expected_sn = _format_org_identifier(
                        primary_id.identifier_value,
                        primary_id.identifier_type,
                        cert_country,
                    )
                    if sn_id_attrs[0].value != expected_sn:
                        errors.append(
                            f"Subject DN serialNumber '{sn_id_attrs[0].value}' "
                            f"does not match expected '{expected_sn}'."
                        )
        else:
            # Legal person (ETSI EN 319 412-3): Subject DN uses O (legal name)
            # and organizationIdentifier.
            org_attrs = subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            if not org_attrs:
                errors.append("Subject DN missing organization name (O).")
            else:
                # O must carry the legal name from the official record
                # (CIR Annex I pt 1), not the trade name — trade name
                # belongs in CN (GEN-6.1.1-04)
                legal_name = entity.legal_entity.display_name
                if org_attrs[0].value != legal_name:
                    errors.append(
                        f"Subject DN organization '{org_attrs[0].value}' "
                        f"does not match registry legal name '{legal_name}'."
                    )
            # organizationIdentifier is mandatory for legal persons (GEN-6.6.1-05).
            # The registry must have a primary identifier registered; without one
            # there is no value to encode and the certificate cannot be valid.
            if not primary_id:
                errors.append(
                    "Entity has no registered primary identifier; "
                    "organizationIdentifier is mandatory for legal persons "
                    "(GEN-6.6.1-05)."
                )
            else:
                oi_attrs = subject.get_attributes_for_oid(
                    NameOID.ORGANIZATION_IDENTIFIER
                )
                if not oi_attrs:
                    errors.append(
                        "Subject DN missing organizationIdentifier (GEN-6.6.1-05)."
                    )
                else:
                    expected_oi = _format_org_identifier(
                        primary_id.identifier_value,
                        primary_id.identifier_type,
                        cert_country,
                    )
                    if oi_attrs[0].value != expected_oi:
                        errors.append(
                            f"Subject DN organizationIdentifier '{oi_attrs[0].value}' "
                            f"does not match expected '{expected_oi}'."
                        )

    def _check_key_usage(self, cert: x509.Certificate, errors: list) -> None:
        try:
            ku_ext = cert.extensions.get_extension_for_class(x509.KeyUsage)
        except x509.ExtensionNotFound:
            errors.append("Certificate missing KeyUsage extension.")
            return
        if not ku_ext.critical:
            errors.append("KeyUsage extension must be critical.")
        if not ku_ext.value.digital_signature:
            errors.append("KeyUsage must include digitalSignature.")

    def _check_policy_oids(self, cert: x509.Certificate, errors: list) -> None:
        try:
            policies_ext = cert.extensions.get_extension_for_class(
                x509.CertificatePolicies
            )
        except x509.ExtensionNotFound:
            errors.append("Certificate missing CertificatePolicies extension.")
            return
        cert_oids = {pi.policy_identifier.dotted_string for pi in policies_ext.value}
        if not cert_oids.intersection(_EUDIWRP_POLICY_OIDS):
            errors.append(
                "Certificate must contain at least one eudiwrp policy OID "
                f"(expected one of: {', '.join(sorted(_EUDIWRP_POLICY_OIDS))})."
            )

    def _check_san_contact_info(self, cert: x509.Certificate, errors: list) -> None:
        """
        GEN-6.6.1-07 [CHOICE]: SAN must contain at least one contact method:
          - uniformResourceIdentifier (website)
          - rfc822Name (email)
          - otherName with type-id id-at-telephoneNumber (phone)
        """
        try:
            san = cert.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            ).value
        except x509.ExtensionNotFound:
            san = None

        has_uri = bool(san and san.get_values_for_type(x509.UniformResourceIdentifier))
        has_email = bool(san and san.get_values_for_type(x509.RFC822Name))
        has_phone = bool(
            san
            and any(
                n.type_id == _TELEPHONE_NUMBER_OID
                for n in san.get_values_for_type(x509.OtherName)
            )
        )

        if not (has_uri or has_email or has_phone):
            errors.append(
                "Certificate SAN must include at least one contact method: "
                "uniformResourceIdentifier (website), rfc822Name (email), or "
                "otherName/id-at-telephoneNumber (phone) — GEN-6.6.1-07."
            )

    def _check_entitlements(self, cert: x509.Certificate, entity, errors: list) -> None:
        registered = {e.entitlement_type for e in entity.entitlements.all()}
        if not registered:
            return

        # Collect RegisteredID OIDs from SAN
        cert_oids: set[str] = set()
        try:
            san_ext = cert.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            )
            for rid in san_ext.value.get_values_for_type(x509.RegisteredID):
                cert_oids.add(rid.dotted_string)
        except x509.ExtensionNotFound:
            pass

        expected_oids = {
            _ENTITLEMENT_OID[et] for et in registered if et in _ENTITLEMENT_OID
        }
        missing = expected_oids - cert_oids
        if missing:
            errors.append(
                f"Certificate SAN missing entitlement OIDs: "
                f"{', '.join(sorted(missing))}."
            )
