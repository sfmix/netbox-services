from rest_framework import serializers

from dcim.models import Cable, Device, Interface
from ipam.models import ASN, VLAN, VRF, Prefix, RouteTarget
from netbox.api.serializers import NetBoxModelSerializer
from netbox_services.models import Service
from virtualization.models import VirtualMachine
from vpn.models import L2VPN, Tunnel


def related(model):
    """Writable list of primary keys for one of Service's related-object M2M fields."""
    return serializers.PrimaryKeyRelatedField(many=True, required=False, queryset=model.objects.all())


class ServiceSerializer(NetBoxModelSerializer):

    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_services-api:service-detail'
    )
    devices = related(Device)
    interfaces = related(Interface)
    cables = related(Cable)
    vlans = related(VLAN)
    prefixes = related(Prefix)
    vrfs = related(VRF)
    asns = related(ASN)
    route_targets = related(RouteTarget)
    l2vpns = related(L2VPN)
    tunnels = related(Tunnel)
    virtual_machines = related(VirtualMachine)
    depends_on = related(Service)
    dependents = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Service
        fields = (
            'id',
            'url',
            'type',
            'service_id',
            'description',
            'status',
            'bandwidth',
            'cir',
            'sla_uptime_percent',
            'tenant',
            'order_date',
            'planned_activation',
            'installed',
            'contract_start',
            'contract_end',
            'requested_disconnect',
            'decommissioned',
            'decommission_reason',
            'devices',
            'interfaces',
            'cables',
            'vlans',
            'prefixes',
            'vrfs',
            'asns',
            'route_targets',
            'l2vpns',
            'tunnels',
            'virtual_machines',
            'depends_on',
            'dependents',
            'tags',
            'custom_fields',
            'created',
            'last_updated',
        )
