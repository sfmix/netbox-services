from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_services', '0006_service_tags_use_netbox_tags'),
        ('tenancy', '0020_remove_contactgroupmembership'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='tenants',
            field=models.ManyToManyField(blank=True, related_name='party_services', to='tenancy.tenant'),
        ),
    ]
