"""
Unit tests for certificates.cert_decoder.decode_certificate.
"""

from datetime import datetime, timedelta, timezone

from certificates.cert_decoder import (
    _decode_oid,
    _format_qc_statements,
    _read_tlv,
    decode_certificate,
)
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


def _build_cert_with_qc_statements() -> str:
    """Self-signed EC cert carrying a qcStatements extension with QcCompliance
    plus two TS 119 475 entitlement OIDs."""
    from certificates.ca_integration import _der_tlv, _encode_oid

    qc = b""
    qc += _der_tlv(0x30, _der_tlv(0x06, _encode_oid("0.4.0.1862.1.1")))  # QcCompliance
    for oid in ("0.4.0.19475.1.2", "0.4.0.19475.1.1"):  # QEAA, Service_Provider
        qc += _der_tlv(0x30, _der_tlv(0x06, _encode_oid(oid)))
    qc_value = _der_tlv(0x30, qc)

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "qc-test")])
    now = datetime(2026, 6, 12, 9, 25, 0, tzinfo=timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.UnrecognizedExtension(
                x509.ObjectIdentifier("1.3.6.1.5.5.7.1.3"), qc_value
            ),
            critical=False,
        )
        .sign(key, hashes.SHA384())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def test_decode_qc_statements_renders_entitlement_oids():
    decoded = decode_certificate(_build_cert_with_qc_statements())
    by_name = {e["name"]: e for e in decoded["extensions"]}

    lines = by_name["qcStatements"]["lines"]
    # decoded as dotted OIDs, not a raw hex blob
    assert "0.4.0.1862.1.1" in lines  # QcCompliance
    assert "0.4.0.19475.1.2" in lines  # QEAA_Provider entitlement
    assert "0.4.0.19475.1.1" in lines  # Service_Provider entitlement
    assert not any(line.startswith("raw:") for line in lines)


def test_qc_statements_handles_long_form_length():
    """A qcStatements value whose content exceeds 127 bytes uses DER long-form
    length encoding; the parser must read it and return every statement."""
    from certificates.ca_integration import _der_tlv, _encode_oid

    # 15 entitlement statements (~11 bytes each) → outer content > 127 bytes.
    oids = [f"0.4.0.19475.1.{n}" for n in range(1, 16)]
    qc = b"".join(_der_tlv(0x30, _der_tlv(0x06, _encode_oid(o))) for o in oids)
    der = _der_tlv(0x30, qc)
    assert der[1] & 0x80  # sanity: outer length is long-form

    lines = _format_qc_statements(der)
    assert lines == oids


def test_read_tlv_parses_long_form_length():
    # tag 0x04, long-form length 0x81 0x80 (128 bytes), 128 content bytes
    payload = b"\x04\x81\x80" + b"\xaa" * 128
    tag, content, end = _read_tlv(payload, 0)
    assert tag == 0x04
    assert len(content) == 128
    assert end == len(payload)


def test_decode_oid_handles_arc_one_and_two():
    # 1.2.840.113549 (arc 1) and 2.5.29.19 (arc 2)
    from certificates.ca_integration import _encode_oid

    assert _decode_oid(_encode_oid("1.2.840.113549")) == "1.2.840.113549"
    assert _decode_oid(_encode_oid("2.5.29.19")) == "2.5.29.19"


def test_format_qc_statements_malformed_falls_back_to_raw():
    # Not a SEQUENCE (tag 0x04) and truncated garbage both → raw hex fallback
    assert _format_qc_statements(b"\x04\x02\xaa\xbb")[0].startswith("raw:")
    assert _format_qc_statements(b"\x30\x05\xaa")[0].startswith("raw:")


def test_decode_other_unrecognized_extension_stays_raw():
    """A non-qcStatements UnrecognizedExtension must still render as raw hex."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "raw-test")])
    now = datetime(2026, 6, 12, 9, 25, 0, tzinfo=timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(2)
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.UnrecognizedExtension(
                x509.ObjectIdentifier("1.2.3.4.5.6.7"), b"\xde\xad\xbe\xef"
            ),
            critical=False,
        )
        .sign(key, hashes.SHA384())
    )
    decoded = decode_certificate(cert.public_bytes(serialization.Encoding.PEM).decode())
    ext = next(e for e in decoded["extensions"] if e["oid"] == "1.2.3.4.5.6.7")
    assert ext["lines"][0].startswith("raw:")
