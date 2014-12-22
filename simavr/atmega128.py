import qb
import qb._simavr

qb.root.o.atmega = qb._simavr.avr_cpu(None, 'atmega128')
