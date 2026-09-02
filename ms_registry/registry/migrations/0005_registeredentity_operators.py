from django.conf import settings
from django.db import migrations, models

_HELP_TEXT = (
    "Operators responsible for this entity. Never empty: the registering "
    "user is added on creation, and additional operators may be added "
    "afterwards."
)


def copy_participant_to_operators(apps, schema_editor):
    """Preserve existing ownership: add each entity's participant as its
    first operator so the many-to-many is never empty after migration."""
    RegisteredEntity = apps.get_model("registry", "RegisteredEntity")
    for entity in RegisteredEntity.objects.all():
        if entity.participant_id:
            entity.operators.add(entity.participant_id)


def restore_operator_to_participant(apps, schema_editor):
    """Reverse: pick one operator per entity to repopulate the participant FK.

    On reverse the FK is first re-added as nullable (reverse of RemoveField
    below), this fills it in, and the reverse of the AlterField then restores
    NOT NULL. That final step fails if any row is still NULL, so an entity with
    no operators cannot be reversed. The "never empty" rule is not DB-enforced
    (operators could be cleared via admin/ORM after creation), so fail fast with
    a clear message rather than leaving participant unset and having the NOT NULL
    restore blow up with an opaque IntegrityError.
    """
    RegisteredEntity = apps.get_model("registry", "RegisteredEntity")
    for entity in RegisteredEntity.objects.all():
        first_operator = entity.operators.first()
        if first_operator is None:
            raise RuntimeError(
                f"Cannot restore participant for RegisteredEntity {entity.pk}: "
                "no operators are set. Add an operator before reversing this "
                "migration."
            )
        entity.participant_id = first_operator.pk
        entity.save(update_fields=["participant"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("registry", "0004_registeredentity_instance_uri_and_more"),
    ]

    operations = [
        # 1. Add the M2M under a temporary related_name so it does not clash
        #    with the participant FK's "registered_entities" accessor while
        #    both fields coexist. (No DB rename cost — M2M related_name is
        #    Python-only.)
        migrations.AddField(
            model_name="registeredentity",
            name="operators",
            field=models.ManyToManyField(
                help_text=_HELP_TEXT,
                related_name="operated_entities_tmp",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # 2. Make participant nullable *before* removing it. This keeps the
        #    rollback path working: the reverse of the RemoveField below then
        #    re-adds participant as nullable, which succeeds on a populated
        #    table (a non-nullable re-add would fail — existing rows have no
        #    value). The reverse of this AlterField restores NOT NULL, after
        #    restore_operator_to_participant has filled every row.
        migrations.AlterField(
            model_name="registeredentity",
            name="participant",
            field=models.ForeignKey(
                null=True,
                on_delete=models.CASCADE,
                related_name="registered_entities",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # 3. Copy existing participant -> operators before dropping the FK.
        #    On reverse this repopulates participant from operators, and must
        #    run after the nullable re-add (step 4 reverse) but before NOT NULL
        #    is restored (step 2 reverse) — hence its position here.
        migrations.RunPython(
            copy_participant_to_operators,
            restore_operator_to_participant,
        ),
        # 4. Drop the now-redundant single-owner FK, freeing up the
        #    "registered_entities" reverse accessor.
        migrations.RemoveField(
            model_name="registeredentity",
            name="participant",
        ),
        # 5. Point operators at the final related_name now the FK is gone.
        migrations.AlterField(
            model_name="registeredentity",
            name="operators",
            field=models.ManyToManyField(
                help_text=_HELP_TEXT,
                related_name="registered_entities",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
