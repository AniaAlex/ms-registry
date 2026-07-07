import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .factories import ParticipantFactory


@pytest.mark.django_db
def test_token_obtain_pair(api_client):
    participant = ParticipantFactory(password="hej123")
    url = reverse("participant:token_obtain_pair")
    response = api_client.post(url, {"email": participant.email, "password": "hej123"})
    assert response.status_code == status.HTTP_200_OK
    AccessToken(response.data["access"], verify=True)
    RefreshToken(response.data["refresh"], verify=True)


@pytest.mark.django_db
def test_token_obtain_pair_wrong_password(api_client):
    participant = ParticipantFactory(password="hej123")
    url = reverse("participant:token_obtain_pair")
    response = api_client.post(url, {"email": participant.email, "password": "wrong"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_token_refresh(api_client):
    participant = ParticipantFactory()
    refresh = RefreshToken.for_user(participant)
    url = reverse("participant:token_refresh")
    response = api_client.post(url, {"refresh": str(refresh)})
    assert response.status_code == status.HTTP_200_OK
    AccessToken(response.data["access"], verify=True)


@pytest.mark.django_db
def test_token_refresh_invalid_token(api_client):
    participant = ParticipantFactory()
    refresh = RefreshToken.for_user(participant)
    url = reverse("participant:token_refresh")
    response = api_client.post(url, {"refresh": str(refresh.access_token)[1:]})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_logout_clears_cookies_and_redirects(api_client):
    url = reverse("participant:logout")
    response = api_client.post(url)

    assert response.status_code == status.HTTP_302_FOUND
    assert response["Location"] == reverse("participant:login")
    # Both JWT cookies are expired/cleared.
    assert response.cookies["access_token"].value == ""
    assert response.cookies["access_token"]["max-age"] == 0
    assert response.cookies["refresh_token"].value == ""
    assert response.cookies["refresh_token"]["max-age"] == 0


@pytest.mark.django_db
def test_dashboard_shows_logout_button(operator_client):
    response = operator_client.get(reverse("home"))
    assert response.status_code == status.HTTP_200_OK
    # The dashboard renders a logout form pointing at the logout endpoint.
    assert reverse("participant:logout").encode() in response.content
    assert b"Log out" in response.content
