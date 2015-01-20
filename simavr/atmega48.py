import qb
import simavr._avr
from time import sleep
from threading import Thread

from OpenGL.GLU import *
from OpenGL.GL import *
from lcd_glut import lcd_glut

class hd44780_lcd(qb.qb_object_t):
    _pinstate = 0
    _datapins = 0
    _readpins = 0
    _cursor = 0

    _vram = [32] * (80+64)

    _port = {
        'RS': 1, 'RW': 2, 'E': 3,
        'D0': 4, 'D1': 5, 'D2': 6, 'D3': 7,
        'D4': 8, 'D5': 9, 'D6': 10, 'D7': 11,
        'BUSY': 12, 'ADDR': 13, 'DATA_IN': 14, 'DATA_OUT': 15
    }

    _colors = (
        ( 0x00aa00ff, 0x00cc00ff, 0x000000ff, 0x00000055 ), # fluo green
        ( 0xaa0000ff, 0xcc0000ff, 0x000000ff, 0x00000055 ), # red
        ( 0x0000aaff, 0x0000ccff, 0x000000ff, 0x00000055 ), # blue
        ( 0xaaaaaaff, 0xccccccff, 0x000000ff, 0x00000055 ), # bw
    )
    _colorpal = 0

    HD44780_FLAG_REENTRANT = False
    HD44780_FLAG_BUSY = False
    HD44780_FLAG_DIRTY = False
    HD44780_FLAG_B = False
    HD44780_FLAG_C = False
    HD44780_FLAG_D = False
    HD44780_FLAG_D_L = False
    HD44780_FLAG_F = False
    HD44780_FLAG_I_D = False
    HD44780_FLAG_N = False
    HD44780_FLAG_S = False
    HD44780_FLAG_S_C = False
    HD44780_FLAG_R_L = False
    HD44780_FLAG_LOWNIBBLE = False

    class signal(simavr._avr.signal):
        def signal_lower(self):
            self._obj.pin_change(str(self._name, 'ascii'), 0)

        def signal_raise(self):
            self._obj.pin_change(str(self._name, 'ascii'), 1)

    def __init__(self, name, geom='20x4'):
        super().__init__(name)
        self._lcd = lcd_glut(self, geom, 3)
        self._font_init()
        self._reset_cursor()
        self._clear_screen()
        self._lcd.start()

    def _font_init(self):
        class FontTexture():
            def __init__(self):
                from lcd_glut import font
                self.xSize = 1280
                self.ySize = 7
                self.rawReference = font

        self._font_texture = glGenTextures(1)
        self._texture = FontTexture()
        glBindTexture(GL_TEXTURE_2D, self._font_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, 4,
                self._texture.xSize,
                self._texture.ySize, 0, GL_RGBA,
                GL_UNSIGNED_BYTE,
                self._texture.rawReference)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        glMatrixMode(GL_TEXTURE)
        glLoadIdentity()
        glScalef(1.0 / self._texture.xSize, 1.0 / self._texture.ySize, 1.0)

        glMatrixMode(GL_MODELVIEW)

    def draw(self):
        border = 3
        charwidth = 5
        charheight = 7

        def glColor32U(color):
            glColor4f(
                ((color >> 24) & 0xff) / 255.0,
                ((color >> 16) & 0xff) / 255.0,
                ((color >> 8) & 0xff) / 255.0,
                ((color) & 0xff) / 255.0)

        def glputchar(c, character, text, shadow):
            index = c
            left = index * charwidth
            right = index * charwidth + charwidth
            top = 0
            bottom = 7

            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            glDisable(GL_TEXTURE_2D)
            glColor32U(character)
            glBegin(GL_QUADS)
            glVertex3i(5, 7, 0)
            glVertex3i(0, 7, 0)
            glVertex3i(0, 0, 0)
            glVertex3i(5, 0, 0)
            glEnd()

            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self._font_texture)

            if shadow:
                glColor32U(shadow)
                glPushMatrix()
                glTranslatef(0.2, 0.2, 0)
                glBegin(GL_QUADS)
                glTexCoord2i(right, top);       glVertex3i(5, 0, 0)
                glTexCoord2i(left, top);        glVertex3i(0, 0, 0)
                glTexCoord2i(left, bottom);     glVertex3i(0, 7, 0)
                glTexCoord2i(right, bottom);    glVertex3i(5, 7, 0)
                glEnd()
                glPopMatrix()

            glColor32U(text)
            glBegin(GL_QUADS)
            glTexCoord2i(right, top);           glVertex3i(5, 0, 0)
            glTexCoord2i(left, top);            glVertex3i(0, 0, 0)
            glTexCoord2i(left, bottom);         glVertex3i(0, 7, 0)
            glTexCoord2i(right, bottom);        glVertex3i(5, 7, 0)
            glEnd()

        rows = self._lcd.width
        lines = self._lcd.height
        background, character, text, shadow = self._colors[self._colorpal]

        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glColor32U(background)
        glTranslatef(border, border, 0)
        glBegin(GL_QUADS)
        glVertex3f(rows * charwidth + (rows - 1) + border, -border, 0)
        glVertex3f(-border, -border, 0)
        glVertex3f(-border, lines * charheight + (lines - 1) + border, 0)
        glVertex3f(rows * charwidth + (rows - 1) + border, lines * charheight
                + (lines - 1) + border, 0)
        glEnd()

        glColor3f(1.0, 1.0, 1.0)
        offset = ( 0, 0x40, 0x20, 0x60 )
        for v in range(0, lines):
            glPushMatrix()
            for i in range(0, rows):
                glputchar(self._vram[offset[v] + i], character, text, shadow)
                glTranslatef(6, 0, 0)
            glPopMatrix()
            glTranslatef(0, 8, 0)

        self.HD44780_FLAG_DIRTY = False

    def pin_change(self, signal, value):
        old = self._pinstate

