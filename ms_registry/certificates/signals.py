"""
Certificate signals.

Auto-revoke access certificates when entity registration status changes to
SUSPENDED or REVOKED.
"""

import logging

from certificates.ca_integration import revoke_entity_certificates
from core.models import RegistrationStatus
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from registry.models import RegisteredEntity

logger = logging.getLogger(__name__)

_REVOCATION_STATUSES = {RegistrationStatus.SUSPENDED, RegistrationStatus.REVOKED}


@receiver(pre_save, sender=RegisteredEntity)
def _snapshot_status_before_save(sender, instance, **kwargs):
    """Store old registration_status on the instance so post_save can compare."""
    if not instance.pk:
        instance._pre_save_status = None
        return
    try:
        instance._pre_save_status = RegisteredEntity.objects.values_list(
            "registration_status", flat=True
        ).get(pk=instance.pk)
    except RegisteredEntity.DoesNotExist:
        instance._pre_save_status = None


@receiver(post_save, sender=RegisteredEntity)
def auto_revoke_certificates_on_status_change(sender, instance, created, **kwargs):
    """
    Revoke all active certificates when entity status changes to SUSPENDED or REVOKED.

    Runs in post_save so the status change is already persisted, and defers the
    actual revocation to transaction.on_commit so a subsequent rollback cannot
    leave certificates revoked while the status change is undone.
    """
    if created:
        return

    old_status = getattr(instance, "_pre_save_status", None)
    new_status = instance.registration_status

    if old_status in _REVOCATION_STATUSES or new_status not in _REVOCATION_STATUSES:
        return

    reason = (
        "certificateHold"
        if new_status == RegistrationStatus.SUSPENDED
        else "cessationOfOperation"
    )
    entity_pk = instance.pk

    def do_revoke():
        try:
            entity = RegisteredEntity.objects.get(pk=entity_pk)
        except RegisteredEntity.DoesNotExist:
            return
        count = revoke_entity_certificates(entity, reason=reason)
        if count > 0:
            logger.info(
                "Auto-revoked %d certificate(s) for entity %s "
                "due to status change: %s → %s",
                count,
                entity_pk,
                old_status,
                new_status,
            )

    transaction.on_commit(do_revoke)
