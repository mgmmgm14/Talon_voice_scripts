from talon import tap
from talon.audio import noise
import eye_zoom_mouse

enabled = True

def on_noise(noise):
    if enabled  and eye_zoom_mouse.zoom_mouse.enabled and noise == 'hiss_start':
        eye_zoom_mouse.zoom_mouse.on_pop('pop')

def on_key(typ, e):
    global enabled
    if e.flags & tap.DOWN and e == 'ctrl-a':
        enabled = not enabled

noise.register('noise', on_noise)
tap.register(tap.KEY, on_key)
