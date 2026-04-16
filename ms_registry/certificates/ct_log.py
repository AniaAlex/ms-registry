# TODO: Non-compliant. Add a proper CT log implementation in the future,
# e.g. using the python-ct library:

"""
Simplified RFC 9162 Certificate Transparency log for the ms-registry simplified flow.

In the simplified flow, ms-registry acts as the CT log.  This module produces
a proper RFC 9162 TransItem-encoded SCT for each uploaded access certificate,
signed with the registry's own ECDSA P-256 key.

This is NOT a full RFC 9162 Merkle-tree log.  It records a signed timestamp
that proves ms-registry saw the certificate at a given moment.  This module
only generates the CT log values; it does not persist them in
``EntityAccessCertificate`` because the former CT-related model fields
(``ct_log_id``, ``ct_log_timestamp``, ``ct_sct``) are not part of the current
schema (removed by migration 0002_remove_ct_log_fields).  Callers may use the
tuple returned by ``create_ct_log_entry()`` if they need to expose or persist
CT data elsewhere.

Wire format of the SCT bytes returned by ``create_ct_log_entry()``:

    TransItemList (RFC 9162 §4.5)
    └── TransItem
        ├── type   uint16 = 1  (x509_sct_v2)
        └── data   SignedCertificateTimestampDataV2 (RFC 9162 §4.8)
            ├── log_id      LogID = 1-byte len + OID value bytes
            ├── timestamp   uint64  milliseconds since epoch
            ├── extensions  uint16 len = 0  (empty)
            └── signature
                ├── scheme  uint16 = 0x0403  (ecdsa_secp256r1_sha256)
                ├── length  uint16
                └── bytes   ECDSA-P256(signed_content)

Signed content (simplified RFC 9162 §4.8 CertificateTimestamp):
    sct_version  uint8  = 1
    type         uint16 = 1  (x509_sct_v2)
    timestamp    uint64  milliseconds since epoch
    log_id       LogID
    cert_hash    uint16 len=32 + SHA-256(cert DER)
                 (simplified: full cert, not TBSCertificate)
    extensions   uint16 len = 0

Log ID (RFC 9162 §4.4):
    Each CT log is now identified by an OID allocated from the IANA CT Log
    Parameters registry.  Set the ``CT_LOG_OID`` environment variable to the
    OID assigned to this deployment.  The default below is a placeholder for
    the simplified/development flow only — replace it with an IANA-allocated
    OID before running a production log.

References:
    RFC 9162 §4.4  LogID definition (OID-based, replaces SHA-256(SPKI) from RFC 6962)
    RFC 9162 §4.5  TransItem and TransItemList
    RFC 9162 §4.6  SignedCertificateTimestamp structure
    RFC 9162 §4.8  SignedCertificateTimestampDataV2
    RFC 8446 §4.2.3  SignatureScheme (ecdsa_secp256r1_sha256 = 0x0403)
"""

import hashlib
import os
import struct
import time

from core.signing import load_private_key
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA

# RFC 9162 §4.5 TransItemType
_X509_SCT_V2 = 1  # uint16

# RFC 8446 §4.2.3 SignatureScheme for ECDSA P-256 + SHA-256
_ECDSA_SECP256R1_SHA256 = 0x0403  # uint16

# OID identifying this CT log instance (RFC 9162 §4.4).
# Override via CT_LOG_OID env var with an IANA-allocated OID for production.
#
# To obtain a real OID:
#   1. Apply for a Private Enterprise Number (PEN) at:
#      https://www.iana.org/assignments/enterprise-numbers/
#   2. Use your PEN to define a sub-arc, e.g. 1.3.6.1.4.1.<PEN>.1
#   3. Set CT_LOG_OID=1.3.6.1.4.1.<PEN>.1 in your environment.
_DEFAULT_LOG_OID = "1.3.6.1.4.1.99999.1"  # placeholder — not IANA-allocated


def _log_id() -> str:
    """
    RFC 9162 §4.4: LogID is an OID allocated from the IANA CT Log Parameters
    registry.  Returns the dotted-decimal OID string configured for this log.
    """
    return os.environ.get("CT_LOG_OID", _DEFAULT_LOG_OID)


