"""
Views for Legal Entity management
"""

from core.models import EntityType, IdentifierType
from rest_framework import generics, status
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from . import models, serializers


class LegalEntityListCreateView(generics.ListCreateAPIView):
    """
    List all legal entities or create a new one via API.

    GET: List all legal entities
    POST: Create a new legal entity
    """

    permission_classes = []
    queryset = models.LegalEntity.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return serializers.LegalEntityCreateSerializer
        return serializers.LegalEntitySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        legal_entity = serializer.save()
        return Response(
            {
                "message": "Legal entity created successfully",
                "data": serializers.LegalEntitySerializer(legal_entity).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LegalEntityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a legal entity.
    """

    permission_classes = []
    serializer_class = serializers.LegalEntitySerializer
    queryset = models.LegalEntity.objects.all()


class LegalEntityFormView(generics.CreateAPIView):
    """
    Render legal entity creation form on GET, create entity on POST.

    GET: Render the legal entity form
    POST: Create a new legal entity
    """

    permission_classes = []
    serializer_class = serializers.LegalEntityCreateSerializer
    queryset = models.LegalEntity.objects.all()
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = "add_legal_entity.html"

    def get_context_data(self, errors=None, form_data=None):
        """Common context for the form"""
        return {
            "errors": errors,
            "form_data": form_data or {},
            "entity_types": EntityType.choices,
            "identifier_types": IdentifierType.choices,
        }

    def get(self, request, *args, **kwargs):
        """Render empty legal entity form"""
        return Response(
            self.get_context_data(),
            template_name=self.template_name,
        )

    def post(self, request, *args, **kwargs):
        """Handle form submission"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                self.get_context_data(errors=serializer.errors, form_data=request.data),
                status=status.HTTP_400_BAD_REQUEST,
                template_name=self.template_name,
            )

        legal_entity = serializer.save()

        # Check if this is an AJAX/API request
        if request.accepted_renderer.format == "json":
            return Response(
                {
                    "message": "Legal entity created successfully",
                    "data": serializers.LegalEntitySerializer(legal_entity).data,
                },
                status=status.HTTP_201_CREATED,
            )

        # HTML response - redirect to success page
        return Response(
            {
                "message": "Legal entity created successfully",
                "entity": legal_entity,
            },
            status=status.HTTP_201_CREATED,
            template_name="add_legal_entity_success.html",
        )
