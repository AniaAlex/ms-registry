from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("certificates", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="entityaccesscertificate",
            name="ct_log_id",
        ),
        migrations.RemoveField(
            model_name="entityaccesscertificate",
            name="ct_log_timestamp",
        ),
        migrations.RemoveField(
            model_name="entityaccesscertificate",
            name="ct_sct",
        ),
    ]
