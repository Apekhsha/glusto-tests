#  Copyright (C) 2015-2016  Red Hat, Inc. <http://www.redhat.com>
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

""" Description: Module for gluster brick operations """

from glusto.core import Glusto as g


def add_brick(mnode, volname, bricks_list, force=False, **kwargs):
    """Add Bricks specified in the bricks_list to the volume.

    Args:
        mnode (str): None on which the commands are executed.
        volname (str): Name of the volume
        bricks_list (list): List of bricks to be added

    Kwargs:
        force (bool): If this option is set to True, then add brick command
            will get executed with force option. If it is set to False,
            then add brick command will get executed without force option

        **kwargs
            The keys, values in kwargs are:
                - replica_count : (int)|None
                - arbiter_count : (int)|None

    Returns:
        tuple: Tuple containing three elements (ret, out, err).
            The first element 'ret' is of type 'int' and is the return value
            of command execution.

            The second element 'out' is of type 'str' and is the stdout value
            of the command execution.

            The third element 'err' is of type 'str' and is the stderr value
            of the command execution.
    """
    replica_count = arbiter_count = None

    if 'replica_count' in kwargs:
        replica_count = int(kwargs['replica_count'])

        if 'arbiter_count' in kwargs:
            arbiter_count = int(kwargs['arbiter_count'])

    replica = arbiter = ''

    if replica_count is not None:
        replica = "replica %d" % replica_count

        if arbiter_count is not None:
            arbiter = "arbiter %d" % arbiter_count

    force_value = ''
    if force:
        force_value = "force"

    cmd = ("gluster volume add-brick %s %s %s %s %s" %
           (volname, replica, arbiter, ' '.join(bricks_list), force_value))

    return g.run(mnode, cmd)


def remove_brick(mnode, volname, bricks_list, option, replica=None):
    """Remove bricks specified in the bricks_list from the volume.

    Args:
        mnode (str): None on which the commands are executed.
        volname (str): Name of the volume
        bricks_list (list): List of bricks to be removed
        option (str): Remove brick options: <start|stop|status|commit|force>

    Kwargs:
        replica (int): Replica count to increase the replica count of
            the volume.

    Returns:
        tuple: Tuple containing three elements (ret, out, err).
            The first element 'ret' is of type 'int' and is the return value
            of command execution.

            The second element 'out' is of type 'str' and is the stdout value
            of the command execution.

            The third element 'err' is of type 'str' and is the stderr value
            of the command execution.
    """
    if option == "commit" or option == "force":
        option = option + " --mode=script"

    if replica is None:
        cmd = ("gluster volume remove-brick %s %s %s" %
               (volname, ' '.join(bricks_list), option))
    else:
        cmd = ("gluster volume remove-brick %s replica %d %s force "
               "--mode=script" % (volname, int(replica),
                                  ' '.join(bricks_list)))

    return g.run(mnode, cmd)


def replace_brick(mnode, volname, src_brick, dst_brick):
    """Replace src brick with dst brick from the volume.

    Args:
        mnode (str): None on which the commands are executed.
        volname (str): Name of the volume
        src_brick (str): Source brick name
        dst_brick (str): Destination brick name

    Returns:
        tuple: Tuple containing three elements (ret, out, err).
            The first element 'ret' is of type 'int' and is the return value
            of command execution.

            The second element 'out' is of type 'str' and is the stdout value
            of the command execution.

            The third element 'err' is of type 'str' and is the stderr value
            of the command execution.
    """
    cmd = ("gluster volume replace-brick %s %s %s commit force" %
           (volname, src_brick, dst_brick))
    return g.run(mnode, cmd)
