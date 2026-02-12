# Generated migration for credentials app

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0001_initial"),
        ("registry", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Credential",
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
                    "format",
                    models.CharField(
                        choices=[
                            ("sd-jwt-vc", "SD-JWT Verifiable Credential"),
                            ("dc+sd-jwt", "Digital Credential SD-JWT"),
                            ("mso_mdoc", "ISO mDL / mdoc Format"),
                            ("jwt_vc_json", "JWT VC JSON"),
                            ("ldp_vc", "JSON-LD VC with Data Integrity"),
                        ],
                        help_text="Attestation format",
                        max_length=50,
                    ),
                ),
                (
                    "meta",
                    models.JSONField(
                        help_text="Format-specific metadata per OpenID4VP Section 6.1"
                    ),
                ),
                (
                    "catalogue_schema_uri",
                    models.URLField(
                        blank=True,
                        help_text="Reference to attestation catalogue",
                        max_length=2048,
                        null=True,
                    ),
                ),
                (
                    "attestation_rulebook_uri",
                    models.URLField(
                        blank=True,
                        help_text="URI to Attestation Rulebook",
                        max_length=2048,
                        null=True,
                    ),
                ),
                (
                    "attestation_type",
                    models.CharField(
                        blank=True,
                        help_text="Self-declared attestation type (if not in catalogue)",
                        max_length=500,
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Credential",
                "verbose_name_plural": "Credentials",
                "db_table": "credentials_credential",
            },
        ),
        migrations.AddIndex(
            model_name="credential",
            index=models.Index(fields=["format"], name="credentials_format_idx"),
        ),
        migrations.CreateModel(
            name="Claim",
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
                    "path",
                    models.JSONField(
                        help_text="JSON path pointer to claim within credential per OpenID4VP Section 6.3"
                    ),
                ),
                (
                    "values",
                    models.JSONField(
                        blank=True,
                        help_text="Optional expected values for matching",
                        null=True,
                    ),
                ),
                (
                    "credential",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="claims",
                        to="credentials.credential",
                    ),
                ),
            ],
            options={
                "verbose_name": "Claim",
                "verbose_name_plural": "Claims",
                "db_table": "credentials_claim",
            },
        ),
        migrations.AddIndex(
            model_name="claim",
            index=models.Index(
                fields=["credential"], name="credentials_claim_cred_idx"
            ),
        ),
        migrations.CreateModel(
            name="IntendedUse",
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
                    "intended_use_identifier",
                    models.CharField(
                        help_text="Registrar-provided unique identifier, may match Registration Certificate ID",
                        max_length=500,
                        unique=True,
                    ),
                ),
                ("validity_start", models.DateField(help_text="Validity start date")),
                (
                    "validity_end",
                    models.DateField(
                        blank=True,
                        help_text="End date for validity (revoked or expired)",
                        null=True,
                    ),
                ),
                (
                    "registered_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="intended_uses",
                        to="registry.registeredentity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Intended Use",
                "verbose_name_plural": "Intended Uses",
                "db_table": "credentials_intended_use",
            },
        ),
        migrations.AddIndex(
            model_name="intendeduse",
            index=models.Index(
                fields=["registered_entity"], name="credentials_iu_reg_ent_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="intendeduse",
            index=models.Index(
                fields=["intended_use_identifier"], name="credentials_iu_ident_idx"
            ),
        ),
        migrations.CreateModel(
            name="IntendedUsePurpose",
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
                    "lang",
                    models.CharField(
                        help_text="Language code per ETSI TS 119 612 Annex E",
                        max_length=5,
                    ),
                ),
                (
                    "content",
                    models.TextField(help_text="Localized purpose description"),
                ),
                (
                    "intended_use",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="purposes",
                        to="credentials.intendeduse",
                    ),
                ),
            ],
            options={
                "verbose_name": "Intended Use Purpose",
                "verbose_name_plural": "Intended Use Purposes",
                "db_table": "credentials_intended_use_purpose",
                "unique_together": {("intended_use", "lang")},
            },
        ),
        migrations.AddIndex(
            model_name="intendedusepurpose",
            index=models.Index(fields=["intended_use"], name="credentials_iup_iu_idx"),
        ),
        migrations.CreateModel(
            name="IntendedUsePrivacyPolicy",
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
                    "locale",
                    models.CharField(
                        blank=True,
                        help_text="Language/locale for this policy version",
                        max_length=5,
                        null=True,
                    ),
                ),
                ("is_primary", models.BooleanField(default=False)),
                (
                    "intended_use",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="privacy_policies",
                        to="credentials.intendeduse",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="intended_use_links",
                        to="core.policy",
                    ),
                ),
            ],
            options={
                "verbose_name": "Intended Use Privacy Policy",
                "verbose_name_plural": "Intended Use Privacy Policies",
                "db_table": "credentials_intended_use_privacy_policy",
                "unique_together": {("intended_use", "policy")},
            },
        ),
        migrations.AddIndex(
            model_name="intendeduseprivacypolicy",
            index=models.Index(fields=["intended_use"], name="credentials_iupp_iu_idx"),
        ),
        migrations.CreateModel(
            name="IntendedUseCredential",
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
                    "is_mandatory",
                    models.BooleanField(
                        default=False, help_text="Whether this credential is required"
                    ),
                ),
                (
                    "request_order",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Order in presentation request",
                        null=True,
                    ),
                ),
                (
                    "intended_use",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="credential_links",
                        to="credentials.intendeduse",
                    ),
                ),
                (
                    "credential",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="intended_use_links",
                        to="credentials.credential",
                    ),
                ),
            ],
            options={
                "verbose_name": "Intended Use Credential",
                "verbose_name_plural": "Intended Use Credentials",
                "db_table": "credentials_intended_use_credential",
                "unique_together": {("intended_use", "credential")},
            },
        ),
        migrations.AddIndex(
            model_name="intendedusecredential",
            index=models.Index(fields=["intended_use"], name="credentials_iuc_iu_idx"),
        ),
        migrations.AddField(
            model_name="intendeduse",
            name="credentials",
            field=models.ManyToManyField(
                related_name="intended_uses",
                through="credentials.IntendedUseCredential",
                to="credentials.credential",
            ),
        ),
        migrations.CreateModel(
            name="EntityProvidesAttestation",
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
                    "registered_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provided_attestations",
                        to="registry.registeredentity",
                    ),
                ),
                (
                    "credential",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provided_by",
                        to="credentials.credential",
                    ),
                ),
            ],
            options={
                "verbose_name": "Provided Attestation",
                "verbose_name_plural": "Provided Attestations",
                "db_table": "credentials_entity_provides_attestation",
                "unique_together": {("registered_entity", "credential")},
            },
        ),
        migrations.AddIndex(
            model_name="entityprovidesattestation",
            index=models.Index(
                fields=["registered_entity"], name="credentials_epa_reg_ent_idx"
            ),
        ),
    ]
