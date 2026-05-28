import pytest
from participant.tests.factories import ParticipantFactory
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def jwt_token(db):
    participant = ParticipantFactory()
    return str(RefreshToken.for_user(participant).access_token)


@pytest.fixture
def authenticated_api_client(jwt_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_token}")
    return client


@pytest.fixture
def auth_client(client, jwt_token):
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {jwt_token}"
    return client
