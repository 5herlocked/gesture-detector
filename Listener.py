from pynput import keyboard


class Listener(keyboard.Listener):
    def __init__(self, recorder):
        super(Listener, self).__init__(on_press=self.on_press)
        self.recorder = recorder

    def on_press(self, key):
        if key is None:
            pass
        elif isinstance(key, keyboard.KeyCode):
            if key.char == 'r' and not self.recorder.recording:
                self.recorder.start()
            if key.char == 's':
                if self.recorder.recording:
                    self.recorder.stop()
                return False
