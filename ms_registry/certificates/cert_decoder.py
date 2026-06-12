"""
Decode a PEM X.509 certificate into a structured, display-friendly dict.

Used by the "Show Access Certificate" page to render every field and
extension of the issued certificate (not just the columns stored on
EntityAccessCertificate).
"""

import hashlib

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed448, ed25519, rsa

# Friendly names for the X.509 extensions we expect on access certificates.
# Falls back to the dotted OID string for anything not listed.
_EXTENSION_NAMES = {
    "2.5.29.14": "Subject Key Identifier",
    "2.5.29.15": "Key Usage",
    "2.5.29.17": "Subject Alternative Name",
    "2.5.29.19": "Basic Constraints",
    "2.5.29.31": "CRL Distribution Points",
    "2.5.29.32": "Certificate Policies",
    "2.5.29.35": "Authority Key Identifier",
    "2.5.29.37": "Extended Key Usage",
    "1.3.6.1.5.5.7.1.1": "Authority Information Access",
    "1.3.6.1.5.5.7.1.3": "qcStatements",
}

# Friendly names for Extended Key Usage OIDs.
_EKU_NAMES = {
    "1.3.6.1.5.5.7.3.1": "TLS Web Server Authentication",
    "1.3.6.1.5.5.7.3.2": "TLS Web Client Authentication",
    "1.3.6.1.5.5.7.3.3": "Code Signing",
    "1.3.6.1.5.5.7.3.4": "Email Protection",
    "1.3.6.1.5.5.7.3.8": "Time Stamping",
    "1.3.6.1.5.5.7.3.9": "OCSP Signing",
}


def _hex(data: bytes) -> str:
    return ":".join(f"{b:02X}" for b in data)


def _name_attributes(name: x509.Name) -> list[dict]:
    """Break a Name into a list of {oid, name, value} attribute rows."""
    attrs = []
    for attr in name:
        attrs.append(
            {
                "oid": attr.oid.dotted_string,
                "name": attr.rfc4514_attribute_name,
                "value": attr.value,
            }
        )
    return attrs


