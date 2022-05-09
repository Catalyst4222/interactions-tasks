import asyncio
import time
from abc import ABC, abstractmethod
from typing import Callable, Coroutine, List, Sequence, Optional, Dict, Any


class Trigger(ABC):
    """
    Represents the condition for a task to depend on.
    
    .. seealso::
        This class is an ABC, and meant to be subclassed
        from for inheriting base trigger logic. For other
        types of triggers, see ``OrTrigger`` and 
        ``IntervalTrigger``.
    """
    
    @abstractmethod
    async def wait_for_ready(self):
        """
        An abstract method to wait until all
        conditions to fire the trigger have been met.
        
        .. warning::
            This method has not yet been implemented and
            will raise a ``NotImplementedError``.
        """
        raise NotImplementedError

    def __await__(self):
        return self.wait_for_ready().__await__()

    def __or__(self, other):
        return OrTrigger(self, other) if isinstance(other, Trigger) else NotImplemented


class OrTrigger(Trigger):
    """
    A trigger variant that waits until any of its nested
    triggers are ready on condition.
    
    :ivar List[Trigger] triggers: The triggers stored for dependency.
    :ivar List[asyncio.Task] tasks: The tasks for each given trigger.
    """

    def __init__(self, *triggers: Trigger):
        r"""
        :param \*triggers: The triggers to depend on.
        :type \*triggers: List[Trigger]
        """
        self.triggers: List[Trigger] = list(triggers)
        self.tasks: List[asyncio.Task] = []

    async def wait_for_ready(self):
        """
        Acts as a non-blocking asynchronous call, "idling"
        or waiting until any of the given triggers are ready.
        
        :return: None
        :rtype: None
        """
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
    """
    A trigger variant that waits until a given time
    value has been relapsed. This trigger acts cyclically
    based off of a delay.
    
    :cvar float last_fire: The last known task call.
    :ivar float delay: The current given waiting time.
    """
    
    def __init__(self, delay: int):
        """
        :param delay: How long the trigger should wait between a task call.
        :type delay: int
        """
        self.last_fire: float = time.time()
        self.delay: float = delay

    async def wait_for_ready(self):
        """
        Acts as a non-blocking asynchronous call, "idling"
        or waiting until any of the given triggers are ready.
        
        :return: None
        :rtype: None
        """
        await asyncio.sleep((self.last_fire + self.delay) - time.time())
        self.last_fire = time.time()


class Task:
    """
    A "task," or instruction that can be decoratively applied to
    an existing coroutine method. The goal of a task is to run
    as a cron-job or triggerable logic event.
    
    :ivar Callable[..., Coroutine] func: The method that the task is applied onto.
    :ivar Sequence[Trigger] triggers: A sequenced trigger that can be listable.
    :ivar Sequence[Any] args: Any extra given running arguments from initialisation.
    :ivar Dict[str, Any] kwargs: Any extra given key-word arguments from initialisation.
    :cvar Sequence pre_args: The pre-given arguments from the task.
    :cvar Dict[str, Any] pre_kwargs: The pre-given key-word arguments from the task.
    :cvar asyncio.Event _running: An asynchronous event used to determine the task's active state.
    :cvar asyncio.AbstractEventLoop _loop: An asynchronous event loop used to help manage the ``self._running`` instance.
    """
    
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
        """
        Calls on the function with all data necessary
        for its argument signature.
        
        :return: The coroutine method.
        :rtype: Callable[..., Coroutine]
        """
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

        :return: None after the task is stopped
        :rtype: None
        """
        while self._running.is_set():
            await asyncio.gather(*self.triggers)
            self._loop.create_task(self.fire())

    def stop(self):
        """
        The method to stop the task
        
        :return: None after the task is stopped
        :rtype: None
        """
        self._running.clear()

    async def __call__(self, *args, **kwargs):
        return await self.func(*args, **kwargs)


def create_task(*triggers: Trigger, **kwargs):
    def inner(func):
        return Task(func, triggers, **kwargs)

    return inner
