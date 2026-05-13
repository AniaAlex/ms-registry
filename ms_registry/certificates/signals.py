"""
Certificate signals.

Auto-revoke access certificates when entity registration status changes to
SUSPENDED or REVOKED.
"""

import logging

from certificates.ca_integration import revoke_entity_certificates
from core.models import RegistrationStatus
from django.db.models.signals import pre_save
from django.dispatch import receiver
from registry.models import RegisteredEntity

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=RegisteredEntity)
def auto_revoke_certificates_on_status_change(sender, instance, **kwargs):
    """
    Automatically revoke all active certificates when entity status changes
    to SUSPENDED or REVOKED.

    Uses pre_save to compare old and new status values.
    """
    # Skip if this is a new entity (no pk yet)
    if not instance.pk:
        return

    # Get the old status from the database
    try:
        old_instance = RegisteredEntity.objects.get(pk=instance.pk)
    except RegisteredEntity.DoesNotExist:
        return

    old_status = old_instance.registration_status
    new_status = instance.registration_status

    # Check if status changed to SUSPENDED or REVOKED
    revocation_statuses = {RegistrationStatus.SUSPENDED, RegistrationStatus.REVOKED}

    if old_status not in revocation_statuses and new_status in revocation_statuses:
        # Determine revocation reason based on status
        if new_status == RegistrationStatus.SUSPENDED:
            reason = "certificateHold"  # Temporary suspension
        else:
            reason = "cessationOfOperation"  # Permanent revocation

        # Revoke all certificates
        count = revoke_entity_certificates(instance, reason=reason)

        if count > 0:
            logger.info(
                f"Auto-revoked {count} certificate(s) for entity {instance.id} "
                f"due to status change: {old_status} → {new_status}"
            )
