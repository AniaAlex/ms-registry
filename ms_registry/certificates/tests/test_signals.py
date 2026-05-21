"""
Tests for certificate auto-revocation signal.

Uses transaction=True so transaction.on_commit() callbacks actually fire.
EntityAccessCertificates without a django_ca_certificate link exercise the
local-record-only path in revoke_entity_certificates (no CA call needed).
"""

from datetime import timedelta

import pytest
from certificates.models import EntityAccessCertificate
from core.models import RegistrationStatus
from django.db import transaction
from django.utils import timezone
from registry.tests.factories import RegisteredEntityFactory

# ---------------------------------------------------------------------------
# Helpers / inline factory
# ---------------------------------------------------------------------------


def _make_cert(entity, *, is_current=True, revoked=False):
    now = timezone.now()
    return EntityAccessCertificate.objects.create(
        registered_entity=entity,
        certificate_serial="DEADBEEF",
        not_before=now,
        not_after=now + timedelta(days=365),
        is_current=is_current,
        revoked_at=now if revoked else None,
        revocation_reason="superseded" if revoked else None,
    )


def _active_entity(**kwargs):
    return RegisteredEntityFactory(
        registration_status=RegistrationStatus.ACTIVE, **kwargs
    )


def _change_status(entity, new_status):
    entity.registration_status = new_status
    entity.save()


# ---------------------------------------------------------------------------
# Revocation fires for the two triggering transitions
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_active_to_suspended_revokes_with_certificate_hold():
    entity = _active_entity()
    cert = _make_cert(entity)

    _change_status(entity, RegistrationStatus.SUSPENDED)

    cert.refresh_from_db()
    assert cert.revoked_at is not None
    assert cert.revocation_reason == "certificateHold"


@pytest.mark.django_db(transaction=True)
def test_active_to_revoked_revokes_with_cessation_of_operation():
    entity = _active_entity()
    cert = _make_cert(entity)

    _change_status(entity, RegistrationStatus.REVOKED)

    cert.refresh_from_db()
    assert cert.revoked_at is not None
    assert cert.revocation_reason == "cessationOfOperation"


@pytest.mark.django_db(transaction=True)
def test_pending_to_suspended_revokes():
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.PENDING)
    cert = _make_cert(entity)

    _change_status(entity, RegistrationStatus.SUSPENDED)

    cert.refresh_from_db()
    assert cert.revoked_at is not None


# ---------------------------------------------------------------------------
# No revocation for non-triggering transitions
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_suspended_to_revoked_does_not_re_revoke():
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.SUSPENDED)
    cert = _make_cert(entity)

    _change_status(entity, RegistrationStatus.REVOKED)

    cert.refresh_from_db()
    assert cert.revoked_at is None


@pytest.mark.django_db(transaction=True)
def test_active_to_active_no_revocation():
    entity = _active_entity()
    cert = _make_cert(entity)

    _change_status(entity, RegistrationStatus.ACTIVE)

    cert.refresh_from_db()
    assert cert.revoked_at is None


@pytest.mark.django_db(transaction=True)
def test_active_to_pending_no_revocation():
    entity = _active_entity()
    cert = _make_cert(entity)

    _change_status(entity, RegistrationStatus.PENDING)

    cert.refresh_from_db()
    assert cert.revoked_at is None


@pytest.mark.django_db(transaction=True)
def test_new_entity_creation_no_revocation():
    entity = RegisteredEntityFactory(registration_status=RegistrationStatus.SUSPENDED)
    # No cert was created before, and no crash means signal skipped correctly.
    assert EntityAccessCertificate.objects.filter(registered_entity=entity).count() == 0


# ---------------------------------------------------------------------------
# Only eligible certificates are revoked
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_only_current_non_revoked_certs_are_revoked():
    entity = _active_entity()
    active_cert = _make_cert(entity, is_current=True, revoked=False)
    already_revoked = _make_cert(entity, is_current=True, revoked=True)
    historical = _make_cert(entity, is_current=False, revoked=False)

    _change_status(entity, RegistrationStatus.SUSPENDED)

    active_cert.refresh_from_db()
    already_revoked.refresh_from_db()
    historical.refresh_from_db()

    assert active_cert.revoked_at is not None
    # pre-revoked timestamp must not change
    assert already_revoked.revocation_reason == "superseded"
    # non-current cert untouched
    assert historical.revoked_at is None


@pytest.mark.django_db(transaction=True)
def test_all_current_certs_revoked_when_multiple():
    entity = _active_entity()
    certs = [_make_cert(entity) for _ in range(3)]

    _change_status(entity, RegistrationStatus.SUSPENDED)

    for cert in certs:
        cert.refresh_from_db()
        assert cert.revoked_at is not None


@pytest.mark.django_db(transaction=True)
def test_no_certs_does_not_raise():
    entity = _active_entity()
    # No certs — should complete silently
    _change_status(entity, RegistrationStatus.SUSPENDED)
    assert EntityAccessCertificate.objects.filter(registered_entity=entity).count() == 0


# ---------------------------------------------------------------------------
# on_commit: revocation is deferred until the transaction commits
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_revocation_deferred_until_commit():
    entity = _active_entity()
    cert = _make_cert(entity)

    with transaction.atomic():
        _change_status(entity, RegistrationStatus.SUSPENDED)
        # Still inside the transaction — on_commit has not fired yet
        cert.refresh_from_db()
        assert cert.revoked_at is None

    # Transaction committed — on_commit fires now
    cert.refresh_from_db()
    assert cert.revoked_at is not None
