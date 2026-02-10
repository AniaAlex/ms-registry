from legal_entities.models import LegalEntity
from rest_framework import generics, status
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response

from . import models, serializers


class RegisterEntityFormView(generics.CreateAPIView):
    """
    Render registration form on GET, create entity on POST.

    GET: Render the registration form
    POST: Create a new registered entity
    """

    permission_classes = []
    serializer_class = serializers.RegisteredEntitySerializer
    queryset = models.RegisteredEntity.objects.all()
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "register_entity.html"

    def get(self, request, *args, **kwargs):
        """Render empty registration form"""
        serializer = self.get_serializer()
        return Response(
            {
                "serializer": serializer,
                "errors": None,
                "legal_entities": LegalEntity.objects.all(),
                "supervisory_authorities": models.SupervisoryAuthority.objects.all(),
                "entity_roles": models.RegisteredEntity._meta.get_field(
                    "entity_role"
                ).choices,
            },
            template_name=self.template_name,
        )

    def post(self, request, *args, **kwargs):
        """Handle form submission"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "serializer": serializer,
                    "errors": serializer.errors,
                    "legal_entities": LegalEntity.objects.all(),
                    "supervisory_authorities": models.SupervisoryAuthority.objects.all(),
                    "entity_roles": models.RegisteredEntity._meta.get_field(
                        "entity_role"
                    ).choices,
                },
                status=status.HTTP_400_BAD_REQUEST,
                template_name=self.template_name,
            )

        self.perform_create(serializer)
        # Redirect to entity detail or list on success
        return Response(
            {
                "message": "Entity registered successfully",
                "entity": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            template_name="register_entity_success.html",
        )


class RegisteredEntityListCreateView(generics.ListCreateAPIView):
    """
    List all registered entities or create a new one.

    GET: List all registered entities
    POST: Create a new registered entity
    """

    permission_classes = []
    serializer_class = serializers.RegisteredEntitySerializer
    queryset = models.RegisteredEntity.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "serializer": serializer,
                    **serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
                template_name="register_entity.html",
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "Entity registered successfully",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class RegisteredEntityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a registered entity.

    GET: Retrieve entity details
    PUT/PATCH: Update entity
    DELETE: Delete entity (or revoke)
    """

    permission_classes = []
    serializer_class = serializers.RegisteredEntitySerializer
    queryset = models.RegisteredEntity.objects.all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid():
            return Response(
                {
                    "errors": serializer.errors,
                    "entity": self.get_serializer(instance).data,
                    "message": "Validation failed for entity update",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        self.perform_update(serializer)
        return Response(
            {
                "message": "Entity updated successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
