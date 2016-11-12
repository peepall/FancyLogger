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
