#  Copyright (C) 2016 Red Hat, Inc. <http://www.redhat.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
"""
    Description: Module containing GlusterBaseClass which defines all the
        variables necessary for tests.
"""

import unittest
import os
import random
import time
import copy
from glusto.core import Glusto as g
from glustolibs.gluster.exceptions import ExecutionError, ConfigError
from glustolibs.gluster.peer_ops import is_peer_connected, peer_status
from glustolibs.gluster.volume_ops import volume_info
from glustolibs.gluster.volume_libs import (setup_volume, cleanup_volume,
                                            log_volume_info_and_status)
from glustolibs.gluster.samba_libs import share_volume_over_smb
from glustolibs.gluster.nfs_libs import export_volume_through_nfs
from glustolibs.gluster.mount_ops import create_mount_objs
from glustolibs.io.utils import log_mounts_info


class runs_on(g.CarteTestClass):
    """Decorator providing runs_on capability for standard unittest script"""

    def __init__(self, value):
        # the names of the class attributes set by the runs_on decorator
        self.axis_names = ['volume_type', 'mount_type']

        # the options to replace 'ALL' in selections
        self.available_options = [['distributed', 'replicated',
                                   'distributed-replicated',
                                   'dispersed', 'distributed-dispersed'],
                                  ['glusterfs', 'nfs', 'cifs', 'smb']]

        # these are the volume and mount options to run and set in config
        # what do runs_on_volumes and runs_on_mounts need to be named????
        run_on_volumes = g.config.get('running_on_volumes',
                                      self.available_options[0])
        run_on_mounts = g.config.get('running_on_mounts',
                                     self.available_options[1])

        # selections is the above info from the run that is intersected with
        # the limits from the test script
        self.selections = [run_on_volumes, run_on_mounts]

        # value is the limits that are passed in by the decorator
        self.limits = value


