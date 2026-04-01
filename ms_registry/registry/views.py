from core.models import EntitlementType, EntityType, IdentifierType
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from legal_entities.models import LegalEntity
from legal_entities.serializers import LegalEntityCreateSerializer
from rest_framework import generics, status
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

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

    def get_form_context(
        self,
        errors=None,
        legal_entity_errors=None,
        le_form_data=None,
        new_legal_entity_id=None,
    ):
        """Common context for the registration form"""
        return {
            "serializer": self.get_serializer(),
            "errors": errors,
            "legal_entity_errors": legal_entity_errors,
            "le_form_data": le_form_data or {},
            "new_legal_entity_id": new_legal_entity_id,
            "legal_entities": LegalEntity.objects.all(),
            "supervisory_authorities": models.SupervisoryAuthority.objects.all(),
            "entity_roles": models.RegisteredEntity._meta.get_field(
                "entity_role"
            ).choices,
            "entitlement_types": EntitlementType.choices,
            "entity_types": EntityType.choices,
            "identifier_types": IdentifierType.choices,
        }

    def get(self, request, *args, **kwargs):
        # If HTML is requested and 'form' param present, show the registration form
        if request.accepted_renderer.format == "html":
            return Response(
                self.get_form_context(),
                template_name="register_entity.html",
            )
        # Otherwise return JSON list
        return self.list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # Check if we need to create a new legal entity first
        create_new_legal_entity = request.data.get("create_new_legal_entity") == "true"
        new_legal_entity_id = None

        if create_new_legal_entity and request.accepted_renderer.format == "html":
            # Extract legal entity data from prefixed fields
            le_data = {
                "entity_type": request.data.get("le_entity_type"),
                "legal_name": request.data.get("le_legal_name"),
                "legal_form": request.data.get("le_legal_form"),
                "registration_date": request.data.get("le_registration_date") or None,
                "given_name": request.data.get("le_given_name"),
                "family_name": request.data.get("le_family_name"),
                "nationality": request.data.get("le_nationality"),
                "street_address": request.data.get("le_street_address"),
                "locality": request.data.get("le_locality"),
                "country_code": request.data.get("le_country_code"),
                "identifier_type": request.data.get("le_identifier_type"),
                "identifier_value": request.data.get("le_identifier_value"),
                "email": request.data.get("le_email"),
            }

            le_serializer = LegalEntityCreateSerializer(data=le_data)
            if not le_serializer.is_valid():
                return Response(
                    self.get_form_context(
                        legal_entity_errors=le_serializer.errors,
                        le_form_data=le_data,
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                    template_name="register_entity.html",
                )

            # Create the legal entity
            legal_entity = le_serializer.save()
            new_legal_entity_id = str(legal_entity.id)

            # Update request data to use the new legal entity
            request_data = request.data.copy()
            request_data["legal_entity"] = new_legal_entity_id
        else:
            request_data = request.data

        serializer = self.get_serializer(data=request_data)
        if not serializer.is_valid():
            # HTML form submission - re-render form with errors
            if (
                hasattr(request, "accepted_renderer")
                and request.accepted_renderer.format == "html"
            ):
                return Response(
                    self.get_form_context(
                        errors=serializer.errors,
                        new_legal_entity_id=new_legal_entity_id,
                    ),
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

    def get_context_data(self, errors=None, form_data=None):
        """Common context for the form"""
        return {
            "errors": errors,
            "form_data": form_data or {},
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
                self.get_context_data(errors=serializer.errors, form_data=request.data),
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


# =============================================================================
# WalletRelyingParty API Views (TS5 Specification)
# =============================================================================


class WalletRelyingPartyView(generics.GenericAPIView):
    """
    WalletRelyingParty API endpoint per TS5 specification.

    path: /wrp

    Supported methods:
    - GET: List all WalletRelyingParties (returns 200)
    - POST: Create a new WalletRelyingParty (returns 201)
    - PUT: Update an existing WalletRelyingParty (returns 200 or 404)
    - DELETE: Delete an existing WalletRelyingParty (returns 204)

    Note: The harmonisation of the POST method (means to accomplish registration
    of a new Wallet-Relying Party) has been left for further study per TS5.

    Reference:
    https://github.com/eu-digital-identity-wallet/eudi-doc-standards-and-technical-specifications/
    blob/main/docs/technical-specifications/ts5-common-formats-and-api-for-rp-registration-information.md
    """

    permission_classes = []
    serializer_class = serializers.WalletRelyingPartySerializer
    queryset = models.RegisteredEntity.objects.all().select_related(
        "legal_entity", "supervisory_authority"
    )

    @extend_schema(
        parameters=[serializers.WRPQueryParameterSerializer],
        responses={200: serializers.WalletRelyingPartyResponseSerializer(many=True)},
        description=(
            "List all WalletRelyingParties, optionally filtered by "
            "entitlement URI or intermediary status."
        ),
    )
    def get(self, request, *args, **kwargs):
        """
        List all WalletRelyingParties.

        Supports filtering by entitlement URI and intermediary status:
        GET /wrp?entitlement=http://data.europa.eu/eudi/entitlement/PUB_EAA_Provider
        GET /wrp?isintermediary=true

        Returns 200 with a list of all registered WRPs
        (filtered if query param provided).
        """
        queryset = self.get_queryset()

        # Filter by entitlement URI if provided
        entitlement_filter = request.query_params.get("entitlement")
        if entitlement_filter:
            queryset = queryset.filter(entitlements__entitlement_uri=entitlement_filter)

        # Filter by intermediary status if provided
        isintermediary = request.query_params.get("isintermediary")
        if isintermediary is not None:
            is_intermediary_bool = isintermediary.lower() in ("true", "1", "yes")
            queryset = queryset.filter(is_intermediary=is_intermediary_bool)

        serializer = self.get_serializer()
        data = [serializer.to_representation(obj) for obj in queryset]
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        request=serializers.WalletRelyingPartySerializer,
        responses={201: serializers.WalletRelyingPartyResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new WalletRelyingParty.

        Expects a request body with the WalletRelyingParty schema.
        Returns 201 on success with the created WRP data.
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        registered_entity = serializer.save()

        return Response(
            serializer.to_representation(registered_entity),
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=serializers.WalletRelyingPartySerializer,
        responses={200: serializers.WalletRelyingPartyResponseSerializer},
    )
    def put(self, request, *args, **kwargs):
        """
        Update an existing WalletRelyingParty.

        Expects a request body with the WalletRelyingParty schema including 'id'.
        Returns 200 on success or 404 if not found.
        """
        wrp_id = request.data.get("id")
        if not wrp_id:
            return Response(
                {"error": "WalletRelyingParty 'id' is required for update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            instance = self.get_queryset().get(id=wrp_id)
        except models.RegisteredEntity.DoesNotExist:
            return Response(
                {"error": f"WalletRelyingParty with id '{wrp_id}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_entity = serializer.update(instance, serializer.validated_data)

        return Response(
            serializer.to_representation(updated_entity),
            status=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        """
        Delete an existing WalletRelyingParty.

        Expects a request body with the WalletRelyingParty identifier.
        Returns 204 on success.
        """
        wrp_id = request.data.get("id")
        if not wrp_id:
            return Response(
                {"error": "WalletRelyingParty 'id' is required for deletion"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            instance = self.get_queryset().get(id=wrp_id)
        except models.RegisteredEntity.DoesNotExist:
            return Response(
                {"error": f"WalletRelyingParty with id '{wrp_id}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Delete the registered entity (cascade will handle related records)
        instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class WalletRelyingPartyListView(generics.ListAPIView):
    """
    List all WalletRelyingParties.

    path: /wrp/list

    GET: Returns a list of all registered WalletRelyingParties.
    """

    permission_classes = []
    serializer_class = serializers.WalletRelyingPartySerializer
    queryset = models.RegisteredEntity.objects.all().select_related(
        "legal_entity", "supervisory_authority"
    )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer()
        data = [serializer.to_representation(obj) for obj in queryset]
        return Response(data, status=status.HTTP_200_OK)


class WalletRelyingPartyDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single WalletRelyingParty by ID.

    path: /wrp/<uuid:pk>

    GET: Returns the WalletRelyingParty data for the given ID.
    """

    permission_classes = []
    serializer_class = serializers.WalletRelyingPartySerializer
    queryset = models.RegisteredEntity.objects.filter(
        entity_role="RELYING_PARTY"
    ).select_related("legal_entity", "supervisory_authority")

    @extend_schema(responses={200: serializers.WalletRelyingPartyResponseSerializer})
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer()
        return Response(
            serializer.to_representation(instance),
            status=status.HTTP_200_OK,
        )


# =============================================================================
# JWKS endpoint
# =============================================================================


class JWKSView(APIView):
    """
    /.well-known/jwks.json

    Publishes the registrar's public signing key in JWK Set format (RFC 7517).
    Consumers (WRPAC/WRPRC providers) use this to verify JWS-signed responses.

    TODO: Replace the placeholder key with the real registrar public key.
          The corresponding private key should be stored in Hiera (eyaml-encrypted)
          and injected via REGISTRY_SIGNING_KEY env var.
    """

    permission_classes = []
    authentication_classes = []

    # Placeholder EC P-256 public key (fake - for development only).
    # Replace x, y, and kid before pilot go-live.
    _PLACEHOLDER_JWKS = {
        "keys": [
            {
                "kty": "EC",
                "crv": "P-256",
                "use": "sig",
                "alg": "ES256",
                "kid": "ms-registry-signing-key-v1",
                # Coordinates from RFC 7517 Appendix A example — NOT a real key
                "x": "f83OJ3D2xF1Bg8vub9tLe1gHMzV76e8Tus9uPHvRVEU",
                "y": "x_FEzRu9m36HLN_tue659LNpXW6pCyStikYjKIWI5a0",
            }
        ]
    }

    def get(self, request, *args, **kwargs):
        return Response(self._PLACEHOLDER_JWKS, status=status.HTTP_200_OK)


class LoteView(APIView):
    """
    GET /registry/lote/

    Returns all active registered entities as a LoTE JSON document
    (ETSI TS 119 602 format). Consumed directly by tsl-tool load-lote step.
    """

    @extend_schema(
        summary="LoTE document (ETSI TS 119 602)",
        description=(
            "Returns all active registered entities as an unsigned LoTE JSON"
            " document. Consumed by tsl-tool load-lote for signing and publishing."
        ),
        responses={200: {"type": "object"}},
    )
    def get(self, request, *args, **kwargs):
        from django.utils import timezone

        entities = (
            models.RegisteredEntity.objects.filter(registration_status="active")
            .select_related(
                "legal_entity__legal_person", "legal_entity__natural_person"
            )
            .prefetch_related(
                "entitlements", "service_descriptions", "access_certificates"
            )
        )

        trusted_entities = []
        for entity in entities:
            trusted_entities.append(self._build_entity(entity))

        lote = {
            "version": "1.0",
            "schemeInformation": {
                "territory": "SE",
                "schemeOperator": [
                    {"language": "en", "value": "WE BUILD WP4 Trust Group"}
                ],
                "schemeName": [
                    {"language": "en", "value": "WP4 List of Trusted Entities"}
                ],
                "schemeType": (
                    "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric"
                ),
                "issueDate": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sequenceNumber": 1,
            },
            "trustedEntities": trusted_entities,
        }
        return Response(lote)

    _STATUS_URI = {
        "active": "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted",
        "suspended": "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/suspended",
        "revoked": "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/revoked",
    }

    _SERVICE_TYPE_URI = {
        "PID_Provider": "http://uri.etsi.org/TrstSvc/Svctype/EAA/PID",
        "QEAA_Provider": "http://uri.etsi.org/TrstSvc/Svctype/EAA/QEAA",
        "Non_Q_EAA_Provider": "http://uri.etsi.org/TrstSvc/Svctype/EAA/NonQEAA",
        "PUB_EAA_Provider": "http://uri.etsi.org/TrstSvc/Svctype/EAA/PubEAA",
        "Service_Provider": "http://uri.etsi.org/TrstSvc/Svctype/RelyingParty",
        "QCert_for_ESig_Provider": "http://uri.etsi.org/TrstSvc/Svctype/CA/QC",
        "QCert_for_ESeal_Provider": "http://uri.etsi.org/TrstSvc/Svctype/CA/QCSeal",
        "Intermediary": "http://uri.etsi.org/TrstSvc/Svctype/Intermediary",
    }

    _ENTITY_TYPE = {
        "relying_party": "relying-party",
        "pid_provider": "pid-provider",
        "attestation_provider": "attestation-provider",
    }

    def _build_entity(self, entity):
        from django.utils import timezone

        descriptions = list(entity.service_descriptions.all())
        names = (
            [{"language": d.lang, "value": d.content} for d in descriptions]
            if descriptions
            else [{"language": "en", "value": entity.display_name}]
        )

        services = []
        for ent in entity.entitlements.all():
            svc_type = self._SERVICE_TYPE_URI.get(ent.entitlement_type)
            if not svc_type:
                continue
            expired = ent.expires_at and ent.expires_at < timezone.now()
            svc_status = (
                self._STATUS_URI["active"]
                if ent.is_active and not expired
                else self._STATUS_URI["revoked"]
            )
            services.append(
                {
                    "serviceType": svc_type,
                    "serviceName": [
                        {"language": "en", "value": ent.get_entitlement_type_display()}
                    ],
                    "serviceStatus": svc_status,
                }
            )

        digital_identities = []
        current_cert = entity.access_certificates.filter(
            is_current=True, certificate_pem__isnull=False
        ).first()
        if current_cert:
            pem = current_cert.certificate_pem
            b64 = "".join(pem.strip().splitlines()[1:-1])
            digital_identities.append({"type": "x509", "x509Certificate": b64})

        result = {
            "entityId": entity.registry_uri,
            "entityName": names,
            "entityStatus": self._STATUS_URI.get(
                entity.registration_status, self._STATUS_URI["active"]
            ),
            "digitalIdentities": digital_identities,
        }
        if entity.entity_role in self._ENTITY_TYPE:
            result["entityType"] = self._ENTITY_TYPE[entity.entity_role]
        if services:
            result["services"] = services
        return result
