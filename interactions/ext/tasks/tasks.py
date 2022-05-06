import asyncio
import time
from abc import ABC, abstractmethod
from typing import Callable, Coroutine, List, Sequence, Optional, Dict, Any


class Trigger(ABC):
    @abstractmethod
    async def wait_for_ready(self):
        """
        A method to wait until all conditions to fire are met
        """
        raise NotImplementedError

    def __await__(self):
        return self.wait_for_ready().__await__()

    def __or__(self, other):
        return OrTrigger(self, other) if isinstance(other, Trigger) else NotImplemented


class OrTrigger(Trigger):
    """Waits until any of its triggers are ready"""

    def __init__(self, *triggers: Trigger):
        self.triggers: List[Trigger] = list(triggers)
        self.tasks: List[asyncio.Task] = []

    async def wait_for_ready(self):
        to_make: List[Trigger] = []
        for trigger in self.triggers:
            for task in self.tasks:
                if task.trigger == trigger:
                    break
            else:
                to_make.append(trigger)

        for trigger in to_make:
            task = asyncio.create_task(trigger.wait_for_ready())
            task.trigger = trigger
            self.tasks.append(task)

        done, pending = await asyncio.wait(
            self.tasks, return_when=asyncio.FIRST_COMPLETED
        )

        for task in done:
            self.tasks.remove(task)

    def __or__(self, other):
        if not isinstance(other, Trigger):
            return NotImplemented

        self.triggers.append(other)
        return self


class IntervalTrigger(Trigger):
    def __init__(self, delay: int):
        self.last_fire: float = time.time()
        self.delay: float = delay

    async def wait_for_ready(self):
        await asyncio.sleep((self.last_fire + self.delay) - time.time())
        self.last_fire = time.time()


class Task:
    def __init__(self, func, triggers: Sequence[Trigger], *args, **kwargs):
        self.func: Callable[..., Coroutine] = func
        self.triggers: Sequence[Trigger] = triggers
        self.args: Sequence[Any] = args
        self.kwargs: Dict[str, Any] = kwargs

        self.pre_args: Sequence = ()
        self.pre_kwargs: Dict[str, Any] = {}
        self._running: asyncio.Event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

    async def fire(self):
        res = await self.func(*self.pre_args, *self.args, **self.pre_kwargs, **self.kwargs)
        return res

    def start(self, *args, **kwargs) -> asyncio.Task:
        """
        The synchronous method to start a task loop
        Any args/kwargs passed are prepended to the set args/kwargs
        :return: The asyncio.Task running the loop
        :rtype: asyncio.Task
        """
        self.pre_args = args
        self.pre_kwargs = kwargs
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

    async def __call__(self, *args, **kwargs):
        return await self.func(*args, **kwargs)


def create_task(*triggers: Trigger, **kwargs):
    def inner(func):
        return Task(func, triggers, **kwargs)

    return inner