class GlusterBaseClass(unittest.TestCase):
    """GlusterBaseClass to be subclassed by Gluster Tests.
    This class reads the config for variable values that will be used in
    gluster tests. If variable values are not specified in the config file,
    the variable are defaulted to specific values.
    """
    # these will be populated by either the runs_on decorator or
    # defaults in setUpClass()
    volume_type = None
    mount_type = None

    @classmethod
    def setUpClass(cls):
        """Initialize all the variables necessary for testing Gluster
        """
        g.log.info("Setting up class: %s", cls.__name__)

        # Get all servers
        cls.all_servers = None
        if 'servers' in g.config and g.config['servers']:
            cls.all_servers = g.config['servers']
            cls.servers = cls.all_servers
        else:
            raise ConfigError("'servers' not defined in the global config")

        # Get all clients
        cls.all_clients = None
        if 'clients' in g.config and g.config['clients']:
            cls.all_clients = g.config['clients']
            cls.clients = cls.all_clients
        else:
            raise ConfigError("'clients' not defined in the global config")

        # Get all servers info
        cls.all_servers_info = None
        if 'servers_info' in g.config and g.config['servers_info']:
            cls.all_servers_info = g.config['servers_info']
        else:
            raise ConfigError("'servers_info' not defined in the global "
                              "config")

        # All clients_info
        cls.all_clients_info = None
        if 'clients_info' in g.config and g.config['clients_info']:
            cls.all_clients_info = g.config['clients_info']
        else:
            raise ConfigError("'clients_info' not defined in the global "
                              "config")

        # Set mnode : Node on which gluster commands are executed
        cls.mnode = cls.all_servers[0]

        # SMB Cluster info
        try:
            cls.smb_users_info = (
                g.config['gluster']['cluster_config']['smb']['users_info'])
        except KeyError:
            cls.smb_users_info = {}
            cls.smb_users_info['root'] = {}
            cls.smb_users_info['root']['password'] = 'foobar'
            cls.smb_users_info['root']['acl'] = 'rwx'

        # NFS-Ganesha Cluster Info
        try:
            cls.enable_nfs_ganesha = bool(g.config['gluster']['cluster_config']
                                          ['nfs_ganesha']['enable'])
        except KeyError:
            cls.enable_nfs_ganesha = False

        # Defining default volume_types configuration.
        default_volume_type_config = {
            'replicated': {
                'type': 'replicated',
                'replica_count': 3,
                'transport': 'tcp'
                },
            'dispersed': {
                'type': 'dispersed',
                'disperse_count': 6,
                'redundancy_count': 2,
                'transport': 'tcp'
                },
            'distributed': {
                'type': 'distributed',
                'dist_count': 4,
                'transport': 'tcp'
                },
            'distributed-replicated': {
                'type': 'distributed-replicated',
                'dist_count': 2,
                'replica_count': 3,
                'transport': 'tcp'
                },
            'distributed-dispersed': {
                'type': 'distributed-dispersed',
                'dist_count': 2,
                'disperse_count': 6,
                'redundancy_count': 2,
                'transport': 'tcp'
                }
            }

        # Get the volume configuration.
        cls.volume = {}
        if cls.volume_type:
            found_volume = False
            if 'gluster' in g.config:
                if 'volumes' in g.config['gluster']:
                    for volume in g.config['gluster']['volumes']:
                        if volume['voltype']['type'] == cls.volume_type:
                            cls.volume = copy.deepcopy(volume)
                            found_volume = True
                            break

            if found_volume:
                if 'name' not in cls.volume:
                    cls.volume['name'] = 'testvol_%s' % cls.volume_type

                if 'servers' not in cls.volume:
                    cls.volume['servers'] = cls.all_servers

            if not found_volume:
                try:
                    if g.config['gluster']['volume_types'][cls.volume_type]:
                        cls.volume['voltype'] = (g.config['gluster']
                                                 ['volume_types']
                                                 [cls.volume_type])
                except KeyError:
                    try:
                        cls.volume['voltype'] = (default_volume_type_config
                                                 [cls.volume_type])
                    except KeyError:
                        raise ConfigError("Unable to get configs of volume "
                                          "type: %s", cls.volume_type)
                cls.volume['name'] = 'testvol_%s' % cls.volume_type
                cls.volume['servers'] = cls.all_servers

            # Set volume options
            if 'options' not in cls.volume:
                cls.volume['options'] = {}

            # Define Volume Useful Variables.
            cls.volname = cls.volume['name']
            cls.voltype = cls.volume['voltype']['type']
            cls.servers = cls.volume['servers']
            cls.mnode = cls.servers[0]
            cls.vol_options = cls.volume['options']

        # Get the mount configuration.
        cls.mounts = []
        if cls.mount_type:
            cls.mounts_dict_list = []
            found_mount = False
            if 'gluster' in g.config:
                if 'mounts' in g.config['gluster']:
                    for mount in g.config['gluster']['mounts']:
                        if mount['protocol'] == cls.mount_type:
                            temp_mount = {}
                            temp_mount['protocol'] = cls.mount_type
                            if 'volname' in mount and mount['volname']:
                                if mount['volname'] == cls.volname:
                                    temp_mount = copy.deepcopy(mount)
                                else:
                                    continue
                            else:
                                temp_mount['volname'] = cls.volname
                            if ('server' not in temp_mount or
                                    (not temp_mount['server'])):
                                temp_mount['server'] = cls.mnode
                            if ('mountpoint' not in temp_mount or
                                    (not temp_mount['mountpoint'])):
                                temp_mount['mountpoint'] = (os.path.join(
                                    "/mnt", '_'.join([cls.volname,
                                                      cls.mount_type])))
                            if ('client' not in temp_mount or
                                    (not temp_mount['client'])):
                                temp_mount['client'] = (
                                    cls.all_clients_info[
                                        random.choice(
                                            cls.all_clients_info.keys())]
                                    )
                            cls.mounts_dict_list.append(temp_mount)
                            found_mount = True
            if not found_mount:
                for client in cls.all_clients_info.keys():
                    mount = {
                        'protocol': cls.mount_type,
                        'server': cls.mnode,
                        'volname': cls.volname,
                        'client': cls.all_clients_info[client],
                        'mountpoint': (os.path.join(
                            "/mnt", '_'.join([cls.volname, cls.mount_type]))),
                        'options': ''
                        }
                    cls.mounts_dict_list.append(mount)

            if cls.mount_type == 'cifs' or cls.mount_type == 'smb':
                for mount in cls.mounts_dict_list:
                    if 'smbuser' not in mount:
                        mount['smbuser'] = random.choice(
                            cls.smb_users_info.keys())
                        mount['smbpasswd'] = (
                            cls.smb_users_info[mount['smbuser']]['password'])

            cls.mounts = create_mount_objs(cls.mounts_dict_list)

            # Defining clients from mounts.
            cls.clients = []
            for mount in cls.mounts_dict_list:
                cls.clients.append(mount['client']['host'])
            cls.clients = list(set(cls.clients))

        # Log the baseclass variables for debugging purposes
        g.log.debug("GlusterBaseClass Variables:\n %s", cls.__dict__)

    def setUp(self):
        g.log.info("Starting Test: %s", self.id())

    def tearDown(self):
        g.log.info("Ending Test: %s", self.id())

    @classmethod
    def tearDownClass(cls):
        g.log.info("Teardown class: %s", cls.__name__)


