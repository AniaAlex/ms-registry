from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View
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
    rate = None
    num_requests = 10
    duration = 60 * 15

    def parse_rate(self, rate):
        return self.num_requests, self.duration


class ParticipantTokenObtainPairView(TokenObtainPairView):
    throttle_classes = (LoginThrottle,)


def _is_valid_access_token(token_str):
    try:
        AccessToken(token_str)
        return True
    except (InvalidToken, TokenError):
        return False


def _token_from_request(request):
    token = request.COOKIES.get("access_token")
    if not token:
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    return token


def _user_from_token(token_str):
    """Resolve the Participant a valid access token belongs to, or None."""
    try:
        access = AccessToken(token_str)
        user_id = access["user_id"]
    except (InvalidToken, TokenError, KeyError):
        return None
    user_model = get_user_model()
    try:
        return user_model.objects.get(pk=user_id)
    except (user_model.DoesNotExist, ValueError):
        return None


class JWTLoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        token = _token_from_request(request)
        user = _user_from_token(token) if token else None
        if user is None:
            # Clear any stale JWT cookies. A token can be cryptographically
            # valid yet map to no user (e.g. deleted account); LoginView.get
            # only checks token validity, so leaving the cookie set would
            # bounce login -> home -> login in an infinite redirect loop.
            response = HttpResponseRedirect(reverse("participant:login"))
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response
        # Attach the authenticated participant so plain Django views (which
        # otherwise see AnonymousUser from session middleware) can scope by
        # request.user. DRF views re-authenticate independently.
        request.user = user
        return super().dispatch(request, *args, **kwargs)


class LogoutView(View):
    """
    POST /participants/logout/

    Clears the JWT cookies set at login and redirects to the login page.

    A plain Django View (not a DRF APIView) so it is covered by
    CsrfViewMiddleware. DRF APIViews are CSRF-exempt, which would let a
    cross-site POST forcibly log a user out; the dashboard's logout form sends
    the CSRF token, so a legitimate logout is unaffected.
    """

    def post(self, request):
        response = HttpResponseRedirect(reverse("participant:login"))
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


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
                httponly=False,
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
