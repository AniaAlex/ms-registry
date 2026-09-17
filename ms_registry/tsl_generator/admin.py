"""
Django Admin configuration for TSL Generator models.
"""

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from .models import (
    AdditionalServiceInformation,
    ServiceCertificate,
    ServiceDefinitionURI,
    ServiceHistoryAdditionalInfo,
    ServiceHistoryDigitalId,
    ServiceHistoryInstance,
    ServiceHistoryName,
    ServiceHistoryQualification,
    ServiceName,
    ServiceQualification,
    ServiceSupplyPoint,
    TrustService,
    TrustServiceProvider,
    TSLPointer,
    TSLPointerCertificate,
    TSLPointerOperatorName,
    TSLPolicyOrLegalNotice,
    TSLScheme,
    TSLSchemeCommunityRule,
    TSLSchemeInformationURI,
    TSLSchemeName,
    TSLSchemeOperatorName,
    TSPCertificate,
    TSPElectronicAddress,
    TSPInformationURI,
    TSPName,
    TSPTradeName,
)


# =============================================================================
# Inline Admin Classes
# =============================================================================
class TSLSchemeOperatorNameInline(admin.TabularInline):
    model = TSLSchemeOperatorName
    extra = 1


class TSLSchemeNameInline(admin.TabularInline):
    model = TSLSchemeName
    extra = 1


class TSLSchemeInformationURIInline(admin.TabularInline):
    model = TSLSchemeInformationURI
    extra = 1


class TSLSchemeCommunityRuleInline(admin.TabularInline):
    model = TSLSchemeCommunityRule
    extra = 1


class TSLPolicyOrLegalNoticeInline(admin.TabularInline):
    model = TSLPolicyOrLegalNotice
    extra = 1


class TSLPointerInline(admin.TabularInline):
    model = TSLPointer
    extra = 0
    show_change_link = True


class TSLPointerOperatorNameInline(admin.TabularInline):
    model = TSLPointerOperatorName
    extra = 1


class TSLPointerCertificateInline(admin.TabularInline):
    model = TSLPointerCertificate
    extra = 0


class TSPNameInline(admin.TabularInline):
    model = TSPName
    extra = 1


class TSPTradeNameInline(admin.TabularInline):
    model = TSPTradeName
    extra = 0


class TSPElectronicAddressInline(admin.TabularInline):
    model = TSPElectronicAddress
    extra = 1


class TSPInformationURIInline(admin.TabularInline):
    model = TSPInformationURI
    extra = 0


class TSPCertificateInline(admin.StackedInline):
    model = TSPCertificate
    extra = 0
    fields = [
        "certificate_pem",
        "certificate_type",
        "subject_cn",
        "subject_dn",
        "issuer_cn",
        "issuer_dn",
        "serial_number",
        "fingerprint_sha256",
        "not_before",
        "not_after",
        "key_usage",
        "extended_key_usage",
        "is_active",
    ]
    readonly_fields = [
        "subject_cn",
        "subject_dn",
        "issuer_cn",
        "issuer_dn",
        "serial_number",
        "fingerprint_sha256",
        "not_before",
        "not_after",
        "key_usage",
        "extended_key_usage",
    ]


class TrustServiceInline(admin.TabularInline):
    model = TrustService
    extra = 0
    show_change_link = True
    fields = ["service_type", "status", "status_starting_time", "is_active"]


class ServiceNameInline(admin.TabularInline):
    model = ServiceName
    extra = 1


class ServiceCertificateInline(admin.StackedInline):
    model = ServiceCertificate
    extra = 0
    fields = [
        "certificate_pem",
        "x509_subject_name",
        "x509_ski",
        "subject_cn",
        "issuer_cn",
        "serial_number",
        "not_before",
        "not_after",
    ]
    readonly_fields = [
        "x509_subject_name",
        "x509_ski",
        "subject_cn",
        "issuer_cn",
        "serial_number",
        "not_before",
        "not_after",
    ]


class ServiceSupplyPointInline(admin.TabularInline):
    model = ServiceSupplyPoint
    extra = 0


class ServiceDefinitionURIInline(admin.TabularInline):
    model = ServiceDefinitionURI
    extra = 0


class ServiceHistoryInstanceInline(admin.TabularInline):
    model = ServiceHistoryInstance
    extra = 0
    show_change_link = True
    fields = ["service_type", "status", "status_starting_time"]


class ServiceHistoryNameInline(admin.TabularInline):
    model = ServiceHistoryName
    extra = 1