#        print('%02x %04x %04x' % (self._port[signal], self._pinstate, value))

        if self.HD44780_FLAG_REENTRANT and len(signal) == 2 and signal[0] == 'D':
            return

        self._pinstate = (self._pinstate & ~(1 << self._port[signal])) | (value << self._port[signal])
        eo = old & (1 << self._port['E'])
        e = self._pinstate & (1 << self._port['E'])
        if not (not eo and e):
            return

        '''
        print('LCD: %04x %04x %c %c %c %c' % (self._pinstate, 0,
            'R' if self._pinstate & (1 << self._port['RW']) else 'W',
            'D' if self._pinstate & (1 << self._port['RS']) else 'C',
            'L' if self.HD44780_FLAG_LOWNIBBLE else 'H',
            'B' if self.HD44780_FLAG_BUSY else ' '))
        '''

        self.HD44780_FLAG_REENTRANT = True

        if self._pinstate & (1 << self._port['RW']):
            delay = self.read()
        else:
            delay = self.write()

        if delay:
            self.HD44780_FLAG_BUSY = True
#            self.pin['BUSY'].signal_raise()
            self._busy_timer()

        self.HD44780_FLAG_REENTRANT = False

    def _busy_timer(self):
        self.HD44780_FLAG_BUSY = False
