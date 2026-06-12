"""
Unit tests for certificates.cert_decoder.decode_certificate.
"""

from datetime import datetime, timedelta, timezone

from certificates.cert_decoder import decode_certificate
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def _build_cert() -> str:
    """Build a self-signed EC certificate with the extensions an access
    certificate carries, returned as PEM."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "SE"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Somelegalname"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Sometradename"),
            x509.NameAttribute(x509.ObjectIdentifier("2.5.4.97"), "LEIXG-LEI"),
        ]
    )
    issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "SE Access Certificate Authority")]
    )
    now = datetime(2026, 6, 12, 9, 25, 0, tzinfo=timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(0x550F1BB2537189420D595C460012AA2AF03DDB51)
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.SERVER_AUTH]
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("service.example.se"),
                    x509.UniformResourceIdentifier("https://service.example.se:8008/"),
                    x509.RFC822Name("contact@example.se"),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA384())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def test_decode_returns_none_for_garbage():
    assert decode_certificate("not a pem") is None


def test_decode_returns_none_for_empty():
    assert decode_certificate("") is None


def test_decode_basic_fields():
    decoded = decode_certificate(_build_cert())
    assert decoded["version"] == "v3"
    assert decoded["serial_hex"] == "550F1BB2537189420D595C460012AA2AF03DDB51"
    assert decoded["signature_algorithm"] == "ecdsa-with-SHA384"
    assert len(decoded["fingerprint_sha256"]) == 64


def test_decode_subject_and_issuer_attrs():
    decoded = decode_certificate(_build_cert())
    subj = {a["oid"]: a["value"] for a in decoded["subject_attrs"]}
    assert subj["2.5.4.6"] == "SE"
    assert subj["2.5.4.10"] == "Somelegalname"
    assert subj["2.5.4.97"] == "LEIXG-LEI"
    issuer = {a["value"] for a in decoded["issuer_attrs"]}
    assert "SE Access Certificate Authority" in issuer


def test_decode_public_key_is_ec_p256():
    decoded = decode_certificate(_build_cert())
    assert decoded["public_key"]["type"] == "Elliptic Curve (EC)"
    assert "secp256r1" in decoded["public_key"]["details"]
    assert decoded["public_key"]["hex"]


def test_decode_extensions_include_eku_and_san():
    decoded = decode_certificate(_build_cert())
    by_name = {e["name"]: e for e in decoded["extensions"]}

    assert by_name["Basic Constraints"]["critical"] is True
    assert by_name["Basic Constraints"]["lines"] == ["CA: False"]

    ku = by_name["Key Usage"]
    assert ku["critical"] is True
    assert ku["lines"] == ["Digital Signature"]

    eku_lines = by_name["Extended Key Usage"]["lines"]
    assert any("TLS Web Client Authentication" in line for line in eku_lines)
    assert any("TLS Web Server Authentication" in line for line in eku_lines)

    san_lines = by_name["Subject Alternative Name"]["lines"]
    # domain_uri -> dNSName (host only); instance_uri -> URI (keeps port)
    assert "DNS: service.example.se" in san_lines
    assert "URI: https://service.example.se:8008/" in san_lines
    assert "email: contact@example.se" in san_lines
