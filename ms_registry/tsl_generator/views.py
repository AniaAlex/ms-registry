"""
Views for TSL Generator
"""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from legal_entities.models import LegalEntity
from registry.models import RegisteredEntity
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from . import serializers
from .models import (
    SERVICE_STATUS_CHOICES,
    SERVICE_TYPE_CHOICES,
    TrustService,
    TrustServiceProvider,
    TSLScheme,
)
from .registered_entity_prefill import (
    build_trust_service_prefill,
    tsl_eligible_entitlement_types,
)
from .xml_generator import generate_tsl_xml_etsi_format


class TrustServiceProviderListCreateView(generics.ListCreateAPIView):
    """
    List all Trust Service Providers or create a new one via API.

    GET: List all TSPs
    POST: Create a new TSP
    """

    permission_classes = (IsAuthenticated,)
    queryset = TrustServiceProvider.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return serializers.TrustServiceProviderCreateSerializer
        return serializers.TrustServiceProviderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tsp = serializer.save()
        return Response(
            {
                "message": "Trust Service Provider created successfully",
                "data": serializers.TrustServiceProviderSerializer(tsp).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TrustServiceProviderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a Trust Service Provider.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.TrustServiceProviderSerializer
    queryset = TrustServiceProvider.objects.all()


class TrustServiceProviderFormView(generics.CreateAPIView):
    """
    Render TSP creation form on GET, create TSP on POST.

    GET: Render the TSP registration form
    POST: Create a new Trust Service Provider
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.TrustServiceProviderCreateSerializer
    queryset = TrustServiceProvider.objects.all()
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = "add_trust_service_provider.html"

    def get_context_data(self, errors=None):
        """Common context for the form"""
        return {
            "errors": errors,
            "tsl_schemes": TSLScheme.objects.filter(is_active=True),
            "legal_entities": LegalEntity.objects.all(),
            "service_types": SERVICE_TYPE_CHOICES,
        }

    def get(self, request, *args, **kwargs):
        """Render empty TSP form"""
        return Response(
            self.get_context_data(),
            template_name=self.template_name,
        )

    def post(self, request, *args, **kwargs):
        """Handle form submission"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                self.get_context_data(errors=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
                template_name=self.template_name,
            )

        tsp = serializer.save()

        # Check if this is an AJAX/API request
        if request.accepted_renderer.format == "json":
            return Response(
                {
                    "message": "Trust Service Provider created successfully",
                    "data": serializers.TrustServiceProviderSerializer(tsp).data,
                },
                status=status.HTTP_201_CREATED,
            )

        # HTML response - redirect to success page
        return Response(
            {
                "message": "Trust Service Provider added to TSL successfully",
                "tsp": tsp,
            },
            status=status.HTTP_201_CREATED,
            template_name="add_trust_service_provider_success.html",
        )


class TSLSchemeListView(generics.ListAPIView):
    """
    List all active TSL Schemes.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.TSLSchemeSerializer
    queryset = TSLScheme.objects.filter(is_active=True)


class TSLSchemeXMLView(generics.RetrieveAPIView):
    """
    Return the ETSI TS 119612 compliant XML for a TSL Scheme.

    GET: Returns application/xml
    """

    permission_classes = (IsAuthenticated,)
    queryset = TSLScheme.objects.filter(is_active=True)

    def retrieve(self, request, *args, **kwargs):
        scheme = self.get_object()
        xml_content = generate_tsl_xml_etsi_format(scheme)
        return HttpResponse(xml_content, content_type="application/xml")


class TSLXMLView(generics.GenericAPIView):
    """
    Return the ETSI TS 119612 compliant XML for the default active TSL Scheme.

    GET /tsl/xml/ - Returns XML for the first active scheme
    GET /tsl/xml/?download=true - Returns XML as downloadable file
    """

    def get(self, request, *args, **kwargs):
        scheme = TSLScheme.objects.filter(is_active=True).first()
        if not scheme:
            return HttpResponse(
                "No active TSL Scheme found", status=404, content_type="text/plain"
            )

        xml_content = generate_tsl_xml_etsi_format(scheme)

        # Check if download is requested
        if request.query_params.get("download", "").lower() in ("true", "1", "yes"):
            response = HttpResponse(xml_content, content_type="application/xml")
            filename = f"tsl-{scheme.territory}-{scheme.sequence_number}.xml"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        return HttpResponse(xml_content, content_type="application/xml")


# =============================================================================
# Trust Service Views
# =============================================================================
class TrustServiceListCreateView(generics.ListCreateAPIView):
    """
    List all Trust Services or create a new one via API.

    GET: List all services
    POST: Create a new service
    """

    permission_classes = (IsAuthenticated,)
    queryset = TrustService.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return serializers.TrustServiceCreateSerializer
        return serializers.TrustServiceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = serializer.save()
        return Response(
            {
                "message": "Trust Service created successfully",
                "data": serializers.TrustServiceSerializer(service).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TrustServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a Trust Service.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.TrustServiceSerializer
    queryset = TrustService.objects.all()


class TrustServiceFormView(generics.CreateAPIView):
    """
    Render Trust Service creation form on GET, create service on POST.

    GET: Render the Trust Service registration form
    POST: Create a new Trust Service (optionally with new TSP)
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.TrustServiceCreateSerializer
    queryset = TrustService.objects.all()
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = "add_trust_service.html"

    def get_context_data(self, errors=None, initial=None):
        """Common context for the form"""
        return {
            "errors": errors,
            "initial": initial,
            "tsl_schemes": TSLScheme.objects.filter(is_active=True),
            "providers": TrustServiceProvider.objects.filter(
                is_active=True
            ).select_related("scheme", "legal_entity"),
            "legal_entities": LegalEntity.objects.all(),
            "service_types": SERVICE_TYPE_CHOICES,
            "service_statuses": SERVICE_STATUS_CHOICES,
        }

    def get(self, request, *args, **kwargs):
        """
        Render the Trust Service form.

        With ?registered_entity=<id>&entitlement_type=<type>, prefills the
        new-provider fields and certificate from that entity's existing
        registration instead of a blank form - the operator still has to
        pick the TSL scheme and submit.
        """
        initial = None
        entity_id = request.query_params.get("registered_entity")
        if entity_id:
            entity = get_object_or_404(RegisteredEntity, pk=entity_id)
            entitlement_type = request.query_params.get("entitlement_type") or next(
                iter(tsl_eligible_entitlement_types(entity)), None
            )
            if entitlement_type:
                initial = build_trust_service_prefill(entity, entitlement_type)

        return Response(
            self.get_context_data(initial=initial),
            template_name=self.template_name,
        )

    def post(self, request, *args, **kwargs):
        """Handle form submission"""
        # Handle the checkbox for create_new_provider
        data = request.data.copy()
        data["create_new_provider"] = "create_new_provider" in request.data

        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response(
                self.get_context_data(errors=serializer.errors),
                status=status.HTTP_400_BAD_REQUEST,
                template_name=self.template_name,
            )

        service = serializer.save()

        # Check if this is an AJAX/API request
        if request.accepted_renderer.format == "json":
            return Response(
                {
                    "message": "Trust Service created successfully",
                    "data": serializers.TrustServiceSerializer(service).data,
                },
                status=status.HTTP_201_CREATED,
            )

        # HTML response - redirect to success page
        return Response(
            {
                "message": "Trust Service added to TSL successfully",
                "service": service,
            },
            status=status.HTTP_201_CREATED,
            template_name="add_trust_service_success.html",
        )