#        self.pin['BUSY'].signal_lower()

    def _reset_cursor(self):
        self._cursor = 0
        HD44780_FLAG_DIRTY = True
        # avr_raise_irq(b->irq + IRQ_HD44780_ADDR, b->cursor)

    def _clear_screen(self):
        self._vram[0:79] = (32,)*80
        self.HD44780_FLAG_DIRTY = True
        # avr_raise_irq(b->irq + IRQ_HD44780_ADDR, b->cursor)

    def kick_cursor(self):
        if self.HD44780_FLAG_I_D:
            if self._cursor < 79:
                self._cursor += 1
            elif self._cursor < 80+64-1:
                self._cursor += 1
        else:
            if self._cursor < 80 and self._cursor > 0:
                self._cursor -= 1
            elif self._cursor > 80:
                self._cursor -= 1
            self.HD44780_FLAG_DIRTY = True
            # avr_raise_irq(b->irq + IRQ_HD44780_ADDR, b->cursor)

    def write_command(self):
        delay = 37

        top = 7
        while top:
            if self._datapins & (1 << top):
                break
            top -= 1

        #print('write_command %02x (%d)' % (self._datapins, top))
        # Clear display
        if top == 0:
            self._clear_screen()
        # Return home
        elif top == 1:
            self._reset_cursor()
            delay = 1520
        # Entry mode set
        elif top == 2:
            self.HD44780_FLAG_I_D = bool(self._datapins & 2)
            self.HD44780_FLAG_S = bool(self._datapins & 1)
        # Display on/off control
        elif top == 3:
            self.HD44780_FLAG_D = bool(self._datapins & 4)
            self.HD44780_FLAG_C = bool(self._datapins & 2)
            self.HD44780_FLAG_B = bool(self._datapins & 1)
            self.HD44780_FLAG_DIRTY = True
        # Cursor display shift
        elif top == 4:
            self.HD44780_FLAG_S_C = bool(self._datapins & 8)
            self.HD44780_FLAG_R_L = bool(self._datapins & 4)
        # Function set
        elif top == 5:
            four = not self.HD44780_FLAG_D_L
            self.HD44780_FLAG_D_L = bool(self._datapins & 16)
            self.HD44780_FLAG_N = bool(self._datapins & 8)
            self.HD44780_FLAG_F = bool(self._datapins & 4)
            if not four and not self.HD44780_FLAG_D_L:
                print('--> activating 4 bits mode')
                self.HD44780_FLAG_LOWNIBBLE = False
        # Set CGRAM address
        elif top == 6:
            self._cursor = 64 + (self._datapins & 0x3f)
        # Set DDRAM address
        elif top == 7:
            self._cursor = self._datapins & 0x7f

        return delay # uS

    def write_data(self):
        self._vram[self._cursor] = self._datapins
        #print('write_data')
        if self.HD44780_FLAG_S_C:
            # TODO: display shift
            pass
        else:
            self.kick_cursor()
        self.HD44780_FLAG_DIRTY = True
        return 37 # uS


    def read(self):
        delay = 0
        four = not self.HD44780_FLAG_D_L
        comp = four and self.HD44780_FLAG_LOWNIBBLE
        done = False
        if comp:
            self._readpins <<= 4
            self._readpins &= 0xff
            done = True
            self.HD44780_FLAG_LOWNIBBLE = not self.HD44780_FLAG_LOWNIBBLE

        # new read
        if not done:
            if self._pinstate & (1 << self._port['RS']):
                delay = 37
                self._readpins = self._vram[self._cursor] & 0xff
                self.kick_cursor()
            else:
                delay = 0
                self._readpins = self._cursor if self._cursor < 80 else self._cursor - 64
                if self.HD44780_FLAG_BUSY:
                    self._readpins |= 0x80
                self._readpins &= 0xff
                self.HD44780_FLAG_BUSY = False
