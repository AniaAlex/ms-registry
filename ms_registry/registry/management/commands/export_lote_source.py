"""
Management command to export registered entities as a LoTE source directory.

Reads active RegisteredEntity records from PostgreSQL and writes:
  <output_dir>/
    scheme.yaml
    entities/
      <entity-slug>/
        entity.yaml
        access-cert.pem   (if entity has a current access certificate)

The output directory can be consumed directly by tsl-tool generate-lote.
"""

import os
import re

import yaml
from django.core.management.base import BaseCommand
from django.utils import timezone

# RegistrationStatus → LoTE entity/service status URI
STATUS_URI = {
    "active": "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted",
    "suspended": "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/suspended",
    "revoked": "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/revoked",
}

# EntitlementType → LoTE serviceType URI
SERVICE_TYPE_URI = {
    "PID_Provider": "http://uri.etsi.org/TrstSvc/Svctype/EAA/PID",
    "QEAA_Provider": "http://uri.etsi.org/TrstSvc/Svctype/EAA/QEAA",
    "Non_Q_EAA_Provider": "http://uri.etsi.org/TrstSvc/Svctype/EAA/NonQEAA",
    "PUB_EAA_Provider": "http://uri.etsi.org/TrstSvc/Svctype/EAA/PubEAA",
    "Service_Provider": "http://uri.etsi.org/TrstSvc/Svctype/RelyingParty",
    "QCert_for_ESig_Provider": "http://uri.etsi.org/TrstSvc/Svctype/CA/QC",
    "QCert_for_ESeal_Provider": "http://uri.etsi.org/TrstSvc/Svctype/CA/QCSeal",
    "rQSigCDs_Provider": "http://uri.etsi.org/TrstSvc/Svctype/QSCCD",
    "rQSealCDs_Provider": "http://uri.etsi.org/TrstSvc/Svctype/QSCCD",
    "ESig_ESeal_Creation_Provider": "http://uri.etsi.org/TrstSvc/Svctype/QSCCD",
    "Intermediary": "http://uri.etsi.org/TrstSvc/Svctype/Intermediary",
}

# EntityRole → LoTE entityType
ENTITY_TYPE = {
    "relying_party": "relying-party",
    "pid_provider": "pid-provider",
    "attestation_provider": "attestation-provider",
}


def slugify(value):
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    return re.sub(r"-+", "-", value)


def entitlement_status(entitlement):
    if not entitlement.is_active:
        return STATUS_URI["revoked"]
    if entitlement.expires_at and entitlement.expires_at < timezone.now():
        return STATUS_URI["revoked"]
    return STATUS_URI["active"]


class Command(BaseCommand):
    help = "Export active registered entities as a tsl-tool LoTE source directory"

    def add_arguments(self, parser):
        parser.add_argument(
            "output_dir",
            help="Directory to write scheme.yaml + entities/ into",
        )
        parser.add_argument(
            "--operator-name",
            default="WE BUILD WP4 Trust Group",
            help="Scheme operator name (default: WE BUILD WP4 Trust Group)",
        )
        parser.add_argument(
            "--scheme-name",
            default="WP4 List of Trusted Entities",
            help="Scheme name (default: WP4 List of Trusted Entities)",
        )
        parser.add_argument(
            "--territory",
            default="SE",
            help="Territory code (default: SE)",
        )
        parser.add_argument(
            "--sequence-number",
            type=int,
            default=1,
            help="Sequence number (default: 1)",
        )
        parser.add_argument(
            "--include-pending",
            action="store_true",
            help="Also include entities with pending status",
        )

    def handle(self, *args, **options):
        from registry.models import RegisteredEntity

        output_dir = options["output_dir"]
        entities_dir = os.path.join(output_dir, "entities")
        os.makedirs(entities_dir, exist_ok=True)

        # --- scheme.yaml ---
        scheme = {
            "operatorNames": [{"language": "en", "value": options["operator_name"]}],
            "schemeName": [{"language": "en", "value": options["scheme_name"]}],
            "schemeType": "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric",
            "territory": options["territory"],
            "sequenceNumber": options["sequence_number"],
        }
        scheme_path = os.path.join(output_dir, "scheme.yaml")
        with open(scheme_path, "w") as f:
            yaml.dump(scheme, f, default_flow_style=False, allow_unicode=True)
        self.stdout.write(f"  wrote {scheme_path}")

        # --- entities ---
        statuses = ["active"]
        if options["include_pending"]:
            statuses.append("pending")

        entities = (
            RegisteredEntity.objects.filter(registration_status__in=statuses)
            .select_related(
                "legal_entity__legal_person", "legal_entity__natural_person"
            )
            .prefetch_related(
                "entitlements",
                "service_descriptions",
                "access_certificates",
            )
        )

        count = 0
        for entity in entities:
            self._export_entity(entities_dir, entity, options["territory"])
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Exported {count} entities to {output_dir}")
        )

    def _export_entity(self, entities_dir, entity, territory):
        name = entity.display_name
        slug = slugify(name)
        entity_dir = os.path.join(entities_dir, slug)
        os.makedirs(entity_dir, exist_ok=True)

        status_uri = STATUS_URI.get(
            entity.registration_status,
            STATUS_URI["active"],
        )

        # Build services from entitlements
        services = []
        for ent in entity.entitlements.all():
            svc_type = SERVICE_TYPE_URI.get(ent.entitlement_type)
            if not svc_type:
                continue
            svc_names = [
                {"language": "en", "value": ent.get_entitlement_type_display()}
            ]
            services.append(
                {
                    "serviceType": svc_type,
                    "serviceNames": svc_names,
                    "status": entitlement_status(ent),
                }
            )

        # Build multilingual names from service_descriptions or fallback to display_name
        descriptions = list(entity.service_descriptions.all())
        if descriptions:
            names = [{"language": d.lang, "value": d.content} for d in descriptions]
        else:
            names = [{"language": "en", "value": name}]

        entity_data = {
            "entityId": entity.registry_uri,
            "names": names,
            "status": status_uri,
            "entityType": ENTITY_TYPE.get(entity.entity_role, entity.entity_role),
            "services": services,
        }

        entity_path = os.path.join(entity_dir, "entity.yaml")
        with open(entity_path, "w") as f:
            yaml.dump(entity_data, f, default_flow_style=False, allow_unicode=True)
        self.stdout.write(f"  wrote {entity_path}")

        # Write current access certificate if present
        current_cert = entity.access_certificates.filter(
            is_current=True, certificate_pem__isnull=False
        ).first()
        if current_cert:
            cert_path = os.path.join(entity_dir, "access-cert.pem")
            with open(cert_path, "w") as f:
                f.write(current_cert.certificate_pem)
            self.stdout.write(f"  wrote {cert_path}")