def _public_key_info(cert: x509.Certificate) -> dict:
    pub = cert.public_key()
    info = {"type": type(pub).__name__, "details": "", "hex": ""}

    if isinstance(pub, ec.EllipticCurvePublicKey):
        info["type"] = "Elliptic Curve (EC)"
        info["details"] = f"{pub.curve.name} ({pub.key_size} bit)"
        info["hex"] = _hex(
            pub.public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint,
            )
        )
    elif isinstance(pub, rsa.RSAPublicKey):
        info["type"] = "RSA"
        info["details"] = f"{pub.key_size} bit, exponent {pub.public_numbers().e}"
        info["hex"] = format(pub.public_numbers().n, "X")
    elif isinstance(pub, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
        info["type"] = type(pub).__name__.replace("PublicKey", "")
        info["hex"] = _hex(
            pub.public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
        )
    return info


def _format_general_name(gn: x509.GeneralName) -> str:
    if isinstance(gn, x509.UniformResourceIdentifier):
        return f"URI: {gn.value}"
    if isinstance(gn, x509.RFC822Name):
        return f"email: {gn.value}"
    if isinstance(gn, x509.DNSName):
        return f"DNS: {gn.value}"
    if isinstance(gn, x509.IPAddress):
        return f"IP: {gn.value}"
    if isinstance(gn, x509.DirectoryName):
        return f"DirName: {gn.value.rfc4514_string()}"
    if isinstance(gn, x509.RegisteredID):
        return f"Registered ID: {gn.value.dotted_string}"
    if isinstance(gn, x509.OtherName):
        return f"otherName ({gn.type_id.dotted_string}): {_hex(gn.value)}"
    return str(gn)


def _format_extension_value(value) -> list[str]:  # noqa: C901 — type dispatch
    """Return a list of human-readable lines for an extension's value."""
    if isinstance(value, x509.BasicConstraints):
        line = f"CA: {value.ca}"
        if value.path_length is not None:
            line += f", path length: {value.path_length}"
        return [line]

    if isinstance(value, x509.KeyUsage):
        names = [
            ("digital_signature", "Digital Signature"),
            ("content_commitment", "Content Commitment (Non Repudiation)"),
            ("key_encipherment", "Key Encipherment"),
            ("data_encipherment", "Data Encipherment"),
            ("key_agreement", "Key Agreement"),
            ("key_cert_sign", "Certificate Sign"),
            ("crl_sign", "CRL Sign"),
        ]
        out = [label for attr, label in names if getattr(value, attr)]
        # encipher_only / decipher_only only valid when key_agreement is set
        if value.key_agreement:
            if value.encipher_only:
                out.append("Encipher Only")
            if value.decipher_only:
                out.append("Decipher Only")
        return out or ["(none)"]

    if isinstance(value, x509.ExtendedKeyUsage):
        return [
            f"{_EKU_NAMES.get(oid.dotted_string, oid.dotted_string)} "
            f"({oid.dotted_string})"
            for oid in value
        ]

    if isinstance(value, x509.SubjectAlternativeName):
        return [_format_general_name(gn) for gn in value]

    if isinstance(value, x509.CertificatePolicies):
        out = []
        for policy in value:
            out.append(f"Policy: {policy.policy_identifier.dotted_string}")
            for qual in policy.policy_qualifiers or []:
                if isinstance(qual, str):
                    out.append(f"  CPS: {qual}")
                else:
                    out.append(f"  {qual}")
        return out

    if isinstance(value, x509.AuthorityKeyIdentifier):
        if value.key_identifier:
            return [_hex(value.key_identifier)]
        return ["(no keyIdentifier)"]

    if isinstance(value, x509.SubjectKeyIdentifier):
        return [_hex(value.digest)]

    if isinstance(value, x509.CRLDistributionPoints):
        out = []
        for dp in value:
            for gn in dp.full_name or []:
                out.append(_format_general_name(gn))
        return out

    if isinstance(value, x509.AuthorityInformationAccess):
        out = []
        for desc in value:
            method = desc.access_method._name or desc.access_method.dotted_string
            out.append(f"{method}: {_format_general_name(desc.access_location)}")
        return out

    if isinstance(value, x509.UnrecognizedExtension):
        return [f"raw: {_hex(value.value)}"]

    return [str(value)]


def decode_certificate(pem: str) -> dict | None:
    """
    Parse a PEM certificate and return a dict of all its fields, or None if
    the PEM cannot be parsed.
    """
    if not pem:
        return None
    try:
        cert = x509.load_pem_x509_certificate(pem.encode())
    except Exception:
        return None

    der = cert.public_bytes(serialization.Encoding.DER)

    try:
        sig_algo = cert.signature_algorithm_oid._name
    except Exception:
        sig_algo = cert.signature_algorithm_oid.dotted_string

    extensions = []
    for ext in cert.extensions:
        extensions.append(
            {
                "name": _EXTENSION_NAMES.get(
                    ext.oid.dotted_string, ext.oid.dotted_string
                ),
                "oid": ext.oid.dotted_string,
                "critical": ext.critical,
                "lines": _format_extension_value(ext.value),
            }
        )

    return {
        "version": cert.version.name,  # e.g. "v3"
        "serial_hex": format(cert.serial_number, "X"),
        "serial_int": cert.serial_number,
        "signature_algorithm": sig_algo,
        "fingerprint_sha256": hashlib.sha256(der).hexdigest(),
        "fingerprint_sha1": hashlib.sha1(der).hexdigest(),
        "issuer": cert.issuer.rfc4514_string(),
        "issuer_attrs": _name_attributes(cert.issuer),
        "subject": cert.subject.rfc4514_string(),
        "subject_attrs": _name_attributes(cert.subject),
        "not_before": cert.not_valid_before_utc,
        "not_after": cert.not_valid_after_utc,
        "public_key": _public_key_info(cert),
        "extensions": extensions,
    }
