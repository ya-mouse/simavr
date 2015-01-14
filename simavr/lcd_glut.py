from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *
from threading import Thread

class lcd_glut:
    _g = {
        '20x4': (20, 4),
    }

    def __init__(self, obj, geom, scale):
        try:
            w, h = self._g[geom]
        except KeyError:
            print('Unsupported geometry: {}'.format(geom))
            return

        self._w = w
        self._h = h

        w = 5 + w * 6
        h = 5 + h * 8
        w *= scale
        h *= scale

        glutInit(['lcdglut'])
        glutInitDisplayMode(GLUT_RGB | GLUT_DOUBLE)
        glutInitWindowSize(w, h)
        self._obj = obj
        self._window = glutCreateWindow('LCD [{}]'.format(geom))

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, w, 0, h, 0, 10)
        glScalef(1,-1,1)
        glTranslatef(0, -1 * h, 0)

        glutDisplayFunc(self._displayCB)
        glutKeyboardFunc(self._keyCB)
        glutTimerFunc(int(1000 / 24), self._timerCB, 0)

        glEnable(GL_TEXTURE_2D)
        glShadeModel(GL_SMOOTH)

        glClearColor(0.8, 0.8, 0.8, 1.0)
        glColor4f(1.0, 1.0, 1.0, 1.0)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_BLEND)

    def _displayCB(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glScalef(3, 3, 1)

        self._obj.draw()

        glPopMatrix()
        glutSwapBuffers()

    def _keyCB(self, key, x, y):
        pass

    def _timerCB(self, value):
        glutTimerFunc(int(1000/64), self._timerCB, 0)
        glutPostRedisplay()

    def start(self):
        t = Thread(target=glutMainLoop, daemon=True)
        t.start()
        return t

    @property
    def width(self):
        return self._w

    @property
    def height(self):
        return self._h

from lcd_glut_font import font

if __name__ == '__main__':
    class test:
        def draw(self, lcd):
            glDisable(GL_TEXTURE_2D)
            glDisable(GL_BLEND)

    lcd = lcd_glut(test(), '20x4', 3)
    lcd.start().join()
