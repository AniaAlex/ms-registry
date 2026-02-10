# Generated migration for legal_entities app

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LegalPerson",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "legal_name",
                    models.CharField(help_text="Official legal name", max_length=500),
                ),
                (
                    "legal_form",
                    models.CharField(
                        blank=True,
                        help_text="e.g., LLC, GmbH, AB, etc.",
                        max_length=200,
                        null=True,
                    ),
                ),
                (
                    "legal_form_uri",
                    models.URLField(
                        blank=True,
                        help_text="URI to legal form definition",
                        max_length=2048,
                        null=True,
                    ),
                ),
                ("registration_date", models.DateField(blank=True, null=True)),
                (
                    "governing_law",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="legal_persons",
                        to="core.law",
                    ),
                ),
            ],
            options={
                "verbose_name": "Legal Person",
                "verbose_name_plural": "Legal Persons",
                "db_table": "legal_entities_legal_person",
            },
        ),
        migrations.AddIndex(
            model_name="legalperson",
            index=models.Index(fields=["legal_name"], name="legal_enti_legal_na_idx"),
        ),
        migrations.CreateModel(
            name="NaturalPerson",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("given_name", models.CharField(max_length=200)),
                ("family_name", models.CharField(max_length=200)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                (
                    "nationality",
                    models.CharField(
                        blank=True,
                        help_text="ISO 3166-1 alpha-2",
                        max_length=2,
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Natural Person",
                "verbose_name_plural": "Natural Persons",
                "db_table": "legal_entities_natural_person",
            },
        ),
        migrations.CreateModel(
            name="PhysicalAddress",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "street_address",
                    models.CharField(blank=True, max_length=500, null=True),
                ),
                (
                    "locality",
                    models.CharField(
                        blank=True, help_text="City/Town", max_length=200, null=True
                    ),
                ),
                (
                    "region",
                    models.CharField(
                        blank=True,
                        help_text="State/Province",
                        max_length=200,
                        null=True,
                    ),
                ),
                ("postal_code", models.CharField(blank=True, max_length=20, null=True)),
                (
                    "country_code",
                    models.CharField(help_text="ISO 3166-1 alpha-2", max_length=2),
                ),
                (
                    "address_type",
                    models.CharField(
                        default="registered",
                        help_text="registered, operational, etc.",
                        max_length=50,
                    ),
                ),
            ],
            options={
                "verbose_name": "Physical Address",
                "verbose_name_plural": "Physical Addresses",
                "db_table": "legal_entities_physical_address",
            },
        ),
        migrations.CreateModel(
            name="LegalEntity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "entity_type",
                    models.CharField(
                        choices=[
                            ("legal_person", "Legal Person"),
                            ("natural_person", "Natural Person"),
                        ],
                        help_text="Type of legal entity",
                        max_length=20,
                    ),
                ),
                ("email", models.EmailField(blank=True, max_length=320, null=True)),
                ("phone", models.CharField(blank=True, max_length=50, null=True)),
                ("info_uri", models.URLField(blank=True, max_length=2048, null=True)),
                (
                    "legal_person",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="legal_entity",
                        to="legal_entities.legalperson",
                    ),
                ),
                (
                    "natural_person",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="legal_entity",
                        to="legal_entities.naturalperson",
                    ),
                ),
                (
                    "physical_address",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="legal_entities",
                        to="legal_entities.physicaladdress",
                    ),
                ),
                (
                    "primary_identifier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="primary_for_entities",
                        to="core.identifier",
                    ),
                ),
            ],
            options={
                "verbose_name": "Legal Entity",
                "verbose_name_plural": "Legal Entities",
                "db_table": "legal_entities_legal_entity",
            },
        ),
        migrations.AddIndex(
            model_name="legalentity",
            index=models.Index(fields=["entity_type"], name="legal_enti_entity_t_idx"),
        ),
        migrations.CreateModel(
            name="LegalEntityIdentifier",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_primary", models.BooleanField(default=False)),
                (
                    "legal_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_identifiers",
                        to="legal_entities.legalentity",
                    ),
                ),
                (
                    "identifier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_links",
                        to="core.identifier",
                    ),
                ),
            ],
            options={
                "verbose_name": "Legal Entity Identifier",
                "verbose_name_plural": "Legal Entity Identifiers",
                "db_table": "legal_entities_legal_entity_identifier",
                "unique_together": {("legal_entity", "identifier")},
            },
        ),
        migrations.AddField(
            model_name="legalentity",
            name="identifiers",
            field=models.ManyToManyField(
                related_name="legal_entities",
                through="legal_entities.LegalEntityIdentifier",
                to="core.identifier",
            ),
        ),
    ]
