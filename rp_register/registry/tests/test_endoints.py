"""
Tests for Registry app endpoints and models.
"""

import uuid

from core.models import EntityRole, RegistrationStatus
from django.test import TestCase
from django.urls import reverse
from legal_entities.models import LegalEntity, LegalPerson, PhysicalAddress
from registry.models import (
    EntityEntitlement,
    EntityServiceDescription,
    EntitySupportURI,
    EntityUsesIntermediary,
    RegisteredEntity,
    RegisteredEntityPolicy,
    SupervisoryAuthority,
)
from rest_framework import status
from rest_framework.test import APITestCase


class SupervisoryAuthorityModelTests(TestCase):
    """Tests for SupervisoryAuthority model"""

    def test_create_supervisory_authority_with_email(self):
        """Test creating a supervisory authority with email contact"""
        authority = SupervisoryAuthority.objects.create(
            authority_name="Swedish Data Protection Authority",
            country_code="SE",
            email="datainspektionen@datainspektionen.se",
        )
        self.assertEqual(authority.authority_name, "Swedish Data Protection Authority")
        self.assertEqual(authority.country_code, "SE")
        self.assertIsNotNone(authority.id)

    def test_create_supervisory_authority_with_phone(self):
        """Test creating a supervisory authority with phone contact"""
        authority = SupervisoryAuthority.objects.create(
            authority_name="German DPA",
            country_code="DE",
            phone="+49123456789",
        )
        self.assertEqual(authority.phone, "+49123456789")

    def test_create_supervisory_authority_with_info_uri(self):
        """Test creating a supervisory authority with info URI"""
        authority = SupervisoryAuthority.objects.create(
            authority_name="French CNIL",
            country_code="FR",
            info_uri="https://www.cnil.fr/",
        )
        self.assertEqual(authority.info_uri, "https://www.cnil.fr/")

    def test_supervisory_authority_str(self):
        """Test string representation"""
        authority = SupervisoryAuthority.objects.create(
            authority_name="Test Authority",
            country_code="SE",
            email="test@test.se",
        )
        self.assertEqual(str(authority), "Test Authority (SE)")


class RegisteredEntityModelTests(TestCase):
    """Tests for RegisteredEntity model"""

    def setUp(self):
        """Set up test data"""
        # Create physical address
        self.address = PhysicalAddress.objects.create(
            street_address="Test Street 1",
            locality="Stockholm",
            postal_code="12345",
            country_code="SE",
        )

        # Create legal person
        self.legal_person = LegalPerson.objects.create(
            legal_name="Test Company AB",
        )

        # Create legal entity
        self.legal_entity = LegalEntity.objects.create(
            entity_type="legal_person",
            legal_person=self.legal_person,
            physical_address=self.address,
            email="test@testcompany.se",
        )

        # Create supervisory authority
        self.authority = SupervisoryAuthority.objects.create(
            authority_name="Swedish DPA",
            country_code="SE",
            email="dpa@sweden.se",
        )

    def test_create_relying_party(self):
        """Test creating a Relying Party entity"""
        entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            trade_name="Test Service",
            registry_uri="https://registry.example.com/entities/123",
            supervisory_authority=self.authority,
        )
        self.assertEqual(entity.entity_role, EntityRole.RELYING_PARTY)
        self.assertTrue(entity.is_verifier)
        self.assertFalse(entity.is_issuer)

    def test_create_pid_provider(self):
        """Test creating a PID Provider entity"""
        entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.PID_PROVIDER,
            registry_uri="https://registry.example.com/entities/456",
            supervisory_authority=self.authority,
        )
        self.assertEqual(entity.entity_role, EntityRole.PID_PROVIDER)
        self.assertTrue(entity.is_issuer)
        self.assertFalse(entity.is_verifier)

    def test_create_attestation_provider(self):
        """Test creating an Attestation Provider entity"""
        entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.ATTESTATION_PROVIDER,
            is_psb=True,  # Public sector body
            registry_uri="https://registry.example.com/entities/789",
            supervisory_authority=self.authority,
        )
        self.assertEqual(entity.entity_role, EntityRole.ATTESTATION_PROVIDER)
        self.assertTrue(entity.is_psb)
        self.assertTrue(entity.is_issuer)

    def test_default_registration_status_is_pending(self):
        """Test that default registration status is pending"""
        entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            registry_uri="https://registry.example.com/entities/123",
            supervisory_authority=self.authority,
        )
        self.assertEqual(entity.registration_status, RegistrationStatus.PENDING)

    def test_display_name_uses_trade_name(self):
        """Test display_name property prefers trade_name"""
        entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            trade_name="My Trade Name",
            registry_uri="https://registry.example.com/entities/123",
            supervisory_authority=self.authority,
        )
        self.assertEqual(entity.display_name, "My Trade Name")

    def test_display_name_falls_back_to_legal_entity(self):
        """Test display_name falls back to legal entity name"""
        entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            registry_uri="https://registry.example.com/entities/123",
            supervisory_authority=self.authority,
        )
        self.assertEqual(entity.display_name, self.legal_entity.display_name)


