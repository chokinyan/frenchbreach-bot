import asyncio
import inspect
import logging
import threading

log = logging.getLogger("frenchbreaches")


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
            try:
                result = self.action(*self.args, **self.kwargs)
                if inspect.isawaitable(result):
                    if self.event_loop is None:
                        raise RuntimeError(
                            "An event loop is required for async actions"
                        )
                    future = asyncio.run_coroutine_threadsafe(
                        result, self.event_loop
                    )
                    future.result()
            except Exception:  # noqa: BLE001
                # Une itération qui échoue ne doit pas tuer la boucle :
                # sinon plus aucune alerte jusqu'au prochain redémarrage.
                log.exception("Itération SetInterval en échec")

    def cancel(self):
        """Stops the interval loop."""
        self.stop_event.set()
