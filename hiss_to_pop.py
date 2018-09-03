from talon.audio import noise
import eye_zoom_mouse
def on_noise(noise):
    if noise == 'hiss_start':
        eye_zoom_mouse.zoom_mouse.on_pop('pop')

noise.register('noise', on_noise)