from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0002_alter_entityentitlement_entitlement_type_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="registeredentity",
            name="registry_uri",
            field=models.URLField(
                blank=True,
                max_length=2048,
                help_text="National registry API URI, auto-generated on creation (per Reg_03, Reg_04)",
            ),
        ),
    ]
