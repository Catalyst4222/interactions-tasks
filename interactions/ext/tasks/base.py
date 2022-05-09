from interactions.ext import Version, VersionAuthor, Base

__version__ = "1.0.0"

from .tasks import create_task, Task, IntervalTrigger, Trigger, OrTrigger

version = Version(
    version=__version__,
    authors=[VersionAuthor("Catalyst4")],
)

base = Base(
    name="interactions-tasks",
    version=version,
    link="https://github.com/Catalyst4222/interactions-tasks",
    description="A task implementation for discord-py-interactions",
    packages=["interactions.ext.tasks"],
    requirements=["discord-py-interactions>=4.2.0"],
)

base.add_service(create_task, "create_task")
base.add_service(Task, "Task")
base.add_service(Trigger, "Trigger")
base.add_service(IntervalTrigger, "IntervalTrigger")
base.add_service(OrTrigger, "OrTrigger")
