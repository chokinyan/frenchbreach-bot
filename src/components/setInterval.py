import threading


class SetInterval:
    def __init__(self, interval, action, *args, **kwargs):
        self.interval = interval
        self.action = action
        self.args = args
        self.kwargs = kwargs
        self.stop_event = threading.Event()

        # Start the background thread immediately
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True  # Allows program to exit even if thread is running
        self.thread.start()

    def _run(self):
        # wait returns True if stop_event.set() is called, False if timeout expires
        while not self.stop_event.wait(self.interval):
            self.action(*self.args, **self.kwargs)

    def cancel(self):
        """Stops the interval loop."""
        self.stop_event.set()