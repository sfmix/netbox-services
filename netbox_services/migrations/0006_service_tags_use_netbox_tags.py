import taggit.managers
from django.db import migrations
from django.utils.text import slugify


def move_taggit_tags(apps, schema_editor):
    """
    Service.tags used taggit's own Tag/TaggedItem tables instead of NetBox's, so tags assigned
    so far live in taggit_tag. Re-point each assignment at the NetBox tag with the same slug or
    name (creating it if needed) and drop the taggit-side rows.
    """
    ContentType = apps.get_model('contenttypes', 'ContentType')
    TaggitTaggedItem = apps.get_model('taggit', 'TaggedItem')
    Tag = apps.get_model('extras', 'Tag')
    TaggedItem = apps.get_model('extras', 'TaggedItem')

    content_type = ContentType.objects.filter(app_label='netbox_services', model='service').first()
    if content_type is None:
        return
    old_items = TaggitTaggedItem.objects.filter(content_type=content_type).select_related('tag')
    for item in old_items:
        tag = (
            Tag.objects.filter(slug=item.tag.slug).first()
            or Tag.objects.filter(name=item.tag.name).first()
            or Tag.objects.create(name=item.tag.name, slug=item.tag.slug or slugify(item.tag.name))
        )
        TaggedItem.objects.get_or_create(content_type=content_type, object_id=item.object_id, tag=tag)
    old_items.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('extras', '0125_alter_tag_options_tag_weight'),
        ('netbox_services', '0005_service_bandwidth_cir_sla_decommission_reason'),
        ('taggit', '0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx'),
    ]

    operations = [
        # Neither field has a column, so swapping them changes no schema
        migrations.RemoveField(
            model_name='service',
            name='tags',
        ),
        migrations.AddField(
            model_name='service',
            name='tags',
            field=taggit.managers.TaggableManager(through='extras.TaggedItem', to='extras.Tag'),
        ),
        migrations.RunPython(move_taggit_tags, migrations.RunPython.noop),
    ]