class GlusterVolumeBaseClass(GlusterBaseClass):
    """GlusterVolumeBaseClass sets up the volume for testing purposes.
    """
    @classmethod
    def setUpClass(cls):
        """Setup volume, shares/exports volume for cifs/nfs protocols,
            mounts the volume.
        """
        GlusterBaseClass.setUpClass.im_func(cls)

        # Validate if peer is connected from all the servers
        for server in cls.servers:
            ret = is_peer_connected(server, cls.servers)
            if not ret:
                raise ExecutionError("Validating Peers to be in Cluster "
                                     "Failed")
        g.log.info("All peers are in connected state")

        # Peer Status from mnode
        peer_status(cls.mnode)

        # Setup Volume
        ret = setup_volume(mnode=cls.mnode,
                           all_servers_info=cls.all_servers_info,
                           volume_config=cls.volume, force=True)
        if not ret:
            raise ExecutionError("Setup volume %s failed", cls.volname)
        time.sleep(10)

        # Export/Share the volume based on mount_type
        if cls.mount_type != "glusterfs":
            if "nfs" in cls.mount_type:
                ret = export_volume_through_nfs(
                    mnode=cls.mnode, volname=cls.volname,
                    enable_ganesha=cls.enable_nfs_ganesha)
                if not ret:
                    raise ExecutionError("Failed to export volume %s "
                                         "as NFS export", cls.volname)

            if "smb" in cls.mount_type or "cifs" in cls.mount_type:
                ret = share_volume_over_smb(mnode=cls.mnode,
                                            volname=cls.volname,
                                            smb_users_info=cls.smb_users_info)
                if not ret:
                    raise ExecutionError("Failed to export volume %s "
                                         "as SMB Share", cls.volname)

        # Log Volume Info and Status
        ret = log_volume_info_and_status(cls.mnode, cls.volname)
        if not ret:
            raise ExecutionError("Logging volume %s info and status failed",
                                 cls.volname)

        # Create Mounts
        _rc = True
        for mount_obj in cls.mounts:
            ret = mount_obj.mount()
            if not ret:
                g.log.error("Unable to mount volume '%s:%s' on '%s:%s'",
                            mount_obj.server_system, mount_obj.volname,
                            mount_obj.client_system, mount_obj.mountpoint)
                _rc = False
        if not _rc:
            raise ExecutionError("Mounting volume %s on few clients failed",
                                 cls.volname)

        # Get info of mount before the IO
        log_mounts_info(cls.mounts)

    @classmethod
    def tearDownClass(cls, umount_vol=True, cleanup_vol=True):
        """Teardown the mounts and volume.
        """
        GlusterBaseClass.tearDownClass.im_func(cls)

        # Unmount volume
        if umount_vol:
            _rc = True
            for mount_obj in cls.mounts:
                ret = mount_obj.unmount()
                if not ret:
                    g.log.error("Unable to unmount volume '%s:%s' on '%s:%s'",
                                mount_obj.server_system, mount_obj.volname,
                                mount_obj.client_system, mount_obj.mountpoint)
                    _rc = False
            if not _rc:
                raise ExecutionError("Unmount of all mounts are not "
                                     "successful")

        # Cleanup volume
        if cleanup_vol:
            ret = cleanup_volume(mnode=cls.mnode, volname=cls.volname)
            if not ret:
                raise ExecutionError("cleanup volume %s failed", cls.volname)

        # All Volume Info
        volume_info(cls.mnode)
