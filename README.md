# FancyLogger
Fork of [aubricus/print_progress.py](https://gist.github.com/aubricus/f91fb55dc6ba5557fbab06119420dd6a) originated from [StackOverflow's Greenstick](http://stackoverflow.com/a/34325723) to allow using multiple progress bars along with regular message logger.


 * Support for multiple progress bars
 * Auto-scrolling message logger below the progress bars
 * Configurable decimals for percentage
 * Display elapsed time in human readable format from seconds to weeks
 * Display a prefix to the left of the progress bar
 * Display a suffix to the right of the progress bar
 * Keep alive even when completed
 * Displayed length of the progress bar can vary
 * Multiple progress bars will stay left-aligned
 * Keep space for permanent progress bar slots
 * Define the maximum number of displayed messages, but log files will keep them all
 * Static class usage
 
 `![example2-runtime.gif](https://github.com/peepall/FancyLogger/blob/master/example2-runtime.gif)
 
 ```python
#!/bin/env/python
# -*- coding: utf-8 -*-

import time, uuid
from random import randrange

from FancyLogger import FancyLogger, TaskProgress


class SomeWork(object):

    def __init__(self):
        self.sub_progressbar = randrange(0, 35)
        self.sub_progressbar_list = range(randrange(50, 150))

        self.uuid = uuid.uuid4()

    def process(self):
        FancyLogger.info(self.uuid)

        if self.sub_progressbar == 5:
            for i in FancyLogger(list=self.sub_progressbar_list):
                time.sleep(.05)

        time.sleep(.1)


class App(object):

    @classmethod
    def example(cls):

        FancyLogger.init(permanent_progressbar_slots=1)

        # Create data for demo
        workload = []
        for i in range(randrange(100, 150)):
            workload.append(SomeWork())

        FancyLogger.info('Start processing things')

        # Iterator usage
        for work in FancyLogger(list=workload,
                              task_progress_object=TaskProgress(total=None,
                                                                prefix='Main task',
                                                                keep_alive=True)):
            work.process()

        FancyLogger.info('End of processing ({} objects)'.format(len(workload)))
        FancyLogger.flush()

if __name__ == '__main__':
    App.example()
```

![example-runtime.gif](https://github.com/peepall/FancyLogger/blob/master/example-runtime.gif)

```python
#!/bin/env/python
# -*- coding: utf-8 -*-

import time
from random import randrange

from FancyLogger import FancyLogger, TaskProgress


class App(object):

    @classmethod
    def example(cls):

        # Different configurations for demo

        # FancyLogger.init(permanent_progressbar_slots=5)
        # FancyLogger.init(permanent_progressbar_slots=3,
        #                  message_number=5,
        #                  task_seconds_to_removal=1)
        FancyLogger.init(message_number=15,
                         task_millis_to_removal=0)

        # Define new tasks
        tasks = [TaskProgress(total=150,
                              prefix='Loading',
                              suffix='Video game!',
                              display_time=True),
                 TaskProgress(total=80,
                              prefix='You have to be patient please'),
                 TaskProgress(total=120,
                              prefix='This one is permanent',
                              suffix='and I am still there :)',
                              display_time=True,
                              keep_alive=True),
                 TaskProgress(total=50,
                              prefix='Almost done !',
                              display_time=True)
                                ]

        # Add tasks into the logger
        for i, t in enumerate(tasks):
            FancyLogger.setTaskObject(task_id='task{}'.format(i), task_progress_object=t)

        for i in range(1, 200):

            random = randrange(0, 5)
            if random == 0:
                FancyLogger.info('I went to the supermarket yesterday :)')
            elif random == 1:
                FancyLogger.warning('Someone tried to rob me!')
            elif random == 2:
                FancyLogger.debug('An apple fell to the ground...')
            elif random == 3:
                FancyLogger.error('I got punched in the face while stealing a lollipop :(')
            elif random == 4:
                FancyLogger.critical('Hit by a car x_x')

            random = randrange(0, 4)
            if random == 0:
                FancyLogger.update(task_id='task0', progress=i)
            elif random == 1:
                FancyLogger.update(task_id='task1', progress=i*random)
            elif random == 2:
                FancyLogger.update(task_id='task2', progress=i*random)
            elif random == 3:
                FancyLogger.update(task_id='task3', progress=i*random)

            # Change settings during execution
            if i == 50:
                FancyLogger.init(permanent_progressbar_slots=3,
                                 message_number=5)

            time.sleep(0.15)

        FancyLogger.info('Bye bye :)')
        FancyLogger.flush()

if __name__ == '__main__':
    App.example()
```
