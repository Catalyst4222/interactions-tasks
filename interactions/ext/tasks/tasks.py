import asyncio
import time
from abc import ABC, abstractmethod
from typing import Callable, Coroutine, List, Union


class Trigger(ABC):
    @abstractmethod
    async def wait_for_ready(self):
        """
        A method to wait until all conditions to fire are met
        """
        ...

    def __await__(self):
        return self.wait_for_ready().__await__()


class IntervalTrigger(Trigger):
    def __init__(self, delay: int):
        self.last_fire: float = time.time()
        self.delay: float = delay

    async def wait_for_ready(self):
        await asyncio.sleep((self.last_fire + self.delay) - time.time())


class Task:
    def __init__(self, func, triggers: List[Trigger], *args, **kwargs):
        self.func: Callable[..., Coroutine] = func
        self.triggers: List[Trigger] = triggers
        self.args = args
        self.kwargs = kwargs

        self._running: asyncio.Event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

    async def fire(self):
        for trigger in self.triggers:
            trigger.last_fire = time.time()
        res = await self.func(*self.args, **self.kwargs)
        return res

    def start(self) -> asyncio.Task:
        """
        The synchronous method to start a task loop
        :return: The asyncio.Task running the loop
        :rtype: asyncio.Task
        """
        self._running.set()
        return self._loop.create_task(self.run())

    async def run(self):
        """
        The async method to start a task loop

        :returns: None after the task is stopped
        :rtype: None
        """
        while self._running.is_set():
            await asyncio.gather(*self.triggers)
            self._loop.create_task(self.fire())

    def stop(self):
        """
        The method to stop the task
        """
        self._running.clear()


def create_task(triggers: Union[Trigger, List[Trigger]], *args, **kwargs):
    if not isinstance(triggers, list):
        triggers = [triggers]

    def inner(func):
        return Task(func, triggers, *args, **kwargs)

    return inner
