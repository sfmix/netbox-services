from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from ipam.models import VLAN
from tenancy.models import Tenant
from utilities.testing import APITestCase

from netbox_services.models import Service


class ServiceAPITestCase(APITestCase):
    model = Service

    @classmethod
    def setUpTestData(cls):
        Service.objects.create(service_id='NW-1', type='dia')
        Service.objects.create(service_id='NW-2', type='l3vpn')

    def test_list_services(self):
        self.add_permissions('netbox_services.view_service')
        url = reverse('plugins-api:netbox_services-api:service-list')
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_get_service(self):
        self.add_permissions('netbox_services.view_service')
        service = Service.objects.get(service_id='NW-1')
        url = reverse('plugins-api:netbox_services-api:service-detail', kwargs={'pk': service.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['service_id'], 'NW-1')

    def test_create_service(self):
        self.add_permissions('netbox_services.add_service')
        url = reverse('plugins-api:netbox_services-api:service-list')
        data = {
            'type': 'cdn',
            'service_id': 'NW-3',
            'status': 'active',
        }
        response = self.client.post(url, data, format='json', **self.header)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Service.objects.filter(service_id='NW-3').exists())

    def test_create_service_without_permission_is_forbidden(self):
        url = reverse('plugins-api:netbox_services-api:service-list')
        data = {
            'type': 'cdn',
            'service_id': 'NW-4',
            'status': 'active',
        }
        response = self.client.post(url, data, format='json', **self.header)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_service(self):
        self.add_permissions('netbox_services.change_service')
        service = Service.objects.get(service_id='NW-1')
        url = reverse('plugins-api:netbox_services-api:service-detail', kwargs={'pk': service.pk})
        response = self.client.patch(url, {'description': 'Updated'}, format='json', **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        service.refresh_from_db()
        self.assertEqual(service.description, 'Updated')

    def test_delete_service(self):
        self.add_permissions('netbox_services.delete_service')
        service = Service.objects.get(service_id='NW-1')
        url = reverse('plugins-api:netbox_services-api:service-detail', kwargs={'pk': service.pk})
        response = self.client.delete(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Service.objects.filter(pk=service.pk).exists())


class ServiceDependencyAPITestCase(APITestCase):
    model = Service

    @classmethod
    def setUpTestData(cls):
        cls.dia = Service.objects.create(service_id='DIA-1', type='dia')
        cls.l3vpn = Service.objects.create(service_id='L3VPN-1', type='l3vpn')
        cls.l3vpn.depends_on.add(cls.dia)

    def test_depends_on_is_exposed_in_detail(self):
        self.add_permissions('netbox_services.view_service')
        url = reverse('plugins-api:netbox_services-api:service-detail', kwargs={'pk': self.l3vpn.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['depends_on'], [self.dia.pk])

    def test_dependents_is_exposed_in_detail(self):
        self.add_permissions('netbox_services.view_service')
        url = reverse('plugins-api:netbox_services-api:service-detail', kwargs={'pk': self.dia.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['dependents'], [self.l3vpn.pk])

    def test_filter_by_depends_on_id(self):
        self.add_permissions('netbox_services.view_service')
        url = reverse('plugins-api:netbox_services-api:service-list')
        response = self.client.get(url, {'depends_on_id': self.dia.pk}, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['service_id'], 'L3VPN-1')


class ServiceCapacityAPITestCase(APITestCase):
    model = Service

    @classmethod
    def setUpTestData(cls):
        Service.objects.create(
            service_id='NW-1', type='dia', bandwidth=1000, cir=500, sla_uptime_percent='99.90'
        )

    def test_capacity_fields_exposed_in_detail(self):
        self.add_permissions('netbox_services.view_service')
        service = Service.objects.get(service_id='NW-1')
        url = reverse('plugins-api:netbox_services-api:service-detail', kwargs={'pk': service.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['bandwidth'], 1000)
        self.assertEqual(response.data['cir'], 500)
        self.assertEqual(response.data['sla_uptime_percent'], Decimal('99.90'))

    def test_filter_by_bandwidth_min(self):
        self.add_permissions('netbox_services.view_service')
        url = reverse('plugins-api:netbox_services-api:service-list')
        response = self.client.get(url, {'bandwidth_min': 500}, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_create_service_rejects_cir_above_bandwidth(self):
        self.add_permissions('netbox_services.add_service')
        url = reverse('plugins-api:netbox_services-api:service-list')
        data = {
            'type': 'dia',
            'service_id': 'NW-2',
            'bandwidth': 100,
            'cir': 200,
        }
        response = self.client.post(url, data, format='json', **self.header)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ServiceRelationsAPITestCase(APITestCase):
    model = Service

    @classmethod
    def setUpTestData(cls):
        cls.vlans = [VLAN.objects.create(vid=vid, name=f'VLAN{vid}') for vid in (100, 200, 300)]
        cls.dia = Service.objects.create(service_id='DIA-1', type='dia')
        cls.l2vpn = Service.objects.create(service_id='L2VPN-1', type='l2vpn')
        cls.l2vpn.vlans.add(cls.vlans[0])
        cls.l2vpn.depends_on.add(cls.dia)

    def detail_url(self, service):
        return reverse('plugins-api:netbox_services-api:service-detail', kwargs={'pk': service.pk})

    def test_create_service_with_relations(self):
        self.add_permissions('netbox_services.add_service')
        url = reverse('plugins-api:netbox_services-api:service-list')
        data = {
            'type': 'l2vpn',
            'service_id': 'L2VPN-2',
            'vlans': [self.vlans[1].pk, self.vlans[2].pk],
            'depends_on': [self.dia.pk],
        }
        response = self.client.post(url, data, format='json', **self.header)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        service = Service.objects.get(service_id='L2VPN-2')
        self.assertEqual(set(service.vlans.values_list('pk', flat=True)), {self.vlans[1].pk, self.vlans[2].pk})
        self.assertEqual(list(service.depends_on.all()), [self.dia])

    def test_patch_replaces_relations(self):
        self.add_permissions('netbox_services.change_service')
        response = self.client.patch(
            self.detail_url(self.l2vpn), {'vlans': [self.vlans[2].pk]}, format='json', **self.header
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(self.l2vpn.vlans.all()), [self.vlans[2]])

    def test_patch_without_relations_leaves_them_alone(self):
        self.add_permissions('netbox_services.change_service')
        response = self.client.patch(
            self.detail_url(self.l2vpn), {'description': 'Updated'}, format='json', **self.header
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(self.l2vpn.vlans.all()), [self.vlans[0]])
        self.assertEqual(list(self.l2vpn.depends_on.all()), [self.dia])

    def test_patch_rejects_unknown_pk(self):
        self.add_permissions('netbox_services.change_service')
        response = self.client.patch(
            self.detail_url(self.l2vpn), {'vlans': [999999]}, format='json', **self.header
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_rejects_dependency_cycle(self):
        self.add_permissions('netbox_services.change_service')
        response = self.client.patch(
            self.detail_url(self.dia), {'depends_on': [self.l2vpn.pk]}, format='json', **self.header
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.dia.depends_on.exists())


class ServicePartiesAPITestCase(APITestCase):
    model = Service

    @classmethod
    def setUpTestData(cls):
        cls.acme = Tenant.objects.create(name='Acme', slug='acme')
        cls.globex = Tenant.objects.create(name='Globex', slug='globex')
        cls.service = Service.objects.create(service_id='L2-1', type='l2vpn', tenant=cls.acme)
        cls.service.tenants.set([cls.acme, cls.globex])

    def test_parties_exposed_in_detail(self):
        self.add_permissions('netbox_services.view_service')
        url = reverse('plugins-api:netbox_services-api:service-detail', kwargs={'pk': self.service.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data['tenants']), sorted([self.acme.pk, self.globex.pk]))

    def test_filter_by_party(self):
        self.add_permissions('netbox_services.view_service')
        url = reverse('plugins-api:netbox_services-api:service-list')
        response = self.client.get(url, {'tenants': 'globex'}, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_patch_sets_parties(self):
        self.add_permissions('netbox_services.change_service')
        url = reverse('plugins-api:netbox_services-api:service-detail', kwargs={'pk': self.service.pk})
        response = self.client.patch(url, {'tenants': [self.globex.pk]}, format='json', **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(self.service.tenants.all()), [self.globex])
