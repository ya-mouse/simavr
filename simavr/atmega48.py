import qb
import qb._simavr

qb.root.o.atmega = qb._simavr.avr_core(None, 'atmega48')
qb.root.o.atmega.load_firmware(b'atmega48_ledramp.axf')
