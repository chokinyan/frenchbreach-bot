import asyncio
import inspect
import threading


class SetInterval:
    def __init__(self, interval: float, action, *args, event_loop=None, **kwargs):
        self.interval = interval
        self.action = action
        self.args = args
        self.kwargs = kwargs
        self.event_loop = event_loop
        self.stop_event = threading.Event()

        # Start the background thread immediately
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True  # Allows program to exit even if thread is running
        self.thread.start()

    def _run(self):
        # wait returns True if stop_event.set() is called, False if timeout expires
        while not self.stop_event.wait(self.interval):
            result = self.action(*self.args, **self.kwargs)
            if inspect.isawaitable(result):
                if self.event_loop is None:
                    raise RuntimeError("An event loop is required for async actions")
                asyncio.run_coroutine_threadsafe(result, self.event_loop).result()

    def cancel(self):
        """Stops the interval loop."""
        self.stop_event.set()