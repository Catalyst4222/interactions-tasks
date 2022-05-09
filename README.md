Simple example, triggers every 3 seconds:
```python
from interactions.ext.tasks import IntervalTrigger, create_task

@create_task(IntervalTrigger(3))
async def my_task():
    print("hi")

my_task.start()
```

Multiple conditions (example will be improved when more triggers are added)\
The task will only run every 5 seconds because every trigger needs to be ready
```python
from interactions.ext.tasks import IntervalTrigger, create_task

@create_task(IntervalTrigger(3), IntervalTrigger(5))
async def my_task():
    print("hi")

my_task.start()
```

To have the task run when any trigger is ready, use the OrTrigger.\
The task will run every 3 and 5 seconds (it may run twice occasionally due to how timing works)
```python
from interactions.ext.tasks import IntervalTrigger, OrTrigger, create_task

@create_task(OrTrigger(IntervalTrigger(3), IntervalTrigger(5)))
async def my_task():
    print("hi")

my_task.start()
```

Classes are special, due to how functions turn into methods and other python black magic\
There are two ways to properly do tasks in classes

The first way is to pass `self` when starting the task\
Any args or kwargs passed to `Task.start()` will be prepended to the function
```python
from interactions import Extension
from interactions.ext.tasks import IntervalTrigger, create_task

class Cog(Extension):
    def __init__(self, client):
        self.method.start(self)

    @create_task(IntervalTrigger(1))
    async def method(self):
        print(self)
```

The other way is just to wrap the method manually
```python
from interactions import Extension
from interactions.ext.tasks import IntervalTrigger, create_task

class Cog(Extension):
    def __init__(self, client):
        self.method = create_task(IntervalTrigger(1))(self.method)
        self.method.start()

    async def method(self):
        print(self)
```