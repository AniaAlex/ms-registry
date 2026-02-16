from core.models import EntitlementType
from django.views.generic import TemplateView
from legal_entities.models import LegalEntity
from rest_framework import generics, status
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response

from . import models, serializers


class HomeView(TemplateView):
    """
    Home page view that lists all registered entities.
    """

    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entities"] = models.RegisteredEntity.objects.select_related(
            "legal_entity", "supervisory_authority"
        ).order_by("-created_at")
        return context


class RegisteredEntityListCreateView(generics.ListCreateAPIView):
    """
    List all registered entities or create a new one.
    Supports both API (JSON) and HTML form rendering.

    GET: List all registered entities (API) or render form (HTML)
    POST: Create a new registered entity
    """

    permission_classes = []
    serializer_class = serializers.RegisteredEntitySerializer
    queryset = models.RegisteredEntity.objects.all()
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    def get(self, request, *args, **kwargs):
        # If HTML is requested and 'form' param present, show the registration form
        if request.accepted_renderer.format == "html":
            return Response(
                {
                    "serializer": self.get_serializer(),
                    "errors": None,
                    "legal_entities": LegalEntity.objects.all(),
                    "supervisory_authorities": models.SupervisoryAuthority.objects.all(),
                    "entity_roles": models.RegisteredEntity._meta.get_field(
                        "entity_role"
                    ).choices,
                    "entitlement_types": EntitlementType.choices,
                },
                template_name="register_entity.html",
            )
        # Otherwise return JSON list
        return self.list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # HTML form submission - re-render form with errors
            if (
                hasattr(request, "accepted_renderer")
                and request.accepted_renderer.format == "html"
            ):
                return Response(
                    {
                        "serializer": serializer,
                        "errors": serializer.errors,
                        "legal_entities": LegalEntity.objects.all(),
                        "supervisory_authorities": models.SupervisoryAuthority.objects.all(),
                        "entity_roles": models.RegisteredEntity._meta.get_field(
                            "entity_role"
                        ).choices,
                        "entitlement_types": EntitlementType.choices,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                    template_name="register_entity.html",
                )
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # HTML form submission - show success page
        if (
            hasattr(request, "accepted_renderer")
            and request.accepted_renderer.format == "html"
        ):
            return Response(
                {
                    "message": "Entity registered successfully",
                    "entity": serializer.data,
                },
                status=status.HTTP_201_CREATED,
                template_name="register_entity_success.html",
            )

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


# =============================================================================
# Supervisory Authority Views
# =============================================================================


class SupervisoryAuthorityListCreateView(generics.ListCreateAPIView):
    """
    List all supervisory authorities or create a new one via API.

    GET: List all supervisory authorities
    POST: Create a new supervisory authority
    """

    permission_classes = []
    queryset = models.SupervisoryAuthority.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return serializers.SupervisoryAuthorityCreateSerializer
        return serializers.SupervisoryAuthoritySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        authority = serializer.save()
        return Response(
            {
                "message": "Supervisory authority created successfully",
                "data": serializers.SupervisoryAuthoritySerializer(authority).data,
            },
            status=status.HTTP_201_CREATED,
        )


class SupervisoryAuthorityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a supervisory authority.
    """

    permission_classes = []
    serializer_class = serializers.SupervisoryAuthoritySerializer
    queryset = models.SupervisoryAuthority.objects.all()


class SupervisoryAuthorityFormView(generics.CreateAPIView):
    """
    Render supervisory authority creation form on GET, create authority on POST.

    GET: Render the supervisory authority form
    POST: Create a new supervisory authority
    """

    permission_classes = []
    serializer_class = serializers.SupervisoryAuthorityCreateSerializer
    queryset = models.SupervisoryAuthority.objects.all()
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    template_name = "add_supervisory_authority.html"

    def get_context_data(self, errors=None):
        """Common context for the form"""
        return {
            "errors": errors,
            "legal_entities": LegalEntity.objects.all(),
        }

    def get(self, request, *args, **kwargs):
        """Render empty supervisory authority form"""
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

        authority = serializer.save()

        # Check if this is an AJAX/API request
        if request.accepted_renderer.format == "json":
            return Response(
                {
                    "message": "Supervisory authority created successfully",
                    "data": serializers.SupervisoryAuthoritySerializer(authority).data,
                },
                status=status.HTTP_201_CREATED,
            )

        # HTML response - redirect to success page
        return Response(
            {
                "message": "Supervisory authority created successfully",
                "authority": authority,
            },
            status=status.HTTP_201_CREATED,
            template_name="add_supervisory_authority_success.html",
        )
