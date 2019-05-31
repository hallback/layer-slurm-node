from os import chmod
from socket import gethostname

from charms.slurm.helpers import MUNGE_SERVICE
from charms.slurm.helpers import MUNGE_KEY_PATH
from charms.slurm.helpers import SLURMD_SERVICE
from charms.slurm.helpers import SLURM_CONFIG_PATH
from charms.slurm.helpers import SLURMCTLD_SERVICE
from charms.slurm.helpers import create_spool_dir
from charms.slurm.helpers import render_munge_key
from charms.slurm.helpers import render_slurm_config

from charmhelpers.core.host import service_stop
from charmhelpers.core.host import service_pause
from charmhelpers.core.host import service_start
from charmhelpers.core.host import service_restart
from charmhelpers.core.host import service_running
from charmhelpers.core.hookenv import config
from charmhelpers.core.hookenv import status_set
from charmhelpers.core.hookenv import storage_get
from charmhelpers.core.hookenv import log

from charms.slurm.node import get_inventory

import charms.reactive as reactive
import charms.reactive.flags as flags


flags.register_trigger(when='endpoint.slurm-cluster.active.changed',
                       clear_flag='slurm-node.configured')


@reactive.only_once()
@reactive.when('slurm.installed')
def initial_setup():
    status_set('maintenance', 'Initial setup of slurm-node')
    # Disable slurmctld on node
    service_pause(SLURMCTLD_SERVICE)


@reactive.when_not('endpoint.slurm-cluster.joined')
def missing_controller():
    status_set('blocked', 'Missing a relation to slurm-controller')
    # Stop slurmd
    service_stop(SLURMD_SERVICE)

    for f in ['slurm-node.configured', 'slurm-node.info.sent']:
        flags.clear_flag(f)
        log('Cleared {} flag'.format(f))


@reactive.when('endpoint.slurm-cluster.joined')
@reactive.when_not('slurm-node.info.sent')
def send_node_info(cluster_endpoint):
    cluster_endpoint.send_node_info(hostname=gethostname(),
                                    partition=config('partition'),
                                    default=config('default'),
                                    inventory=get_inventory())
    flags.set_flag('slurm-node.info.sent')
    log('Set {} flag'.format('slurm-node.info.sent'))


@reactive.when('endpoint.slurm-cluster.active.available')
@reactive.when('endpoint.slurm-cluster.active.changed')
@reactive.when_not('slurm-node.configured')
def configure_node(cluster_changed, cluster_joined):
    status_set('maintenance', 'Configuring slurm-node')

    controller_data = cluster_changed.active_data
    create_spool_dir(context=controller_data)

    render_munge_key(context=controller_data)
    # If the munge.key has been changed on the controller and munge is
    # running, the service must be restarted to use the new key
    if flags.is_flag_set('endpoint.slurm-cluster.changed.munge_key') and service_running(MUNGE_SERVICE):
        log('Restarting munge due to key change on slurm-controller')
        service_restart(MUNGE_SERVICE)

    render_slurm_config(context=controller_data)

    # Make sure munge is running
    if not service_running(MUNGE_SERVICE):
        service_start(MUNGE_SERVICE)
    # Make sure slurmd is running, or restarted if running
    if not service_running(SLURMD_SERVICE):
        service_start(SLURMD_SERVICE)
    else:
        service_restart(SLURMD_SERVICE)

    flags.set_flag('slurm-node.configured')
    log('Set {} flag'.format('slurm-node.configured'))

    flags.clear_flag('endpoint.slurm-cluster.active.changed')
    log('Cleared {} flag'.format('endpoint.slurm-cluster.active.changed'))

    # Clear this flag to be able to signal munge_key changed if it occurs from
    # a controller.
    flags.clear_flag('endpoint.slurm-cluster.changed.munge_key')
    log('Cleared {} flag'.format('endpoint.slurm-cluster.changed.munge_key'))


@reactive.when('endpoint.slurm-cluster.joined', 'slurm-node.configured')
def node_ready(cluster_endpoint):
    status_set('active', 'Ready')


@reactive.when_not('endpoint.slurm-cluster.active.available')
def controller_gone():
    service_stop(MUNGE_SERVICE)
    service_stop(SLURMD_SERVICE)
    for f in ['slurm-node.configured', 'slurm-node.info.sent']:
        flags.clear_flag(f)
        log('Cleared {} flag'.format(f))


@reactive.hook('config-changed')
def config_changed():
    for f in ['slurm-node.configured', 'slurm-node.info.sent']:
        flags.clear_flag(f)
        log('Cleared {} flag'.format(f))


@reactive.hook('scratch-storage-attached')
def setup_storage():
    storage = storage_get()
    chmod(path=storage.get('location'), mode=0o777)


@reactive.when_file_changed(SLURM_CONFIG_PATH)
def restart_on_slurm_change():
    log('Restarting slurmd due to changed configuration on disk (%s)' % SLURM_CONFIG_PATH)
    service_restart(SLURMD_SERVICE)


@reactive.when_file_changed(MUNGE_KEY_PATH)
def restart_on_munge_change():
    log('Restarting munge due to changed munge key on disk (%s)' % MUNGE_KEY_PATH)
    service_restart(MUNGE_SERVICE)
