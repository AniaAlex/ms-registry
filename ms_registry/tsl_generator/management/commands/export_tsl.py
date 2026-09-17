"""
Management command to export TSL data to XML file.
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Export TSL scheme to ETSI TS 119612 compliant XML file"

    def add_arguments(self, parser):
        parser.add_argument(
            "scheme_id",
            type=int,
            help="ID of the TSL scheme to export",
        )
        parser.add_argument(
            "output_path",
            type=str,
            help="Output file path for the XML",
        )

    def handle(self, *args, **options):
        from tsl_generator.models import TSLScheme

        scheme_id = options["scheme_id"]
        output_path = options["output_path"]

        try:
            scheme = TSLScheme.objects.get(pk=scheme_id)
        except TSLScheme.DoesNotExist:
            raise CommandError(f"TSL Scheme with ID {scheme_id} does not exist")

        try:
            filepath = scheme.export_to_file(output_path)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully exported TSL scheme to: {filepath}\n"
                    f"  - Scheme: {scheme.name}\n"
                    f"  - Territory: {scheme.territory}\n"
                    f"  - Sequence Number: {scheme.sequence_number}"
                )
            )

        except Exception as e:
            raise CommandError(f"Export failed: {e}")
