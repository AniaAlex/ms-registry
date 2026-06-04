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
