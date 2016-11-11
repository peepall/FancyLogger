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