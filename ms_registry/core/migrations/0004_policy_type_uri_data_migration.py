from django.db import migrations


def migrate_policy_type_forward(apps, schema_editor):
    Policy = apps.get_model("core", "Policy")
    Policy.objects.filter(policy_type="Privacy_Statement").update(
        policy_type="http://data.europa.eu/eudi/policy/privacy-policy"
    )


def migrate_policy_type_backward(apps, schema_editor):
    Policy = apps.get_model("core", "Policy")
    Policy.objects.filter(
        policy_type="http://data.europa.eu/eudi/policy/privacy-policy"
    ).update(policy_type="Privacy_Statement")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_policy_type_uri"),
    ]

    operations = [
        migrations.RunPython(
            migrate_policy_type_forward,
            reverse_code=migrate_policy_type_backward,
        ),
    ]
