# FancyLogger
Fork of [aubricus/print_progress.py](https://gist.github.com/aubricus/f91fb55dc6ba5557fbab06119420dd6a) originated from [StackOverflow's Greenstick](http://stackoverflow.com/a/34325723) to allow using multiple progress bars along with regular message logger.  
Available on [PyPi](https://pypi.python.org/pypi/FancyLogger).
Tested on Windows and CentOS Linux using Python 3.5.1.
  
  
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
 * Python's multiprocessing support
  
 ## Iterator usage
 ![example2-runtime.gif](https://github.com/peepall/FancyLogger/blob/master/examples/example2-runtime.gif)
  
```python
#!/bin/env/python
# coding: utf-8

import os
import time
from multiprocessing import Process
from random import randrange

from FancyLogger import FancyLogger, TaskProgress


def pid(text):
    return '[{}] : {}'.format(os.getpid(), text)


class WorkerClass(Process):

    def __init__(self, logger):
        super(WorkerClass, self).__init__()

        self.logger = logger

        # Define a random progress bar
        self.enumerable_data = range(randrange(50, 500))

    def run(self):
        self.logger.info(pid('Hello there :)'))

        # Here we simulate some work using a progress bar iterator
        for _ in self.logger.progress(enumerable=self.enumerable_data,
                                      task_progress_object=TaskProgress(total=None,  # Total is computed by iterator
                                                                        prefix=pid('Progress'),
                                                                        keep_alive=False,
                                                                        display_time=True)):
            time.sleep(.01)

        self.logger.info(pid('See you later!'))


class App(object):

    def __init__(self):
        super(App, self).__init__()

    @classmethod
    def example(cls):

        # Configure and start the logger process
        logger = FancyLogger(permanent_progressbar_slots=9)

        # Create a random list of worker processes
        workers = [WorkerClass(logger) for _ in range(randrange(5, 10))]

        logger.info('[main] : Start processing things')

        # Start processes
        for w in workers:
            w.start()

        # Wait for processes one by one, using a progress bar iterator for the main thread
        for w in logger.progress(enumerable=workers,
                                 task_progress_object=TaskProgress(total=None,  # Total is computed by iterator
                                                                   prefix='Main task',
                                                                   keep_alive=True)):
            w.join()

        logger.info('[main] : End of processing ({} objects)'.format(len(workers)))

        # Display log messages and progress bars as they are right now, to see their last state before exiting
        # Indeed the logger uses a refresh rate that can be set during initialization. If you do not call flush method
        # then you might miss the last messages and progress bar states that have not been displayed yet
        logger.flush()
        # Stop the logger process
        logger.terminate()

if __name__ == '__main__':
    App.example()
```  
  
## In-depth usage
![example-runtime.gif](https://github.com/peepall/FancyLogger/blob/master/examples/example-runtime.gif)
  
```python
#!/bin/env/python
# coding: utf-8

import time
from random import randrange

from FancyLogger import FancyLogger, TaskProgress


class App(object):

    @classmethod
    def example(cls):

        # Different configurations for demo

        # logger = FancyLogger(permanent_progressbar_slots=5)
        # logger = FancyLogger(permanent_progressbar_slots=3,
        #                      message_number=5,
        #                      task_seconds_to_removal=1)
        logger = FancyLogger(message_number=15,
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
            logger.set_task_object(task_id='task{}'.format(i), task_progress_object=t)

        for i in range(1, 200):

            random = randrange(0, 5)
            if random == 0:
                logger.info('This is an info :)')
            elif random == 1:
                logger.warning('You should read this carefully!')
            elif random == 2:
                logger.debug('Don\'t bother read this')
            elif random == 3:
                logger.error('Something went wrong :(')
            elif random == 4:
                logger.critical('Ouch x_x')

            random = randrange(0, 4)
            if random == 0:
                logger.update(task_id='task0', progress=i)
            elif random == 1:
                logger.update(task_id='task1', progress=i*random)
            elif random == 2:
                logger.update(task_id='task2', progress=i*random)
            elif random == 3:
                logger.update(task_id='task3', progress=i*random)

            # Change settings during execution
            if i == 50:
                logger.set_configuration(permanent_progressbar_slots=3,
                                         message_number=5)

            time.sleep(0.15)

        logger.info('Bye bye :)')
        logger.flush()
        logger.terminate()

if __name__ == '__main__':
    App.example()
```
