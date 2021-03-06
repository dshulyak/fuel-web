# -*- coding: utf-8 -*-

#    Copyright 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time

from nailgun.keepalive.watcher import KeepAliveThread
from nailgun.test.base import BaseIntegrationTest


class TestKeepalive(BaseIntegrationTest):

    def setUp(self):
        super(TestKeepalive, self).setUp()
        self.watcher = KeepAliveThread(
            interval=2,
            timeout=1
        )
        self.watcher.start()
        self.timeout = self.watcher.interval + 10

    def tearDown(self):
        self.watcher.join()
        super(TestKeepalive, self).tearDown()

    def check_online(self, node, online):
        self.env.refresh_nodes()
        return node.online == online

    def test_node_becomes_offline(self):
        node = self.env.create_node(status="discover",
                                    roles=["controller"],
                                    name="Dead or alive")

        self.assertEquals(node.online, True)
        self.env.wait_for_true(
            self.check_online,
            args=[node, False],
            timeout=self.timeout)

    def test_provisioning_node_not_becomes_offline(self):
        node = self.env.create_node(status="provisioning",
                                    roles=["controller"],
                                    name="Dead or alive")

        time.sleep(self.watcher.interval + 2)
        self.env.refresh_nodes()
        self.assertEqual(node.online, True)
