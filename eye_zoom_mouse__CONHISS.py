import math
import time

from eye_mouse import tracker, mouse, main_screen
from eye_mouse import config as eye_config
from talon_init import TALON_HOME
from talon import app, canvas, eye, ctrl, screen
from talon.api import lib, ffi
from talon.audio import noise
from talon.skia import Image
from talon.track.geom import Point2d
from talon.ui import Rect

class config:
    screen_area = Point2d(400, 300)
    img_scale = 3
    img_alpha = 0.9
    eye_avg = 20
    double_click = 0.25
    frames = 10
    live = True

def screenshot(x, y, width, height):
    img = screen.capture(x, y, width, height)
    img.rect = Rect(x, y, width, height)
    return img

STATE_IDLE = 0
STATE_OVERLAY = 1

class ZoomMouse:
    def __init__(self):
        self.state = STATE_IDLE
        self.img = None
        self.handle_size = Point2d(0, 0)
        self.last_click = 0
        self.enabled = False
        self.rect = None
        self.canvas = None

    def enable(self):
        if self.enabled: return
        noise.register('noise', self.on_pop)
        # app.register('overlay', self.draw_gaze)
        self.enabled = True

    def disable(self):
        if not self.enabled: return
        noise.unregister('noise', self.on_pop)
        # app.unregister('overlay', self.draw_gaze)
        self.enabled = False
        if self.canvas:
            self.canvas.unregister('draw', self.draw)
            self.canvas.close()
            self.canvas = None

    def capture(self):
        try:
            self.canvas.allow_capture(False)
            self.img = screenshot(*self.rect)
            self.canvas.allow_capture(True)
        except AttributeError:
            pass

    def on_pop(self, noise):
        if len(mouse.eye_hist) < 2:
            return
        if noise != 'hiss_start':
            return
        now = time.time()
        if self.state == STATE_IDLE:
            if now - self.last_click < config.double_click:
                ctrl.mouse_click(hold=32000)
                return

            l, r = mouse.eye_hist[-1]
            p = (l.gaze + r.gaze) / 2
            main_gaze = -0.02 < p.x < 1.02 and -0.02 < p.y < 1.02 and bool(l or r)
            if not main_gaze:
                pass # return

            ctrl.cursor_visible(False)

            self.gaze = eye_config.size_px * p
            capture = self.gaze - (config.screen_area / 2)
            capture.x = min(max(capture.x, 0), main_screen.width - config.screen_area.x)
            capture.y = min(max(capture.y, 0), main_screen.height - config.screen_area.y)
            self.rect = (capture.x, capture.y, config.screen_area.x, config.screen_area.y)
            self.pos = self.gaze - (config.screen_area * config.img_scale) / 2
            self.pos.x = min(max(self.pos.x, 0), main_screen.width - config.screen_area.x * config.img_scale)
            self.pos.y = min(max(self.pos.y, 0), main_screen.height - config.screen_area.y * config.img_scale)
            self.size = Point2d(config.screen_area.x * config.img_scale, config.screen_area.y * config.img_scale)
            self.off = Point2d(0, 0)

            self.frame = 0
            self.canvas = canvas.Canvas(self.pos.x, self.pos.y, self.size.x, self.size.y)
            if not config.live:
                self.capture()
            self.canvas.register('draw', self.draw)
            self.state = STATE_OVERLAY
        elif self.state == STATE_OVERLAY:
            self.state = STATE_IDLE
            ctrl.cursor_visible(True)
            self.canvas.unregister('draw', self.draw)
            self.canvas.close()
            self.canvas = None
            dot, origin = self.get_pos()
            if origin:
                ctrl.mouse(origin.x, origin.y)
                ctrl.mouse_click(hold=32000)
                self.last_click = time.time()

    def get_pos(self):
        dot = Point2d(0, 0)
        hist = mouse.eye_hist[-config.eye_avg:]
        for l, r in hist:
            dot += (l.gaze + r.gaze) / 2
        dot /= len(hist)
        dot *= Point2d(main_screen.width, main_screen.height)

        off = dot - (self.pos - self.off)
        origin = self.img.rect.pos + off / config.img_scale
        if self.img.rect.contains(origin.x, origin.y):
            return dot, origin
        return None, None

    def draw(self, canvas):
        if not self.canvas:
            return False
        if config.live and self.rect:
            self.capture()
        self.frame += 1
        if self.frame < config.frames:
            t = ((self.frame + 1) / config.frames) ** 2

            anim_pos_from = Point2d(self.rect[0], self.rect[1])
            anim_pos_to = Point2d(canvas.x, canvas.y)
            anim_size_from = config.screen_area
            anim_size_to = Point2d(canvas.width, canvas.height)

            pos = anim_pos_from + (anim_pos_to - anim_pos_from) * t
            size = anim_size_from + (anim_size_to - anim_size_from) * t

            dst = Rect(pos.x, pos.y, size.x, size.y)
        elif self.frame == config.frames:
            self.canvas.set_panel(True)
            dst = Rect(canvas.x, canvas.y, canvas.width, canvas.height)
        else:
            dst = Rect(canvas.x, canvas.y, canvas.width, canvas.height)
        src = Rect(0, 0, self.img.width, self.img.height)
        canvas.draw_image_rect(self.img, src, dst)

        dot, origin = self.get_pos()
        if not dot: return
        paint = canvas.paint
        paint.style = paint.Style.FILL
        paint.color = 'ffffff'
        canvas.draw_circle(dot.x, dot.y, config.img_scale + 1)
        canvas.draw_circle(origin.x, origin.y, 2)
        paint.color = '000000'
        canvas.draw_circle(dot.x, dot.y, config.img_scale)
        canvas.draw_circle(origin.x, origin.y, 1)
        ctrl.mouse(origin.x, origin.y)

zoom_mouse = ZoomMouse()

from talon import app
def on_menu(item):
    if item == 'Eye Tracking >> Control Mouse (Zoom)':
        if zoom_mouse.enabled:
            zoom_mouse.disable()
        else:
            zoom_mouse.enable()
        lib.menu_check(b'Eye Tracking >> Control Mouse (Zoom)', zoom_mouse.enabled)

lib.menu_add(b'Eye Tracking >> Control Mouse (Zoom)')
lib.menu_check(b'Eye Tracking >> Control Mouse (Zoom)', zoom_mouse.enabled)
app.register('menu', on_menu)
