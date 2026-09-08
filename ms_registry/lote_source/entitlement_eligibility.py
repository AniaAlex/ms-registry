"""
Which entitlements are published in a LoTE (ETSI TS 119 602) rather than the
EUgeneric Trusted List.

Per ETSI TS 119 412-6 Annex A publication mapping: PID Providers and
PuB-EAA Providers are published in their own LoTE; QEAA is TL-bound and
non-qualified EAA is a member-state decision (this deployment publishes it
in the TL - see tsl_generator.registered_entity_prefill).

Kept as a set, not branching logic, so a future entitlement can be added to
LOTE_ELIGIBLE_ENTITLEMENTS without touching the callers that filter against it.
"""

from certificates.models import ISSUER_ENTITLEMENT_CHOICES
from core.models import EntitlementType

LOTE_ELIGIBLE_ENTITLEMENTS = {
    EntitlementType.PID_PROVIDER,
    EntitlementType.PUB_EAA_PROVIDER,
}

# Every entitlement that requires a signing certificate (certificates.models.
# EntitySigningCertificate) - qualified for the certificate step regardless of
# where it ends up published.
SIGNING_CERTIFICATE_ENTITLEMENTS = {t for t, _ in ISSUER_ENTITLEMENT_CHOICES}


def _held_entitlement_types(entity):
    return set(
        entity.entitlements.filter(is_active=True).values_list(
            "entitlement_type", flat=True
        )
    )


def lote_eligible_entitlement_types(entity):
    """Entitlement types held by this entity that are published via a LoTE."""
    held = _held_entitlement_types(entity)
    return [et for et in LOTE_ELIGIBLE_ENTITLEMENTS if et in held]


def any_signing_certificate_entitlement(entity):
    """True if this entity holds any entitlement that needs a signing certificate."""
    held = _held_entitlement_types(entity)
    return bool(SIGNING_CERTIFICATE_ENTITLEMENTS & held)
