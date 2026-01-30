"""
EUDI Wallet Relying Party Registration - Django Signals
Handles automatic population of intermediary cached fields and audit logging
"""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import (
    AuditLog,
    IntendedUse,
    LegalEntity,
    WalletRelyingParty,
    WRPUsesIntermediary,
)


@receiver(pre_save, sender=WRPUsesIntermediary)
def populate_intermediary_cached_fields(sender, instance, **kwargs):
    """
    Auto-populate cached fields from the intermediary WRP.
    This denormalization provides quick access without additional queries.
    """
    if instance.intermediary:
        # Cache the intermediary's identifier
        if (
            instance.intermediary.legal_entity
            and instance.intermediary.legal_entity.primary_identifier
        ):
            instance.intermediary_identifier = (
                instance.intermediary.legal_entity.primary_identifier.identifier_value
            )
        else:
            instance.intermediary_identifier = str(instance.intermediary.id)

        # Cache the trade name
        instance.intermediary_trade_name = instance.intermediary.trade_name

        # Cache the registry URI
        instance.intermediary_registry_uri = instance.intermediary.registry_uri


# ============================================================================
# AUDIT LOGGING SIGNALS
# ============================================================================

AUDITED_MODELS = [
    "WalletRelyingParty",
    "LegalEntity",
    "IntendedUse",
    "WRPEntitlement",
    "WRPAccessCertificate",
    "WRPRegistrationCertificate",
]


def get_model_changes(old_instance, new_instance):
    """Compare two model instances and return changed fields"""
    if old_instance is None:
        return None, model_to_dict(new_instance)

    old_values = {}
    new_values = {}

    for field in new_instance._meta.fields:
        field_name = field.name
        if field_name in ["created_at", "updated_at"]:
            continue

        old_value = getattr(old_instance, field_name, None)
        new_value = getattr(new_instance, field_name, None)

        if old_value != new_value:
            old_values[field_name] = str(old_value) if old_value is not None else None
            new_values[field_name] = str(new_value) if new_value is not None else None

    return old_values if old_values else None, new_values if new_values else None


def model_to_dict(instance):
    """Convert model instance to dictionary for audit logging"""
    result = {}
    for field in instance._meta.fields:
        field_name = field.name
        if field_name in ["created_at", "updated_at"]:
            continue
        value = getattr(instance, field_name, None)
        result[field_name] = str(value) if value is not None else None
    return result


def create_audit_log(
    table_name, record_id, action, old_values=None, new_values=None, user=None
):
    """Create an audit log entry"""
    AuditLog.objects.create(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
        changed_by=user,
    )


# Store original instances for comparison
_original_instances = {}


@receiver(pre_save, sender=WalletRelyingParty)
@receiver(pre_save, sender=LegalEntity)
@receiver(pre_save, sender=IntendedUse)
def store_original_instance(sender, instance, **kwargs):
    """Store original instance before save for comparison"""
    if instance.pk:
        try:
            _original_instances[f"{sender.__name__}_{instance.pk}"] = (
                sender.objects.get(pk=instance.pk)
            )
        except sender.DoesNotExist:
            _original_instances[f"{sender.__name__}_{instance.pk}"] = None


@receiver(post_save, sender=WalletRelyingParty)
@receiver(post_save, sender=LegalEntity)
@receiver(post_save, sender=IntendedUse)
def audit_log_on_save(sender, instance, created, **kwargs):
    """Create audit log entry on save"""
    key = f"{sender.__name__}_{instance.pk}"
    original = _original_instances.pop(key, None)

    if created:
        create_audit_log(
            table_name=sender.__name__,
            record_id=instance.pk,
            action="INSERT",
            new_values=model_to_dict(instance),
        )
    elif original:
        old_values, new_values = get_model_changes(original, instance)
        if old_values or new_values:
            create_audit_log(
                table_name=sender.__name__,
                record_id=instance.pk,
                action="UPDATE",
                old_values=old_values,
                new_values=new_values,
            )


@receiver(post_delete, sender=WalletRelyingParty)
@receiver(post_delete, sender=LegalEntity)
@receiver(post_delete, sender=IntendedUse)
def audit_log_on_delete(sender, instance, **kwargs):
    """Create audit log entry on delete"""
    create_audit_log(
        table_name=sender.__name__,
        record_id=instance.pk,
        action="DELETE",
        old_values=model_to_dict(instance),
    )
