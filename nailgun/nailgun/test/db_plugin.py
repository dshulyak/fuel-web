#    Copyright 2014 Mirantis, Inc.
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

import multiprocessing

from nose2 import events
from nose2.plugins import mp


class MultiProcessWithIdentity(mp.MultiProcess):

    configSection = 'multiprocess'

    def _startProcs(self):
        # XXX create session export
        session_export = self._exportSession()
        procs = []
        for i in range(0, self.procs):
            session_export['slaveid'] = str(i)
            parent_conn, child_conn = multiprocessing.Pipe()
            proc = multiprocessing.Process(
                target=mp.procserver, args=(session_export, child_conn))
            proc.daemon = True
            proc.start()
            procs.append((proc, parent_conn))
        return procs


class DbPlugin(events.Plugin):

    configSection = 'db'

    def registerInSubprocess(self, event):
        event.pluginClasses.append(self.__class__)

    def start_subprocess(self, event):
        pass
