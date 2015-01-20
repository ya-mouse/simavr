#!/usr/bin/python3.4dm
#
# SIMAVR main executable
#
# Copyright (c) 2014 Anton D. Kachalov <mouse@yandex.ru>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.
#
import os
import sys
import platform
import threading
from importlib import machinery

qb_system=platform.system().lower()
qb_machine=platform.machine()
qb_pyversion=platform.python_version().rsplit('.',1)[0]
sys.path.append('build/lib.{}-{}-{}-pydebug'.format(qb_system, qb_machine, qb_pyversion))
#sys.path.append('{}/build/lib.{}-{}-{}-pydebug'.format('/home/mouse/SW/qbee/cython', qb_system, qb_machine, qb_pyversion))

import qb

print('Starting SIMAVR...')

# Start RPC dom0 server
global dom0
dom0 = qb.rpc.qb_dom0_server() #port=18813)

t = threading.Thread(target = dom0.start)
t.setDaemon(True)
t.start()

sys.ps1 = 'avr0> '

# Load & run python script
if len(sys.argv) > 1:
    machinery.SourceFileLoader(os.path.basename(sys.argv[1]), sys.argv[1]).load_module()

# Enter to interactive main
qb.console.interact(banner='SIMAVR interactive shell\n', context=globals())