class ServiceHistoryDigitalIdInline(admin.TabularInline):
    """Inline for Service History Digital IDs (X509SubjectName, X509SKI)."""

    model = ServiceHistoryDigitalId
    extra = 0
    fields = ["x509_subject_name", "x509_ski"]


class ServiceHistoryQualificationInline(admin.StackedInline):
    """Inline for Service History Qualifications."""

    model = ServiceHistoryQualification
    extra = 0
    fieldsets = (
        (None, {"fields": ("qualifier_uri", "criteria_assert")}),
        (
            "Key Usage Criteria",
            {
                "fields": (
                    "key_usage",
                    ("key_usage_digital_signature", "key_usage_non_repudiation"),
                    ("key_usage_key_encipherment", "key_usage_data_encipherment"),
                    ("key_usage_key_agreement", "key_usage_key_cert_sign"),
                    (
                        "key_usage_crl_sign",
                        "key_usage_encipher_only",
                        "key_usage_decipher_only",
                    ),
                ),
                "classes": ("collapse",),
            },
        ),
    )


class ServiceHistoryAdditionalInfoInline(admin.TabularInline):
    """Inline for Service History Additional Information."""

    model = ServiceHistoryAdditionalInfo
    extra = 0
    fields = ["uri", "language", "critical"]


class ServiceQualificationInline(admin.StackedInline):
    """Inline for Service Qualifications (ns5:Qualifications)."""

    model = ServiceQualification
    extra = 0
    fieldsets = (
        (None, {"fields": ("qualifier_uri", "criteria_assert")}),
        (
            "Key Usage Criteria",
            {
                "fields": (
                    "key_usage",
                    ("key_usage_digital_signature", "key_usage_non_repudiation"),
                    ("key_usage_key_encipherment", "key_usage_data_encipherment"),
                    ("key_usage_key_agreement", "key_usage_key_cert_sign"),
                    (
                        "key_usage_crl_sign",
                        "key_usage_encipher_only",
                        "key_usage_decipher_only",
                    ),
                ),
                "classes": ("collapse",),
            },
        ),
    )


class AdditionalServiceInformationInline(admin.TabularInline):
    """Inline for Additional Service Information extensions."""

    model = AdditionalServiceInformation
    extra = 0
    fields = ["uri", "language", "critical"]


class TrustServiceProviderInline(admin.TabularInline):
    """Inline to show Trust Service Providers aligned to a TSL Scheme."""

    model = TrustServiceProvider
    extra = 0
    show_change_link = True
    fields = ["get_name", "legal_entity", "is_active", "service_count"]
    readonly_fields = ["get_name", "service_count"]
    autocomplete_fields = ["legal_entity"]

    def get_name(self, obj):
        """Get the primary name of the provider."""
        primary_name = obj.names.first()
        return primary_name.value if primary_name else f"TSP #{obj.pk}"

    get_name.short_description = "Provider Name"

    def service_count(self, obj):
        """Count active services for this provider."""
        return obj.services.filter(is_active=True).count()

    service_count.short_description = "Active Services"


