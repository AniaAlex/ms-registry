from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTCookieAuthentication(JWTAuthentication):
    """Extends JWTAuthentication to accept the token from the access_token cookie."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            return result
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
