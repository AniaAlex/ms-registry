# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_ca", "0001_initial"),  # django-ca initial migration
        ("certificates", "0002_remove_ct_log_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="entityaccesscertificate",
            name="django_ca_certificate",
            field=models.OneToOneField(
                blank=True,
                help_text="Link to django-ca Certificate for lifecycle management",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="registry_access_certificate",
                to="django_ca.certificate",
            ),
        ),
    ]