# =============================================================================
# Admin Classes
# =============================================================================
@admin.register(TSLScheme)
class TSLSchemeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "territory",
        "sequence_number",
        "tsl_type",
        "provider_count",
        "issue_date",
        "is_active",
        "generate_xml_link",
    ]
    list_filter = ["territory", "is_active", "tsl_type"]
    search_fields = ["name", "territory"]
    ordering = ["-created_at"]

    change_list_template = "admin/tsl_generator/tslscheme/change_list.html"

    def provider_count(self, obj):
        """Count active providers aligned to this scheme."""
        return obj.providers.filter(is_active=True).count()

    provider_count.short_description = "Providers"

    def generate_xml_link(self, obj):
        """Generate XML download link for list view."""
        from django.urls import reverse
        from django.utils.html import format_html

        url = reverse("admin:tsl_generator_tslscheme_generate_xml", args=[obj.pk])
        return format_html(
            '<a href="{}" class="button" style="padding: 3px 10px; '
            "background: #417223; color: white; text-decoration: none; "
            'border-radius: 4px;">Generate XML</a>',
            url,
        )

    generate_xml_link.short_description = "Generate"
    generate_xml_link.allow_tags = True

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "tsl_id",
                    "version",
                    "tsl_type",
                    "sequence_number",
                    "territory",
                )
            },
        ),
        ("Timestamps", {"fields": ("issue_date", "next_update")}),
        (
            "Configuration",
            {
                "fields": (
                    "distribution_points",
                    "historical_information_period",
                    "status_determination_approach",
                )
            },
        ),
        ("Status", {"fields": ("is_active",)}),
    )

    inlines = [
        TSLSchemeOperatorNameInline,
        TSLSchemeNameInline,
        TSLSchemeInformationURIInline,
        TSLSchemeCommunityRuleInline,
        TSLPolicyOrLegalNoticeInline,
        TSLPointerInline,
        TrustServiceProviderInline,
    ]

    actions = ["export_to_xml"]

    @admin.action(description="Export selected schemes to XML")
    def export_to_xml(self, request, queryset):
        from django.http import HttpResponse

        if queryset.count() == 1:
            scheme = queryset.first()
            xml_content = scheme.to_xml_etsi()
            response = HttpResponse(xml_content, content_type="application/xml")
            response["Content-Disposition"] = (
                f'attachment; filename="{scheme.territory}-TSL-'
                f'{scheme.sequence_number}.xml"'
            )
            return response
        else:
            self.message_user(
                request,
                "Please select only one scheme to export.",
                level="warning",
            )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-xml/",
                self.admin_site.admin_view(self.import_xml_view),
                name="tsl_generator_tslscheme_import_xml",
            ),
            path(
                "<int:pk>/generate-xml/",
                self.admin_site.admin_view(self.generate_xml_view),
                name="tsl_generator_tslscheme_generate_xml",
            ),
        ]
        return custom_urls + urls

    def generate_xml_view(self, request, pk):
        """Generate and export TSL XML in full ETSI TS 119612 format."""
        from django.http import HttpResponse
        from django.shortcuts import get_object_or_404

        scheme = get_object_or_404(TSLScheme, pk=pk)
        xml_content = scheme.to_xml_etsi()

        response = HttpResponse(xml_content, content_type="application/xml")
        response["Content-Disposition"] = (
            f'attachment; filename="{scheme.territory}-TL.xml"'
        )
        return response

    def import_xml_view(self, request):
        """Handle TSL XML import via admin interface."""
        if request.method == "POST":
            xml_file = request.FILES.get("xml_file")
            scheme_name = request.POST.get("scheme_name", "").strip()

            if not xml_file:
                messages.error(request, "Please select an XML file to upload.")
                return HttpResponseRedirect(request.path)

            try:
                xml_content = xml_file.read().decode("utf-8")

                from .importers import import_tsl_from_xml

                scheme = import_tsl_from_xml(xml_content, scheme_name or None)

                provider_count = scheme.providers.count()
                service_count = sum(p.services.count() for p in scheme.providers.all())
                cert_count = sum(
                    s.certificates.count()
                    for p in scheme.providers.all()
                    for s in p.services.all()
                )

                messages.success(
                    request,
                    f"Successfully imported TSL '{scheme.name}' with "
                    f"{provider_count} providers, {service_count} services, "
                    f"and {cert_count} certificates.",
                )

                return HttpResponseRedirect(
                    reverse("admin:tsl_generator_tslscheme_change", args=[scheme.pk])
                )

            except Exception as e:
                messages.error(request, f"Failed to import TSL: {str(e)}")
                return HttpResponseRedirect(request.path)

        # GET request - show the upload form
        context = {
            **self.admin_site.each_context(request),
            "title": "Import TSL from XML",
            "opts": self.model._meta,
        }
        return render(request, "admin/tsl_generator/tslscheme/import_xml.html", context)


@admin.register(TSLPointer)
class TSLPointerAdmin(admin.ModelAdmin):
    list_display = ["scheme", "scheme_territory", "tsl_location", "tsl_type"]
    list_filter = ["scheme_territory", "tsl_type"]
    search_fields = ["tsl_location", "scheme_territory"]

    inlines = [TSLPointerOperatorNameInline, TSLPointerCertificateInline]


@admin.register(TrustServiceProvider)
class TrustServiceProviderAdmin(admin.ModelAdmin):
    list_display = ["__str__", "scheme", "legal_entity", "get_country", "is_active"]
    list_filter = [
        "scheme",
        "is_active",
        "legal_entity__physical_address__country_code",
    ]
    search_fields = [
        "names__value",
        "legal_entity__legal_person__legal_name",
        "legal_entity__natural_person__family_name",
    ]
    autocomplete_fields = ["legal_entity"]

    fieldsets = (
        ("Scheme", {"fields": ("scheme",)}),
        (
            "Organization",
            {
                "fields": ("legal_entity",),
                "description": (
                    "Select the legal entity. Address and contact info "
                    "come from the Legal Entity."
                ),
            },
        ),
        ("Status", {"fields": ("is_active",)}),
    )

    inlines = [
        TSPNameInline,
        TSPTradeNameInline,
        TSPElectronicAddressInline,
        TSPInformationURIInline,
        TSPCertificateInline,
        TrustServiceInline,
    ]

    def get_country(self, obj):
        """Get country from legal entity's physical address."""
        return obj.country_name

    get_country.short_description = "Country"


