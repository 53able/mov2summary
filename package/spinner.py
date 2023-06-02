import itertools
import sys
import threading
import time

# スピナーを表示するクラス
class Spinner:
    def __init__(self, message='Loading...', delay=0.1):
        self.spinner = itertools.cycle(['-', '/', '|', '\\'])
        self.delay = delay
        self.busy = False
        self.spinner_visible = False
        self.message = message

    def write_next(self):
        with self._stdout_lock:
            if not self.spinner_visible:
                return
            sys.stdout.write(next(self.spinner))
            sys.stdout.flush()

    def run(self):
        while self.busy:
            self.write_next()
            time.sleep(self.delay)
            sys.stdout.write('\b')

    def start(self):
        self.busy = True
        self.spinner_visible = True
        sys.stdout.write(self.message)
        self._stdout_lock = threading.Lock()
        threading.Thread(target=self.run).start()

    def stop(self):
        self.busy = False
        self.spinner_visible = False
        time.sleep(self.delay)
