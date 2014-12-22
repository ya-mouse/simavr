# _simavr.pyx
# cython: language_level=3
#
# Simple bindings to SIMAVR
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
from qb._core cimport qb_object_t, qb_interface_t

cdef extern from "sim_avr.h":
    ctypedef struct avr_t:
        char *mmcu

    cdef avr_t * avr_make_mcu_by_name(const char * name)

cdef class avr_cpu(qb_object_t):
    cdef avr_t *_cpu

    def __init__(self, name, mmcu):
        super().__init__(name)
        self._cpu = avr_make_mcu_by_name(bytes(mmcu, 'ascii'))

    @property
    def mmcu(self):
        return str(self._cpu.mmcu, 'ascii')