def _encode_oid_value(oid_str: str) -> bytes:
    """
    Encode a dotted-decimal OID string as DER value bytes, tag and length
    excluded — as required by RFC 9162 §4.4 for LogID.

    Example: "1.3.6.1.4.1.99999.1" → b'\\x2b\\x06\\x01\\x04\\x01\\x86\\x8d\\x1f\\x01'
    """
    parts = [int(x) for x in oid_str.split(".")]
    result = bytearray([40 * parts[0] + parts[1]])
    for n in parts[2:]:
        if n == 0:
            result.append(0)
        else:
            buf = []
            while n:
                buf.append(n & 0x7F)
                n >>= 7
            buf.reverse()
            for i, b in enumerate(buf):
                result.append(b | (0x80 if i < len(buf) - 1 else 0))
    return bytes(result)


def _encode_log_id(oid_str: str) -> bytes:
    """
    LogID wire encoding: 1-byte length prefix + OID value bytes.
    RFC 9162 §4.4: opaque LogID<2..127>
    """
    value = _encode_oid_value(oid_str)
    return struct.pack("B", len(value)) + value


def _build_signed_content(
    timestamp_ms: int, log_id_bytes: bytes, cert_hash: bytes
) -> bytes:
    """
    Build the TLS-encoded content to be signed (simplified RFC 9162 §4.8).

    digitally-signed struct {
        uint8         sct_version = 1
        TransItemType type        = x509_sct_v2
        uint64        timestamp   (ms since epoch)
        LogID         log_id
        opaque        cert_hash<32..32>   SHA-256(cert DER),
                                         simplified from TBSCertificate
        opaque        extensions<0..2^16-1>  (empty)
    }
    """
    extensions = b""
    return (
        struct.pack("B", 1)  # sct_version
        + struct.pack(">H", _X509_SCT_V2)  # TransItemType
        + struct.pack(">Q", timestamp_ms)  # timestamp
        + log_id_bytes  # LogID (len-prefixed)
        + struct.pack(">H", len(cert_hash))
        + cert_hash  # cert_hash
        + struct.pack(">H", len(extensions))
        + extensions  # extensions
    )


def _encode_sct_data(log_id_bytes: bytes, timestamp_ms: int, signature: bytes) -> bytes:
    """
    SignedCertificateTimestampDataV2 — the ``data`` payload inside a TransItem
    (RFC 9162 §4.8).

    struct {
        LogID    log_id
        uint64   timestamp
        opaque   extensions<0..2^16-1>
        Signature: SignatureScheme uint16 + length uint16 + bytes
    }
    """
    extensions = b""
    return (
        log_id_bytes
        + struct.pack(">Q", timestamp_ms)
        + struct.pack(">H", len(extensions))
        + extensions
        + struct.pack(">H", _ECDSA_SECP256R1_SHA256)  # SignatureScheme
        + struct.pack(">H", len(signature))
        + signature  # Signature
    )


def _encode_trans_item(data: bytes) -> bytes:
    """
    TransItem: uint16 type + uint16 data_len + data  (RFC 9162 §4.5).
    """
    return struct.pack(">H", _X509_SCT_V2) + struct.pack(">H", len(data)) + data


def _encode_trans_item_list(items: list[bytes]) -> bytes:
    """
    TransItemList: uint16 total_len + concatenated TransItem bytes  (RFC 9162 §4.5).
    """
    payload = b"".join(items)
    return struct.pack(">H", len(payload)) + payload


def create_ct_log_entry(cert_der: bytes) -> tuple[str, int, bytes]:
    """
    Create a proper RFC 9162 TransItem-encoded SCT for an uploaded certificate.

    Produces a TransItemList containing a single x509_sct_v2 TransItem.
    The signed content follows RFC 9162 §4.8 with SHA-256 of the full
    certificate DER used in place of TBSCertificate (simplified flow).

    Args:
        cert_der: DER-encoded X.509 certificate bytes.

    Returns:
        log_id (str)        OID string identifying this CT log (RFC 9162 §4.4)
        timestamp_ms (int)  milliseconds since epoch
        sct_bytes (bytes)   TLS-encoded TransItemList (RFC 9162 §4.5)
    """
    private_key = load_private_key()
    oid_str = _log_id()
    log_id_bytes = _encode_log_id(oid_str)
    timestamp_ms = int(time.time() * 1000)

    cert_hash = hashlib.sha256(cert_der).digest()
    signed_content = _build_signed_content(timestamp_ms, log_id_bytes, cert_hash)
    signature = private_key.sign(signed_content, ECDSA(hashes.SHA256()))

    sct_data = _encode_sct_data(log_id_bytes, timestamp_ms, signature)
    trans_item = _encode_trans_item(sct_data)
    return oid_str, timestamp_ms, _encode_trans_item_list([trans_item])
