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
