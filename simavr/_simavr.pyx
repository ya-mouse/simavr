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

cdef extern from "sim_irq.h":
    ctypedef struct avr_irq_t
    ctypedef struct avr_irq_hook_t

    ctypedef struct avr_irq_pool_t:
        int count
        avr_irq_t ** irq

    ctypedef struct avr_irq_t:
        avr_irq_pool_t *pool
        const char * name
        uint32_t     irq
        uint32_t     value
        uint8_t      flags
        avr_irq_hook_t * hook

    cdef avr_irq_t *avr_alloc_irq(
                avr_irq_pool_t * pool,
                uint32_t base,
                uint32_t count,
                const char ** names) nogil

    cdef void avr_raise_irq(
                avr_irq_t * irq,
                uint32_t value) nogil

cdef extern from "sim_avr.h":
    ctypedef uint64_t avr_cycle_count_t
    ctypedef uint16_t avr_io_addr_t
    ctypedef uint32_t avr_flashaddr_t

    ctypedef void (*avr_run_t)(avr_t * avr)

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
        avr_cycle_count_t	run_cycle_count
        avr_cycle_count_t	run_cycle_limit

        uint32_t sleep_usec

        void (*init)(avr_t * avr)
        void (*special_init)(avr_t * avr, void * data)
        void (*special_deinit)(avr_t * avr, void * data)
        void *special_data
        void (*reset)(avr_t * avr)
        avr_run_t	run

        void (*sleep)(avr_t * avr, avr_cycle_count_t howLong)

        avr_irq_pool_t	irq_pool
        uint8_t		sreg[8]
        int8_t		interrupt_state

        avr_flashaddr_t	pc

    cdef avr_t * avr_make_mcu_by_name(const char * name) nogil
    cdef void avr_init(avr_t *avr) nogil

    cdef int avr_run(avr_t *avr) nogil
    cdef void avr_terminate(avr_t *avr) nogil

cdef extern from "sim_elf.h":
    ctypedef struct elf_firmware_t:
        char mmcu[64]
        int freq

    cdef void avr_load_firmware(avr_t *avr, elf_firmware_t *elf)
    cdef int elf_read_firmware(const char *filename, elf_firmware_t *elf)

cdef extern from "sim_cycle_timers.h":
    ctypedef avr_cycle_count_t (*avr_cycle_timer_t)(avr_t * avr,
                avr_cycle_count_t when,
                void * param)

    cdef void avr_cycle_timer_register(avr_t * avr,
                avr_cycle_count_t when,
                avr_cycle_timer_t timer,
                void * param)

    cdef void avr_cycle_timer_register_usec(avr_t * avr,
                uint32_t when,
                avr_cycle_timer_t timer,
                void * param)

    cdef void avr_cycle_timer_cancel(avr_t * avr,
                avr_cycle_timer_t timer,
                void * param)

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
    def state(self):
        return self._core.state

    @property
    def mmcu(self):
        return str(self._core.mmcu, 'ascii')

    cdef avr_irq_t * alloc_irq(self, int base, int count):
        cdef char *name = "button"
        return avr_alloc_irq(&self._core.irq_pool, base, count, &name)


cdef class sim_button:
    cdef avr_irq_t * _irq
    cdef avr_core _avr

    def __init__(self, avr_core avr, name):
        self._avr = avr
        self._irq = self._avr.alloc_irq(0, 1)

    @staticmethod
    cdef avr_cycle_count_t _auto_release(avr_t *avr, avr_cycle_count_t when, void *param) with gil:
        cdef sim_button p = <sim_button>param
        avr_raise_irq(p._irq + 0, 1)
        print('button_auto_release', avr.state)
        return 0

    def press(self, duration):
        avr_cycle_timer_cancel(self._avr._core, sim_button._auto_release, <void *>self)
        avr_raise_irq(self._irq + 0, 0)
        avr_cycle_timer_register_usec(self._avr._core, duration, sim_button._auto_release, <void *>self)
