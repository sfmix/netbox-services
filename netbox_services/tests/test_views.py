from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from tenancy.models import Tenant
from users.models import ObjectPermission

from netbox_services.models import Service

User = get_user_model()


class ServiceViewTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.service = Service.objects.create(service_id='NW-1', type='dia')

    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.client = Client()
        self.client.force_login(self.user)

    def _grant(self, *actions):
        permission = ObjectPermission.objects.create(
            name='Service permission',
            actions=list(actions),
        )
        permission.object_types.add(
            __import__('django.contrib.contenttypes.models', fromlist=['ContentType'])
            .ContentType.objects.get_for_model(Service)
        )
        permission.users.add(self.user)

    def test_list_view_requires_permission(self):
        url = reverse('plugins:netbox_services:service_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_list_view_with_permission(self):
        self._grant('view')
        url = reverse('plugins:netbox_services:service_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'NW-1')

    def test_detail_view_with_permission(self):
        self._grant('view')
        url = reverse('plugins:netbox_services:service_view', kwargs={'pk': self.service.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_add_view_creates_service(self):
        self._grant('view', 'add')
        url = reverse('plugins:netbox_services:service_add')
        response = self.client.post(url, {
            'type': 'dia',
            'service_id': 'NW-2',
            'status': 'active',
        })
        self.assertEqual(Service.objects.filter(service_id='NW-2').count(), 1)

    def test_delete_view_removes_service(self):
        self._grant('view', 'delete')
        url = reverse('plugins:netbox_services:service_delete', kwargs={'pk': self.service.pk})
        self.client.post(url, {'confirm': True})
        self.assertFalse(Service.objects.filter(pk=self.service.pk).exists())

    def test_detail_view_lists_parties(self):
        self._grant('view')
        self.service.tenants.add(Tenant.objects.create(name='Globex', slug='globex'))
        url = reverse('plugins:netbox_services:service_view', kwargs={'pk': self.service.pk})
        response = self.client.get(url)
        self.assertContains(response, 'Globex')

    def _grant_view_tenants(self):
        # Edit views restrict related-object choices to what the user can view
        permission = ObjectPermission.objects.create(name='Tenant view', actions=['view'])
        permission.object_types.add(ContentType.objects.get_for_model(Tenant))
        permission.users.add(self.user)

    def test_relate_tenants_assigns_parties(self):
        self._grant('view', 'change')
        self._grant_view_tenants()
        acme = Tenant.objects.create(name='Acme', slug='acme')
        globex = Tenant.objects.create(name='Globex', slug='globex')
        url = reverse('plugins:netbox_services:relate_tenants', kwargs={'pk': self.service.pk})
        self.client.post(url, {'tenants': [acme.pk, globex.pk]})
        self.assertEqual(set(self.service.tenants.all()), {acme, globex})

    def test_relate_tenants_can_clear_parties(self):
        self._grant('view', 'change')
        self._grant_view_tenants()
        self.service.tenants.add(Tenant.objects.create(name='Acme', slug='acme'))
        url = reverse('plugins:netbox_services:relate_tenants', kwargs={'pk': self.service.pk})
        self.client.post(url, {})
        self.assertFalse(self.service.tenants.exists())