@admin.register(TrustService)
class TrustServiceAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "provider",
        "service_type",
        "status",
        "status_starting_time",
        "is_active",
    ]
    list_filter = ["service_type", "status", "is_active", "provider__scheme"]
    search_fields = ["names__value", "provider__names__value"]
    date_hierarchy = "status_starting_time"

    fieldsets = (
        ("Provider", {"fields": ("provider",)}),
        (
            "Service Information",
            {"fields": ("service_type", "status", "status_starting_time")},
        ),
        ("Status", {"fields": ("is_active",)}),
    )

    inlines = [
        ServiceNameInline,
        ServiceCertificateInline,
        ServiceQualificationInline,
        AdditionalServiceInformationInline,
        ServiceSupplyPointInline,
        ServiceDefinitionURIInline,
        ServiceHistoryInstanceInline,
    ]


@admin.register(ServiceCertificate)
class ServiceCertificateAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "service",
        "subject_cn",
        "issuer_cn",
        "not_before",
        "not_after",
    ]
    list_filter = ["service__provider__scheme"]
    search_fields = ["subject_cn", "issuer_cn", "serial_number", "x509_subject_name"]

    fieldsets = (
        ("Service", {"fields": ("service",)}),
        ("Certificate Data", {"fields": ("certificate_pem",)}),
        (
            "X.509 Digital Identity",
            {"fields": ("x509_subject_name", "x509_ski")},
        ),
        (
            "Certificate Metadata",
            {
                "fields": (
                    "subject_cn",
                    "issuer_cn",
                    "serial_number",
                    "not_before",
                    "not_after",
                )
            },
        ),
    )

    readonly_fields = [
        "x509_subject_name",
        "x509_ski",
        "subject_cn",
        "issuer_cn",
        "serial_number",
        "not_before",
        "not_after",
    ]


@admin.register(ServiceHistoryInstance)
class ServiceHistoryInstanceAdmin(admin.ModelAdmin):
    list_display = ["service", "service_type", "status", "status_starting_time"]
    list_filter = ["service_type", "status"]
    date_hierarchy = "status_starting_time"

    inlines = [
        ServiceHistoryNameInline,
        ServiceHistoryDigitalIdInline,
        ServiceHistoryQualificationInline,
        ServiceHistoryAdditionalInfoInline,
    ]


@admin.register(TSPCertificate)
class TSPCertificateAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "provider",
        "certificate_type",
        "subject_cn",
        "not_before",
        "not_after",
        "is_valid_display",
        "is_active",
    ]
    list_filter = ["certificate_type", "is_active", "provider__scheme"]
    search_fields = [
        "subject_cn",
        "subject_dn",
        "issuer_cn",
        "serial_number",
        "fingerprint_sha256",
    ]
    date_hierarchy = "not_after"

    fieldsets = (
        ("Provider", {"fields": ("provider",)}),
        ("Certificate Data", {"fields": ("certificate_pem", "certificate_type")}),
        (
            "Subject Information",
            {"fields": ("subject_cn", "subject_dn")},
        ),
        (
            "Issuer Information",
            {"fields": ("issuer_cn", "issuer_dn")},
        ),
        (
            "Certificate Details",
            {
                "fields": (
                    "serial_number",
                    "fingerprint_sha256",
                    "not_before",
                    "not_after",
                )
            },
        ),
        (
            "Key Usage",
            {"fields": ("key_usage", "extended_key_usage"), "classes": ("collapse",)},
        ),
        ("Status", {"fields": ("is_active",)}),
    )

    readonly_fields = [
        "subject_cn",
        "subject_dn",
        "issuer_cn",
        "issuer_dn",
        "serial_number",
        "fingerprint_sha256",
        "not_before",
        "not_after",
        "key_usage",
        "extended_key_usage",
    ]

    def is_valid_display(self, obj):
        from django.utils.html import format_html

        is_valid = obj.is_valid
        if is_valid is None:
            return format_html('<span style="color: gray;">Unknown</span>')
        elif is_valid:
            days = obj.days_until_expiry
            if days and days < 30:
                return format_html(
                    '<span style="color: orange;">✓ Valid ({} days)</span>', days
                )
            return format_html('<span style="color: green;">✓ Valid</span>')
        else:
            return format_html('<span style="color: red;">✗ Expired</span>')

    is_valid_display.short_description = "Validity"