#                self.pin['BUSY'].signal_lower()
                # cancel timer _busy_timer

            # avr_raise_irq(b->irq + IRQ_HD44780_DATA_OUT, b->readpins)

            done = True
            if four:
                self.HD44780_FLAG_LOWNIBBLE = True

        if done:
            # avr_raise_irq(b->irq + IRQ_HD44780_ALL, b->readpins >> 4)
            #print('ALL', self._readpins)
            for i in range(0, 4):
                self.pin_change('D%d' % (4+i), (self._readpins >> (4+i)) & 1)

            self.pin_change('RS', (self._readpins >> 8) & 1)
            self.pin_change('E', (self._readpins >> 9) & 1)
            self.pin_change('RW', (self._readpins >> 10) & 1)

            r = 4 if four else 0
            for i in range(r, 8):
                if (self._readpins >> i) & 1:
                    self.pin['D%d' % i].dst.signal_raise()
                else:
                    self.pin['D%d' % i].dst.signal_lower()

        #print('READ %d %04x' % (delay, self._readpins))
        return delay

    def write(self):
        delay = 0
        four = not self.HD44780_FLAG_D_L
        comp = four and self.HD44780_FLAG_LOWNIBBLE
        write = False
        if four:
            if comp:
                self._datapins = (self._datapins & 0xf0) | ((self._pinstate >> self._port['D4']) & 0xf)
            else:
                self._datapins = (self._datapins & 0xf)  | ((self._pinstate >> (self._port['D4']-4)) & 0xf0)
            self._datapins &= 0xff
            write = comp
            self.HD44780_FLAG_LOWNIBBLE = not self.HD44780_FLAG_LOWNIBBLE
        else:
            self._datapins = (self._pinstate >> self._port['D0']) & 0xff
            write = True

        # avr_raise_irq(b->irq + IRQ_HD44780_DATA_IN, b->datapins)

        if write:
            if self.HD44780_FLAG_BUSY:
                print("Command {} write when still BUSY".format(self._datapins))
            if self._pinstate & (1 << self._port['RS']):
                delay = self.write_data()
            else:
                delay = self.write_command()

        return delay

    def __new__(cls, *args, **kwargs):
        for n in cls._port.keys():
            cls._pins[n] = hd44780_lcd.signal
        return super().__new__(cls, *args, **kwargs)

class ac_input(qb.qb_object_t):
    class signal(simavr._avr.signal):
        def __set__(self, obj, dst):
            super().__set__(obj, dst)
            self._obj._t.start()

        def signal_lower(self):
            self._obj.pin_change(str(self._name, 'ascii'), 0)

        def signal_raise(self):
            self._obj.pin_change(str(self._name, 'ascii'), 1)

    def _switch_auto(self):
        value = True
        while True:
            sleep(1.0 / 50.0)
            if value:
                self.pin['ac_input'].dst.signal_raise()
            else:
                self.pin['ac_input'].dst.signal_lower()
            value = not value

    def pin_change(self, name, value):
        pass

    def __init__(self, name):
        super().__init__(name)
        self._t = Thread(target=self._switch_auto, daemon=True)

    def __new__(cls, *args, **kwargs):
        cls._pins['ac_input'] = ac_input.signal
        return super().__new__(cls, *args, **kwargs)

class charlcd_component(qb.qb_object_t):
    def __init__(self, name, mmcu):
        super().__init__(name)
        self.o.avr = simavr._avr.avr_core(name, mmcu)
        self.o.lcd = hd44780_lcd('HD44780')
        self.o.ac  = ac_input('AC-input')

        self.o.ac.pin['ac_input'] = self.o.avr.pin['IOGD2']
        for i in range(0, 4):
            self.o.avr.pin['IOGB%d' % i] = self.o.lcd.pin['D%d' % (4+i)]
            self.o.lcd.pin['D%d' % (4+i)] = self.o.avr.pin['IOGB%d' % i]

        self.o.avr.pin['IOGB4'] = self.o.lcd.pin['RS']
        self.o.avr.pin['IOGB5'] = self.o.lcd.pin['E']
        self.o.avr.pin['IOGB6'] = self.o.lcd.pin['RW']

#qb.root.o.atmega48 = qb._simavr.avr_core(None, 'atmega48')
#qb.root.o.atmega48.load_firmware(b'atmega48_ledramp.axf')

qb.root.o.obj = charlcd_component(None, 'atmega48')
qb.root.o.obj.o.avr.load_firmware(b'atmega48_charlcd.axf')