class EntitySupportURIModelTests(TestCase):
    """Tests for EntitySupportURI model"""

    def setUp(self):
        """Set up test data"""
        self.address = PhysicalAddress.objects.create(
            country_code="SE",
        )
        self.legal_person = LegalPerson.objects.create(legal_name="Test Co")
        self.legal_entity = LegalEntity.objects.create(
            entity_type="legal_person",
            legal_person=self.legal_person,
            physical_address=self.address,
        )
        self.authority = SupervisoryAuthority.objects.create(
            authority_name="DPA", country_code="SE", email="dpa@test.se"
        )
        self.entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            registry_uri="https://registry.example.com/1",
            supervisory_authority=self.authority,
        )

    def test_create_support_uri(self):
        """Test creating a support URI"""
        support = EntitySupportURI.objects.create(
            registered_entity=self.entity,
            support_uri="https://support.example.com",
            support_type="website",
            is_primary=True,
        )
        self.assertEqual(support.support_uri, "https://support.example.com")
        self.assertTrue(support.is_primary)


class EntityEntitlementModelTests(TestCase):
    """Tests for EntityEntitlement model"""

    def setUp(self):
        """Set up test data"""
        self.address = PhysicalAddress.objects.create(country_code="SE")
        self.legal_person = LegalPerson.objects.create(legal_name="Test Co")
        self.legal_entity = LegalEntity.objects.create(
            entity_type="legal_person",
            legal_person=self.legal_person,
            physical_address=self.address,
        )
        self.authority = SupervisoryAuthority.objects.create(
            authority_name="DPA", country_code="SE", email="dpa@test.se"
        )
        self.entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            registry_uri="https://registry.example.com/1",
            supervisory_authority=self.authority,
        )

    def test_create_entitlement(self):
        """Test creating an entitlement"""
        from core.models import EntitlementType

        entitlement = EntityEntitlement.objects.create(
            registered_entity=self.entity,
            entitlement_uri="http://uri.etsi.org/TrstSvc/Svctype/EudiWallet/RelyingParty",
            entitlement_type=EntitlementType.SERVICE_PROVIDER,
        )
        self.assertTrue(entitlement.is_active)
        self.assertIsNotNone(entitlement.granted_at)


