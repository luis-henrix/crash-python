#!/usr/bin/env python

from __future__ import print_function

from crash.types.list import list_for_each_entry
from crash.commands import CrashCommand, CrashCommandParser

import gdb
import socket
import struct

class CephMaps(CrashCommand):
    """
    doc
    """
    __types__ = [ 'struct super_block', 'struct ceph_fs_client *', 'struct sockaddr_in' ]
    __symvals__ = [ 'super_blocks' ]
    def __init__(self):
        self.name = "cephmaps"
        CrashCommand.__init__(self, self.name, None)

    def get_entity_name(self, n):
        types_map = {
            0x1: "mon",
            0x2: "mds",
            0x4: "osd",
            0x8: "client",
            0x20: "auth"
        }
        num = n['num']
        t = int(n['type'])
        if t in types_map:
            return "{}{}".format(types_map[t], num)
        return "unknown"

    def get_entity_address(self, addr):
        in_addr = addr['in_addr']
        family = in_addr['ss_family']
        if family == socket.AF_INET:
            in4 = (in_addr).cast(self.sockaddr_in_type)
            ip = socket.ntohl(long(in4['sin_addr']['s_addr']))
            port = socket.ntohs(long(in4['sin_port']))
            return "{}:{}".format(socket.inet_ntoa(struct.pack('!L', ip)), port)
        elif family == socket.AF_INET6:
            return "AF_INET6" # XXX
        return "(unknown sockaddr family {}".format(family)

    def get_subs_name(self, id):
        subs_map = {
            0: "monmap",
            1: "osdmap",
            2: "fsmap.user",
            3: "mdsmap"
        }
        if id in subs_map:
            return subs_map[id]
        return "(unknown)"

    def show_ceph_monmap(self, fs_client):
        mon_client = fs_client['client']['monc']
        monmap = mon_client['monmap']
        num_mons = int(monmap['num_mon'])
        entities = monmap['mon_inst']

        # monmap
        print("epoch {}".format(monmap['epoch']))
        for m in range(num_mons):
            name = self.get_entity_name(entities[m]['name'])
            addr = self.get_entity_address(entities[m]['addr'])
            print("\t{} {}".format(name, addr))
        print("")

        # monc
        for i in range(4):
            name = self.get_subs_name(i)
            have = mon_client['subs'][i]['have']
            if mon_client['subs'][i]['want']:
                start = mon_client['subs'][i]['item']['start']
                if (mon_client['subs'][i]['item']['flags'] & 1): # CEPH_SUBSCRIBE_ONETIME
                    flags = "+"
                else:
                    flags = ""
                want = " want {}{}".format(start, flags)
            else:
                want = "" #mon_client['subs'][i]['have']
            print("have {} {}{}".format(name, have, want))
        print("fs_cluster_id {}".format(mon_client['fs_cluster_id']))

    def execute(self, args):
        for sb in list_for_each_entry(self.super_blocks, self.super_block_type, 's_list'):
            if (sb['s_type']['name'].string()) == 'ceph':
                fs_client = gdb.Value(sb['s_fs_info']).cast(self.ceph_fs_client_p_type)
                self.show_ceph_monmap(fs_client)

CephMaps()
