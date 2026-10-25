from importlib import import_module

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from taggit.models import Tag as TaggitTag, TaggedItem as TaggitTaggedItem

from extras.models import Tag
from utilities.testing import APITestCase

from netbox_services.models import Service

move_taggit_tags = import_module(
    'netbox_services.migrations.0006_service_tags_use_netbox_tags'
).move_taggit_tags


class ServiceTagsTestCase(TestCase):

    def test_tags_are_netbox_tags(self):
        tag = Tag.objects.create(name='Gold', slug='gold')
        service = Service.objects.create(service_id='NW-1', type='dia')
        service.tags.add(tag)
        self.assertEqual(list(Service.objects.filter(tags__slug='gold')), [service])
        self.assertIsInstance(service.tags.first(), Tag)
        self.assertFalse(TaggitTag.objects.exists())

    def test_migration_moves_taggit_tags_to_netbox_tags(self):
        existing = Tag.objects.create(name='Gold', slug='gold')
        service = Service.objects.create(service_id='NW-1', type='dia')
        content_type = ContentType.objects.get_for_model(Service)
        for name, slug in (('Gold', 'gold'), ('Silver', 'silver')):
            TaggitTaggedItem.objects.create(
                content_type=content_type, object_id=service.pk,
                tag=TaggitTag.objects.create(name=name, slug=slug),
            )

        move_taggit_tags(apps, None)

        self.assertEqual(
            sorted(service.tags.values_list('slug', flat=True)), ['gold', 'silver']
        )
        self.assertIn(existing, service.tags.all())
        self.assertFalse(TaggitTaggedItem.objects.filter(content_type=content_type).exists())


class ServiceTagsAPITestCase(APITestCase):
    model = Service

    @classmethod
    def setUpTestData(cls):
        cls.tag = Tag.objects.create(name='Gold', slug='gold')

    def test_create_and_list_tagged_service(self):
        self.add_permissions('netbox_services.add_service', 'netbox_services.view_service', 'extras.view_tag')
        url = reverse('plugins-api:netbox_services-api:service-list')
        data = {'type': 'dia', 'service_id': 'NW-1', 'tags': [{'slug': 'gold'}]}
        response = self.client.post(url, data, format='json', **self.header)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual([t['slug'] for t in response.data['tags']], ['gold'])

        response = self.client.get(url, {'tag': 'gold'}, **self.header)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
