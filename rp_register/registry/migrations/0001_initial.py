# Generated migration for registry app

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0001_initial"),
        ("legal_entities", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupervisoryAuthority",
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
                ("authority_name", models.CharField(max_length=500)),
                (
                    "country_code",
                    models.CharField(help_text="Member State", max_length=2),
                ),
                ("email", models.EmailField(blank=True, max_length=320, null=True)),
                ("phone", models.CharField(blank=True, max_length=50, null=True)),
                ("info_uri", models.URLField(blank=True, max_length=2048, null=True)),
                (
                    "legal_entity",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="supervised_authorities",
                        to="legal_entities.legalentity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Supervisory Authority (DPA)",
                "verbose_name_plural": "Supervisory Authorities (DPAs)",
                "db_table": "registry_supervisory_authority",
            },
        ),
        migrations.AddIndex(
            model_name="supervisoryauthority",
            index=models.Index(fields=["country_code"], name="registry_su_country_idx"),
        ),
        migrations.CreateModel(
            name="RegisteredEntity",
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
                    "entity_role",
                    models.CharField(
                        choices=[
                            ("relying_party", "Relying Party (Verifier)"),
                            ("pid_provider", "PID Provider (Issuer)"),
                            ("attestation_provider", "Attestation Provider (Issuer)"),
                        ],
                        help_text="Primary role: RP (verifier), PID Provider, or Attestation Provider",
                        max_length=30,
                    ),
                ),
                (
                    "trade_name",
                    models.CharField(
                        blank=True,
                        help_text="Common/service name [0..1]",
                        max_length=500,
                        null=True,
                    ),
                ),
                (
                    "is_psb",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates whether the entity is a public sector body (relevant for PuB-EAA Providers)",
                        verbose_name="Is Public Sector Body",
                    ),
                ),
                (
                    "is_intermediary",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates whether the entity acts as an intermediary. Only applicable to Relying Parties.",
                    ),
                ),
                (
                    "registry_uri",
                    models.URLField(
                        help_text="National registry API URI, provided by Registrar (per Reg_03, Reg_04)",
                        max_length=2048,
                    ),
                ),
                (
                    "registration_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("revoked", "Revoked"),
                        ],
                        default="pending",
                        max_length=50,
                    ),
                ),
                ("registered_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.CharField(blank=True, max_length=200, null=True)),
                ("updated_by", models.CharField(blank=True, max_length=200, null=True)),
                (
                    "legal_entity",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registered_entity",
                        to="legal_entities.legalentity",
                    ),
                ),
                (
                    "supervisory_authority",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registered_entities",
                        to="registry.supervisoryauthority",
                    ),
                ),
            ],
            options={
                "verbose_name": "Registered Entity",
                "verbose_name_plural": "Registered Entities",
                "db_table": "registry_registered_entity",
            },
        ),
        migrations.AddIndex(
            model_name="registeredentity",
            index=models.Index(fields=["entity_role"], name="registry_re_entity_r_idx"),
        ),
        migrations.AddIndex(
            model_name="registeredentity",
            index=models.Index(fields=["trade_name"], name="registry_re_trade_n_idx"),
        ),
        migrations.AddIndex(
            model_name="registeredentity",
            index=models.Index(fields=["registry_uri"], name="registry_re_registr_idx"),
        ),
        migrations.AddIndex(
            model_name="registeredentity",
            index=models.Index(fields=["is_psb"], name="registry_re_is_psb_idx"),
        ),
        migrations.AddIndex(
            model_name="registeredentity",
            index=models.Index(
                fields=["is_intermediary"], name="registry_re_is_inte_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="registeredentity",
            index=models.Index(
                fields=["registration_status"], name="registry_re_registr_st_idx"
            ),
        ),
        migrations.CreateModel(
            name="EntitySupportURI",
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
                ("support_uri", models.URLField(max_length=2048)),
                (
                    "support_type",
                    models.CharField(
                        blank=True,
                        help_text="website, email, phone",
                        max_length=100,
                        null=True,
                    ),
                ),
                ("description", models.TextField(blank=True, null=True)),
                ("is_primary", models.BooleanField(default=False)),
                (
                    "registered_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="support_uris",
                        to="registry.registeredentity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Support URI",
                "verbose_name_plural": "Support URIs",
                "db_table": "registry_entity_support_uri",
            },
        ),
        migrations.AddIndex(
            model_name="entitysupporturi",
            index=models.Index(
                fields=["registered_entity"], name="registry_es_reg_ent_idx"
            ),
        ),
        migrations.CreateModel(
            name="EntityEntitlement",
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
                    "entitlement_uri",
                    models.URLField(
                        help_text="EUDI Wallet Entitlement URIs: http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/PID_Issuer, http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/QEAA_Provider, http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/WalletProvider, http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/RelyingParty",
                        max_length=2048,
                    ),
                ),
                (
                    "entitlement_type",
                    models.CharField(
                        choices=[
                            ("Service_Provider", "Service Provider"),
                            ("QEAA_Provider", "Qualified EAA Provider"),
                            ("Non_Q_EAA_Provider", "Non-Qualified EAA Provider"),
                            ("PUB_EAA_Provider", "Public EAA Provider"),
                            ("PID_Provider", "PID Provider"),
                            ("Intermediary", "Intermediary"),
                        ],
                        max_length=50,
                    ),
                ),
                ("granted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "registered_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entitlements",
                        to="registry.registeredentity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entitlement",
                "verbose_name_plural": "Entitlements",
                "db_table": "registry_entity_entitlement",
                "unique_together": {("registered_entity", "entitlement_uri")},
            },
        ),
        migrations.AddIndex(
            model_name="entityentitlement",
            index=models.Index(
                fields=["registered_entity"], name="registry_ee_reg_ent_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="entityentitlement",
            index=models.Index(
                fields=["entitlement_type"], name="registry_ee_ent_typ_idx"
            ),
        ),
        migrations.CreateModel(
            name="EntityServiceDescription",
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
                ("content", models.TextField(help_text="Localized description")),
                (
                    "registered_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_descriptions",
                        to="registry.registeredentity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Service Description",
                "verbose_name_plural": "Service Descriptions",
                "db_table": "registry_entity_service_description",
                "unique_together": {("registered_entity", "lang")},
            },
        ),
        migrations.AddIndex(
            model_name="entityservicedescription",
            index=models.Index(
                fields=["registered_entity"], name="registry_esd_reg_ent_idx"
            ),
        ),
        migrations.CreateModel(
            name="RegisteredEntityPolicy",
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
                        related_name="policy_links",
                        to="registry.registeredentity",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entity_links",
                        to="core.policy",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entity Policy",
                "verbose_name_plural": "Entity Policies",
                "db_table": "registry_entity_policy",
                "unique_together": {("registered_entity", "policy")},
            },
        ),
        migrations.AddField(
            model_name="registeredentity",
            name="policies",
            field=models.ManyToManyField(
                related_name="registered_entities",
                through="registry.RegisteredEntityPolicy",
                to="core.policy",
            ),
        ),
        migrations.CreateModel(
            name="EntityUsesIntermediary",
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
                ("intermediary_identifier", models.CharField(max_length=500)),
                (
                    "intermediary_trade_name",
                    models.CharField(blank=True, max_length=500, null=True),
                ),
                ("intermediary_registry_uri", models.URLField(max_length=2048)),
                (
                    "relationship_start_date",
                    models.DateField(default=django.utils.timezone.now),
                ),
                ("relationship_end_date", models.DateField(blank=True, null=True)),
                (
                    "registered_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="used_intermediaries",
                        to="registry.registeredentity",
                    ),
                ),
                (
                    "intermediary",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="clients_using",
                        to="registry.registeredentity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Uses Intermediary",
                "verbose_name_plural": "Uses Intermediaries",
                "db_table": "registry_entity_uses_intermediary",
                "unique_together": {("registered_entity", "intermediary")},
            },
        ),
        migrations.AddIndex(
            model_name="entityusesintermediary",
            index=models.Index(
                fields=["registered_entity"], name="registry_eui_reg_ent_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="entityusesintermediary",
            index=models.Index(fields=["intermediary"], name="registry_eui_interm_idx"),
        ),
    ]
