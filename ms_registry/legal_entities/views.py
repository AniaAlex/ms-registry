"""
Views for Legal Entity management
"""

from core.models import EntityType, IdentifierType
from django.http import HttpResponseRedirect
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from . import models, serializers


class LegalEntityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a legal entity.
    """

    permission_classes = []
    serializer_class = serializers.LegalEntitySerializer
    queryset = models.LegalEntity.objects.all()


class LegalEntityCreateView(generics.CreateAPIView):
    """
    GET:  Render the legal entity creation form (HTML only).
    POST: Create a new legal entity.
          - HTML: redirects to success page on success, re-renders form on error.
          - JSON: returns created entity data or validation errors.
    """

    permission_classes = []
    serializer_class = serializers.LegalEntityCreateSerializer
    queryset = models.LegalEntity.objects.all()
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]
    template_name = "add_legal_entity.html"

    def _form_context(self, serializer):
        return {
            "serializer": serializer,
            "entity_types": EntityType.choices,
            "identifier_types": IdentifierType.choices,
        }

    @extend_schema(exclude=True)
    def get(self, request, *args, **kwargs):
        if request.accepted_renderer.format != "html":
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return Response(
            self._form_context(self.get_serializer()),
            template_name=self.template_name,
        )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            if request.accepted_renderer.format == "html":
                return Response(
                    self._form_context(serializer),
                    status=status.HTTP_400_BAD_REQUEST,
                    template_name=self.template_name,
                )
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()

        if request.accepted_renderer.format == "html":
            return HttpResponseRedirect(
                reverse("legal_entities:legal-entity-create-success")
            )

        return Response(
            {
                "message": "Legal entity created successfully",
                "data": serializers.LegalEntitySerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )
