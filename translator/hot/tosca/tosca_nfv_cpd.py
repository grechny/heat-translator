#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from translator.hot.syntax.hot_resource import HotResource

# Name used to dynamically load appropriate map class.
TARGET_CLASS_NAME = 'ToscaNfvCpd'
TOSCA_LINKS_TO = 'tosca.relationships.nfv.VirtualLinksTo'
TOSCA_BINDS_TO = 'tosca.relationships.nfv.VirtualBindsTo'


class ToscaNfvCpd(HotResource):
    '''Translate TOSCA node type tosca.nodes.nfv.Cpd.'''

    toscatype = 'tosca.nodes.nfv.Cpd'

    def __init__(self, nodetemplate, csar_dir=None):
        super(ToscaNfvCpd, self).__init__(nodetemplate,
                                          type='OS::Neutron::Port',
                                          csar_dir=csar_dir)
        # Default order
        self.order = 0
        pass

    def _generate_networks_for_compute(self, port_resources):
        '''Generate compute networks property list from the port resources.'''
        networks = []
        for resource in port_resources:
            networks.append({'port': '{ get_resource: %s }' % (resource.name)})
        return networks

    def _insert_sorted_resource(self, resources, resource):
        '''Insert a resource in the list of resources and keep the order.'''
        lo = 0
        hi = len(resources)
        while lo < hi:
            mid = (lo + hi) // 2
            if resource.order < resources[mid].order:
                hi = mid
            else:
                lo = mid + 1
        resources.insert(lo, resource)

    def handle_properties(self):
        port_props = {}
        links_to = None
        binds_to = None

        for rel, node in self.nodetemplate.relationships.items():
            # Check for LinksTo relations. If found add a network property with
            # the network name into the port
            if not links_to and rel.is_derived_from(TOSCA_LINKS_TO):
                links_to = node

                network_resource = None
                for hot_resource in self.depends_on_nodes:
                    if links_to.name == hot_resource.name:
                        network_resource = hot_resource
                        self.depends_on.remove(hot_resource)
                        break

                if (network_resource is not None) and \
                        network_resource.existing_resource_id:
                    port_props['network'] =\
                        str(network_resource.existing_resource_id)
                else:
                    port_props['network'] = '{ get_resource: %s }'\
                        % (links_to.name)

            # Check for BindsTo relationship. If found add network to the
            # network property of the corresponding compute resource
            elif not binds_to and rel.is_derived_from(TOSCA_BINDS_TO):
                binds_to = node
                compute_resource = None
                for hot_resource in self.depends_on_nodes:
                    if binds_to.name == hot_resource.name:
                        compute_resource = hot_resource
                        self.depends_on.remove(hot_resource)
                        break
                if compute_resource:
                    port_rsrcs = compute_resource.assoc_port_resources
                    self._insert_sorted_resource(port_rsrcs, self)
                    # TODO(sdmonov): Using generate networks every time we add
                    # a network is not the fastest way to do the things. We
                    # should do this only once at the end.
                    networks = self._generate_networks_for_compute(port_rsrcs)
                    compute_resource.properties['networks'] = networks

        # todo: get network name from an input payload
        if not port_props.get('network'):
            properties = self.get_tosca_props()
            port_props['network'] = properties.get('network_name')

        self.properties = port_props
