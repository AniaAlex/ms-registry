from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import (
    AuthenticationFailed,
    InvalidToken,
    TokenError,
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import TokenObtainPairView


class LoginThrottle(AnonRateThrottle):
    rate = "overriden/below"  # Needed but overriden by parse_rate()

    def parse_rate(self, rate):
        return 10, 60 * 15  # 10 requests per 15 minutes


class ParticipantTokenObtainPairView(TokenObtainPairView):
    throttle_classes = (LoginThrottle,)


def _is_valid_access_token(token_str):
    try:
        AccessToken(token_str)
        return True
    except Exception:
        return False


def _token_from_request(request):
    token = request.COOKIES.get("access_token")
    if not token:
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    return token


class JWTLoginRequiredMixin:
    """Redirect to login if request carries no valid JWT (cookie or Bearer header)."""

    def dispatch(self, request, *args, **kwargs):
        token = _token_from_request(request)
        if not token or not _is_valid_access_token(token):
            return HttpResponseRedirect(reverse("participant:login"))
        return super().dispatch(request, *args, **kwargs)


class LoginView(APIView):
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    throttle_classes = (LoginThrottle,)
    authentication_classes = ()
    permission_classes = (AllowAny,)
    template_name = "participant/login.html"

    def get(self, request):
        if request.accepted_renderer.format == "html":
            token = _token_from_request(request)
            if token and _is_valid_access_token(token):
                return HttpResponseRedirect(reverse("home"))
        return Response({})

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, InvalidToken, TokenError):
            if request.accepted_renderer.format == "html":
                return Response(
                    {"error": "Invalid email or password."},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"detail": "No active account found with the given credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = serializer.validated_data

        if request.accepted_renderer.format == "html":
            response = HttpResponseRedirect(reverse("home"))
            response.set_cookie(
                "access_token",
                tokens["access"],
                httponly=False,  # accessible to JS for API calls
                samesite="Lax",
            )
            response.set_cookie(
                "refresh_token",
                tokens["refresh"],
                httponly=True,
                samesite="Lax",
            )
            return response

        return Response(tokens)