class SupervisoryAuthorityAPITests(APITestCase):
    """API tests for SupervisoryAuthority endpoints"""

    def test_list_supervisory_authorities(self):
        """Test listing supervisory authorities"""
        SupervisoryAuthority.objects.create(
            authority_name="Swedish DPA",
            country_code="SE",
            email="dpa@sweden.se",
        )
        SupervisoryAuthority.objects.create(
            authority_name="German DPA",
            country_code="DE",
            email="dpa@germany.de",
        )

        url = reverse("registry:supervisory-authority-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_supervisory_authority_api(self):
        """Test creating a supervisory authority via API"""
        url = reverse("registry:supervisory-authority-list-create")
        data = {
            "authority_name": "French CNIL",
            "country_code": "FR",
            "email": "contact@cnil.fr",
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupervisoryAuthority.objects.count(), 1)
        self.assertEqual(
            SupervisoryAuthority.objects.first().authority_name, "French CNIL"
        )

    def test_create_supervisory_authority_requires_contact(self):
        """Test that at least one contact method is required"""
        url = reverse("registry:supervisory-authority-list-create")
        data = {
            "authority_name": "Test Authority",
            "country_code": "SE",
            # No email, phone, or info_uri
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_supervisory_authority_detail(self):
        """Test retrieving a supervisory authority detail"""
        authority = SupervisoryAuthority.objects.create(
            authority_name="Test DPA",
            country_code="SE",
            email="test@dpa.se",
        )

        url = reverse("registry:supervisory-authority-detail", args=[authority.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["authority_name"], "Test DPA")


class RegisteredEntityAPITests(APITestCase):
    """API tests for RegisteredEntity endpoints"""

    def setUp(self):
        """Set up test data"""
        self.address = PhysicalAddress.objects.create(
            street_address="Test Street 1",
            locality="Stockholm",
            postal_code="12345",
            country_code="SE",
        )
        self.legal_person = LegalPerson.objects.create(
            legal_name="Test Company AB",
        )
        self.legal_entity = LegalEntity.objects.create(
            entity_type="legal_person",
            legal_person=self.legal_person,
            physical_address=self.address,
            email="test@testcompany.se",
        )
        self.authority = SupervisoryAuthority.objects.create(
            authority_name="Swedish DPA",
            country_code="SE",
            email="dpa@sweden.se",
        )

    def test_list_registered_entities(self):
        """Test listing registered entities"""
        RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            registry_uri="https://registry.example.com/1",
            supervisory_authority=self.authority,
        )

        url = reverse("registry:entity-list-create")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_registered_entity(self):
        """Test creating a registered entity via API"""
        url = reverse("registry:entity-list-create")
        data = {
            "legal_entity": str(self.legal_entity.id),
            "entity_role": EntityRole.RELYING_PARTY,
            "trade_name": "Test Service",
            "registry_uri": "https://registry.example.com/new",
            "supervisory_authority": str(self.authority.id),
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RegisteredEntity.objects.count(), 1)

    def test_create_registered_entity_missing_required_fields(self):
        """Test that required fields are validated"""
        url = reverse("registry:entity-list-create")
        data = {
            "trade_name": "Test Service",
            # Missing required fields
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HomeViewTests(TestCase):
    """Tests for the home page view"""

    def setUp(self):
        """Set up test data"""
        self.address = PhysicalAddress.objects.create(country_code="SE")
        self.legal_person = LegalPerson.objects.create(legal_name="Test Co")
        self.legal_entity = LegalEntity.objects.create(
            entity_type="legal_person",
            legal_person=self.legal_person,
            physical_address=self.address,
        )
        self.authority = SupervisoryAuthority.objects.create(
            authority_name="DPA", country_code="SE", email="dpa@test.se"
        )

    def test_home_page_loads(self):
        """Test that the home page loads successfully"""
        url = reverse("home")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")

    def test_home_page_shows_entities(self):
        """Test that registered entities are shown on home page"""
        entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            trade_name="Visible Entity",
            registry_uri="https://registry.example.com/1",
            supervisory_authority=self.authority,
        )

        url = reverse("home")
        response = self.client.get(url)

        self.assertContains(response, "Visible Entity")

    def test_home_page_empty_state(self):
        """Test home page shows empty state when no entities"""
        url = reverse("home")
        response = self.client.get(url)

        self.assertContains(response, "No registered entities yet")


class EntityIntermediaryTests(TestCase):
    """Tests for intermediary relationships"""

    def setUp(self):
        """Set up test data for two entities"""
        self.authority = SupervisoryAuthority.objects.create(
            authority_name="DPA", country_code="SE", email="dpa@test.se"
        )

        # Create first entity (RP that will use intermediary)
        self.address1 = PhysicalAddress.objects.create(country_code="SE")
        self.legal_person1 = LegalPerson.objects.create(legal_name="RP Company")
        self.legal_entity1 = LegalEntity.objects.create(
            entity_type="legal_person",
            legal_person=self.legal_person1,
            physical_address=self.address1,
        )
        self.rp_entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity1,
            entity_role=EntityRole.RELYING_PARTY,
            registry_uri="https://registry.example.com/rp",
            supervisory_authority=self.authority,
        )

        # Create second entity (Intermediary)
        self.address2 = PhysicalAddress.objects.create(country_code="SE")
        self.legal_person2 = LegalPerson.objects.create(legal_name="Intermediary Co")
        self.legal_entity2 = LegalEntity.objects.create(
            entity_type="legal_person",
            legal_person=self.legal_person2,
            physical_address=self.address2,
        )
        self.intermediary_entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity2,
            entity_role=EntityRole.RELYING_PARTY,
            is_intermediary=True,
            registry_uri="https://registry.example.com/intermediary",
            supervisory_authority=self.authority,
        )

    def test_rp_can_use_intermediary(self):
        """Test that a Relying Party can use an intermediary"""
        relationship = EntityUsesIntermediary.objects.create(
            registered_entity=self.rp_entity,
            intermediary=self.intermediary_entity,
            intermediary_identifier="INT-123",
            intermediary_registry_uri="https://registry.example.com/intermediary",
        )
        self.assertEqual(self.rp_entity.used_intermediaries.count(), 1)
        self.assertEqual(self.intermediary_entity.clients_using.count(), 1)


class EntityServiceDescriptionTests(TestCase):
    """Tests for multilingual service descriptions"""

    def setUp(self):
        """Set up test data"""
        self.address = PhysicalAddress.objects.create(country_code="SE")
        self.legal_person = LegalPerson.objects.create(legal_name="Test Co")
        self.legal_entity = LegalEntity.objects.create(
            entity_type="legal_person",
            legal_person=self.legal_person,
            physical_address=self.address,
        )
        self.authority = SupervisoryAuthority.objects.create(
            authority_name="DPA", country_code="SE", email="dpa@test.se"
        )
        self.entity = RegisteredEntity.objects.create(
            legal_entity=self.legal_entity,
            entity_role=EntityRole.RELYING_PARTY,
            registry_uri="https://registry.example.com/1",
            supervisory_authority=self.authority,
        )

    def test_create_multilingual_descriptions(self):
        """Test creating descriptions in multiple languages"""
        EntityServiceDescription.objects.create(
            registered_entity=self.entity,
            lang="en",
            content="English description of the service",
        )
        EntityServiceDescription.objects.create(
            registered_entity=self.entity,
            lang="sv",
            content="Svensk beskrivning av tjänsten",
        )

        self.assertEqual(self.entity.service_descriptions.count(), 2)

    def test_unique_language_per_entity(self):
        """Test that each language can only be used once per entity"""
        EntityServiceDescription.objects.create(
            registered_entity=self.entity,
            lang="en",
            content="First English description",
        )

        with self.assertRaises(Exception):  # IntegrityError
            EntityServiceDescription.objects.create(
                registered_entity=self.entity,
                lang="en",
                content="Second English description",
            )
