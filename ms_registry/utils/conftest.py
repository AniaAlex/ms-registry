import pytest
from participant.tests.factories import ParticipantFactory
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_participant(db):
    """The participant that ``authenticated_api_client`` is logged in as.

    Exposed so tests can register entities operated by this participant —
    certificate endpoints are scoped to an entity's operators.
    """
    return ParticipantFactory()


@pytest.fixture
def jwt_token(authenticated_participant):
    return str(RefreshToken.for_user(authenticated_participant).access_token)


@pytest.fixture
def authenticated_api_client(jwt_token, authenticated_participant):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {jwt_token}")
    client.participant = authenticated_participant
    return client


@pytest.fixture
def auth_client(client, jwt_token):
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {jwt_token}"
    return client


@pytest.fixture
def operator(db):
    """A participant used as an authenticated operator in tests."""
    return ParticipantFactory()


@pytest.fixture
def operator_client(client, operator):
    """Django test client authenticated as ``operator`` (for HTML views)."""
    token = str(RefreshToken.for_user(operator).access_token)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client
