# Generated migration for certificates app

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("registry", "0001_initial"),
        ("credentials", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EntityAccessCertificate",
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
                ("certificate_serial", models.CharField(max_length=100)),
                (
                    "certificate_fingerprint_sha256",
                    models.CharField(blank=True, max_length=64, null=True),
                ),
                ("issuer_dn", models.CharField(blank=True, max_length=500, null=True)),
                ("subject_dn", models.CharField(blank=True, max_length=500, null=True)),
                ("not_before", models.DateTimeField()),
                ("not_after", models.DateTimeField()),
                ("ct_log_id", models.CharField(blank=True, max_length=200, null=True)),
                ("ct_log_timestamp", models.DateTimeField(blank=True, null=True)),
                (
                    "ct_sct",
                    models.BinaryField(
                        blank=True, help_text="Signed Certificate Timestamp", null=True
                    ),
                ),
                ("is_current", models.BooleanField(default=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "revocation_reason",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("certificate_pem", models.TextField(blank=True, null=True)),
                (
                    "registered_entity",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_certificates",
                        to="registry.registeredentity",
                    ),
                ),
            ],
            options={
                "verbose_name": "Access Certificate",
                "verbose_name_plural": "Access Certificates",
                "db_table": "certificates_entity_access_certificate",
            },
        ),
        migrations.AddIndex(
            model_name="entityaccesscertificate",
            index=models.Index(
                fields=["registered_entity"], name="certs_eac_reg_ent_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="entityaccesscertificate",
            index=models.Index(fields=["is_current"], name="certs_eac_is_curr_idx"),
        ),
        migrations.AddIndex(
            model_name="entityaccesscertificate",
            index=models.Index(
                fields=["not_before", "not_after"], name="certs_eac_validity_idx"
            ),
        ),
        migrations.CreateModel(
            name="EntityRegistrationCertificate",
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
                ("certificate_identifier", models.CharField(max_length=500)),
                (
                    "certificate_serial",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("issuer_dn", models.CharField(blank=True, max_length=500, null=True)),
                ("subject_dn", models.CharField(blank=True, max_length=500, null=True)),
                ("issued_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "revocation_reason",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("certificate_pem", models.TextField(blank=True, null=True)),
                (
                    "intended_use",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registration_certificate",
                        to="credentials.intendeduse",
                    ),
                ),
            ],
            options={
                "verbose_name": "Registration Certificate",
                "verbose_name_plural": "Registration Certificates",
                "db_table": "certificates_entity_registration_certificate",
            },
        ),
        migrations.AddIndex(
            model_name="entityregistrationcertificate",
            index=models.Index(fields=["intended_use"], name="certs_erc_iu_idx"),
        ),
        migrations.AddIndex(
            model_name="entityregistrationcertificate",
            index=models.Index(
                fields=["certificate_identifier"], name="certs_erc_cert_id_idx"
            ),
        ),
        migrations.CreateModel(
            name="AuditLog",
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
                ("table_name", models.CharField(max_length=100)),
                ("record_id", models.UUIDField()),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("INSERT", "Insert"),
                            ("UPDATE", "Update"),
                            ("DELETE", "Delete"),
                        ],
                        max_length=20,
                    ),
                ),
                ("old_values", models.JSONField(blank=True, null=True)),
                ("new_values", models.JSONField(blank=True, null=True)),
                ("changed_by", models.CharField(blank=True, max_length=200, null=True)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Audit Log",
                "verbose_name_plural": "Audit Logs",
                "db_table": "certificates_audit_log",
            },
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["table_name"], name="certs_al_table_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["record_id"], name="certs_al_record_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["changed_at"], name="certs_al_changed_idx"),
        ),
    ]
