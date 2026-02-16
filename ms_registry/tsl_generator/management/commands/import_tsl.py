"""
Management command to import TSL data from YAML/PEM directory or XML file.
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Import TSL data from a go-trust example-tsl directory structure or ETSI TS 119612 XML file"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            type=str,
            help="Path to TSL directory (with scheme.yaml) or XML file (with --xml flag)",
        )
        parser.add_argument(
            "--xml",
            action="store_true",
            help="Import from ETSI TS 119612 XML file instead of YAML/PEM directory",
        )
        parser.add_argument(
            "--name",
            type=str,
            default=None,
            help="Custom name for the imported scheme",
        )

    def handle(self, *args, **options):
        path = options["path"]
        is_xml = options["xml"]
        scheme_name = options.get("name")

        try:
            if is_xml:
                from tsl_generator.importers import import_tsl_from_xml_file

                self.stdout.write(f"Importing TSL from XML file: {path}")
                scheme = import_tsl_from_xml_file(path, scheme_name)

                provider_count = scheme.providers.count()
                service_count = sum(p.services.count() for p in scheme.providers.all())
                cert_count = sum(
                    s.certificates.count()
                    for p in scheme.providers.all()
                    for s in p.services.all()
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully imported TSL scheme: {scheme.name}\n"
                        f"  - Territory: {scheme.territory}\n"
                        f"  - Sequence Number: {scheme.sequence_number}\n"
                        f"  - Providers: {provider_count}\n"
                        f"  - Services: {service_count}\n"
                        f"  - Certificates: {cert_count}"
                    )
                )
            else:
                from tsl_generator.importers import import_tsl_directory

                self.stdout.write(f"Importing TSL from directory: {path}")
                scheme = import_tsl_directory(path)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully imported TSL scheme: {scheme.name}\n"
                        f"  - Territory: {scheme.territory}\n"
                        f"  - Sequence Number: {scheme.sequence_number}\n"
                        f"  - Providers: {scheme.providers.count()}"
                    )
                )

        except FileNotFoundError as e:
            raise CommandError(f"File not found: {e}")
        except Exception as e:
            raise CommandError(f"Import failed: {e}")
