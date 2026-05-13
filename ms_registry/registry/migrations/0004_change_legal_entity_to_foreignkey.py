# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("legal_entities", "0001_initial"),
        ("registry", "0003_registeredentity_registry_uri_blank"),
    ]

    operations = [
        migrations.AlterField(
            model_name="registeredentity",
            name="legal_entity",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="registered_entities",
                to="legal_entities.legalentity",
            ),
        ),
    ]
