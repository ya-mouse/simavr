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
import threading
from libc.stdint cimport *
from libc.string cimport strcpy
from qb._core cimport qb_object_t, qb_interface_t

cdef extern from "sim_avr.h":
    ctypedef uint64_t avr_cycle_count_t
    ctypedef uint16_t avr_io_addr_t

    ctypedef struct avr_t:
        char *mmcu
        uint16_t ramend
        uint32_t flashed
        uint32_t e2end;
        uint8_t  vector_size
        uint8_t  signature[3]
        uint8_t  fuse[4]
        avr_io_addr_t rampz
        avr_io_addr_t eind
        uint8_t address_size
        uint32_t codeend
        int state
        uint32_t frequency
        uint32_t vcc,avcc,aref
        avr_cycle_count_t cycle

    cdef avr_t * avr_make_mcu_by_name(const char * name)
    cdef void avr_init(avr_t *core)

    cdef int avr_run(avr_t *core) nogil
    cdef void avr_terminate(avr_t *core)

cdef extern from "sim_elf.h":
    ctypedef struct elf_firmware_t:
        char mmcu[64]
        int freq

    cdef void avr_load_firmware(avr_t *core, elf_firmware_t *elf)
    cdef int elf_read_firmware(const char *filename, elf_firmware_t *elf)

cdef class avr_core(qb_object_t):
    cdef avr_t *_core
    cdef elf_firmware_t _elf
    cdef object _t
    cdef int paused

    def __init__(self, name, mmcu):
        super().__init__(name)
        self._t = None
        self._core = avr_make_mcu_by_name(bytes(mmcu, 'ascii'))
        if self._core == NULL:
            raise Exception("AVR '{}' not known".format(mmcu))

        strcpy(self._elf.mmcu, self._core.mmcu)
        avr_init(self._core)

    def load_firmware(self, filename):
        if elf_read_firmware(filename, &self._elf) == -1:
             raise Exception("Unable to load firmware from file {}".format(filename))

        avr_load_firmware(self._core, &self._elf)

    def _cpu_step(self):
        with nogil:
            while avr_run(self._core) not in (1, 6, 7):
                pass
        print('DONE ({})'.format(self._core.cycle))

    def start(self):
        if self._core.state == 1:
            self._core.state = 2
        self._t = threading.Thread(target = self._cpu_step)
        self._t.setDaemon(True)
        self._t.start()

    def stop(self):
        self._core.state = 1
        if self._t is not None:
            self._t.join()

    def __del__(self):
        avr_terminate(self._core)

    @property
    def mmcu(self):
        return str(self._core.mmcu, 'ascii')
