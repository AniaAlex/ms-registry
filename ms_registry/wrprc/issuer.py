"""
WRPRC Issuer - Signs and issues Wallet Relying Party Registration Certificates

Per ETSI TS 119 475, the WRPRC is a JWT with:
- Header: typ="rc-wrp+jwt", alg="ES256", x5c=[cert chain]
- Payload: RP information, entitlements, requested credentials, etc.
"""

import hashlib
import uuid
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone


class WRPRCIssuer:
    """
    Issues WRPRCs for registered entities.

    This class builds the WRPRC payload from registry data and
    delegates signing to a key service (HSM/KMS in production).
    """

    def __init__(self, signer=None):
        """
        Initialize the issuer.

        Args:
            signer: A signing backend (LocalSigner, KMSSigner, HSMSigner)
                   If None, uses the configured default signer.
        """
        self.signer = signer or self._get_default_signer()

    def _get_default_signer(self):
        """Get the default signer based on settings."""
        signer_type = getattr(settings, "WRPRC_SIGNER_TYPE", "registry")

        if signer_type == "registry":
            # Integrated mode: use registry's main signing key
            from .signing import RegistrySigner

            return RegistrySigner()
        elif signer_type == "local":
            from .signing import LocalSigner

            return LocalSigner()
        elif signer_type == "kms":
            from .signing import KMSSigner

            return KMSSigner(settings.WRPRC_KMS_KEY_ID)
        else:
            raise ValueError(f"Unknown signer type: {signer_type}")

    def issue(
        self,
        registered_entity,
        intended_use=None,
        validity_days: int = 365,
    ) -> dict:
        """
        Issue a WRPRC for a registered entity.

        Args:
            registered_entity: The RegisteredEntity to issue WRPRC for
            intended_use: Specific IntendedUse (optional)
            validity_days: How long the WRPRC is valid

        Returns:
            dict with 'jwt' (the signed WRPRC) and 'record' (IssuedWRPRC instance)
        """
        from .models import IssuedWRPRC

        # Get or create status list
        status_list = self._get_or_create_status_list()

        # Allocate index in status list
        status_index = status_list.allocate_index()

        # Generate JWT ID
        jti = str(uuid.uuid4())

        # Calculate timestamps
        iat = timezone.now()
        exp = iat + timedelta(days=validity_days)

        # Build payload
        payload = self._build_payload(
            registered_entity=registered_entity,
            intended_use=intended_use,
            jti=jti,
            iat=iat,
            exp=exp,
            status_list=status_list,
            status_index=status_index,
        )

        # Build headers
        headers = self._build_headers()

        # Sign
        signed_jwt = self.signer.sign(payload, headers)

        # Calculate hash for audit
        jwt_hash = hashlib.sha256(signed_jwt.encode()).hexdigest()

        # Create record
        record = IssuedWRPRC.objects.create(
            registered_entity=registered_entity,
            intended_use=intended_use,
            status_list=status_list,
            status_list_index=status_index,
            expires_at=exp,
            jwt_hash=jwt_hash,
            jti=jti,
        )

        return {
            "jwt": signed_jwt,
            "record": record,
            "expires_at": exp,
        }

    def _build_payload(
        self,
        registered_entity,
        intended_use,
        jti: str,
        iat: datetime,
        exp: datetime,
        status_list,
        status_index: int,
    ) -> dict:
        """Build the WRPRC JWT payload."""

        legal_entity = registered_entity.legal_entity

        # Base payload
        payload = {
            # JWT standard claims
            "jti": jti,
            "iat": int(iat.timestamp()),
            "exp": int(exp.timestamp()),
            # RP identification
            "name": legal_entity.legal_name,
            "sub": {
                "legal_name": legal_entity.legal_name,
            },
            # Country
            "country": (
                legal_entity.country if hasattr(legal_entity, "country") else "SE"
            ),
            # Public sector body flag
            "public_body": registered_entity.is_public_sector_body,
            # Status for revocation checking
            "status": {
                "status_list": {
                    "idx": status_index,
                    "uri": status_list.get_uri(),
                }
            },
        }

        # Add identifier (LEI, EUID, etc.)
        if hasattr(legal_entity, "lei") and legal_entity.lei:
            payload["sub"]["id"] = f"LEI-{legal_entity.lei}"
        elif hasattr(legal_entity, "euid") and legal_entity.euid:
            payload["sub"]["id"] = f"EUID-{legal_entity.euid}"

        # Add entitlements
        entitlements = registered_entity.entitlements.all()
        if entitlements:
            payload["entitlements"] = [
                f"https://uri.etsi.org/19475/Entitlement/{e.entitlement_type}"
                for e in entitlements
            ]

        # Add intended use specific data
        if intended_use:
            payload["purpose"] = self._build_purpose(intended_use)
            payload["privacy_policy"] = intended_use.privacy_policy_url
            payload["credentials"] = self._build_credentials(intended_use)
        else:
            # Include all intended uses
            intended_uses = registered_entity.intended_uses.all()
            if intended_uses:
                # Use first intended use for purpose/privacy_policy
                first_use = intended_uses.first()
                payload["purpose"] = self._build_purpose(first_use)
                payload["privacy_policy"] = first_use.privacy_policy_url

                # Combine credentials from all intended uses
                all_credentials = []
                for use in intended_uses:
                    all_credentials.extend(self._build_credentials(use))
                payload["credentials"] = all_credentials

        # Add info URI if available
        if hasattr(registered_entity, "info_uri") and registered_entity.info_uri:
            payload["info_uri"] = registered_entity.info_uri

        # Add provided attestations for issuers (PID/EAA providers)
        if self._is_issuer(registered_entity):
            payload["provided_attestations"] = self._build_provided_attestations(
                registered_entity
            )

        return payload

    def _build_headers(self) -> dict:
        """Build the JWT headers."""
        from .models import SigningKey

        signing_key = SigningKey.get_active_key()
        if not signing_key:
            raise ValueError("No active signing key available")

        return {
            "typ": "rc-wrp+jwt",
            "alg": signing_key.algorithm,
            "kid": signing_key.kid,
            "x5c": signing_key.x5c,
        }

    def _build_purpose(self, intended_use) -> list:
        """Build multilingual purpose array."""
        purposes = []

        # Primary purpose
        if intended_use.purpose:
            purposes.append({"lang": "en-US", "value": intended_use.purpose})

        # Add translations if available
        if hasattr(intended_use, "purpose_translations"):
            for lang, value in intended_use.purpose_translations.items():
                purposes.append({"lang": lang, "value": value})

        return purposes

    def _build_credentials(self, intended_use) -> list:
        """Build credentials array from intended use."""
        credentials = []

        for credential in intended_use.credentials.all():
            cred_entry = {
                "format": credential.format,  # e.g., "dc+sd-jwt", "mso_mdoc"
            }

            # Add metadata
            if credential.vct:
                cred_entry["meta"] = {"vct_values": [credential.vct]}
            elif credential.doctype:
                cred_entry["meta"] = {"doctype_value": credential.doctype}

            # Add requested claims
            claims = credential.claims.all()
            if claims:
                cred_entry["claims"] = [{"path": [c.name]} for c in claims]

            credentials.append(cred_entry)

        return credentials

    def _is_issuer(self, registered_entity) -> bool:
        """Check if entity is an issuer (PID/EAA provider)."""
        issuer_entitlements = [
            "PID_Provider",
            "QEAA_Provider",
            "Non_Q_EAA_Provider",
            "PUB_EAA_Provider",
        ]

        return registered_entity.entitlements.filter(
            entitlement_type__in=issuer_entitlements
        ).exists()

    def _build_provided_attestations(self, registered_entity) -> list:
        """Build provided attestations for issuer entities."""
        # This would come from a related model tracking what the issuer provides
        # For now, return empty list
        return []

    def _get_or_create_status_list(self):
        """Get the current status list or create a new one."""
        from .models import StatusList

        # Try to get an active status list with capacity
        status_list = (
            StatusList.objects.filter(purpose=StatusList.Purpose.REVOCATION)
            .order_by("-created_at")
            .first()
        )

        if not status_list or status_list.current_index >= status_list.capacity - 100:
            # Create new status list
            list_id = f"wrprc-{uuid.uuid4().hex[:8]}"
            status_list = StatusList.objects.create(
                list_id=list_id,
                purpose=StatusList.Purpose.REVOCATION,
                capacity=10000,
            )

        return status_list
