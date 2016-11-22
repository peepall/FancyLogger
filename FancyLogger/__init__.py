#!/bin/env/python
# coding: utf-8

import logging
import time
import uuid
import dill
from multiprocessing import Queue

from .commands import *
from .processing import MultiprocessingLogger


class TaskProgress(object):
    """
    Holds both data and graphics-related information for a task's progress bar
    """

    def __init__(self,
                 total,
                 prefix='',
                 suffix='',
                 decimals=0,
                 bar_length=60,
                 keep_alive=False,
                 display_time=False):
        super(TaskProgress, self).__init__()

        self.progress = 0

        # Minimum number of seconds at maximum completion before a progress bar is removed from display
        # The progress bar may vanish at a further time as the redraw rate depends upon chrono AND method calls
        self.timeout_chrono = None
        self.begin_time = None
        self.end_time = None
        self.elapsed_time_at_end = None

        # Graphics related information
        self.keep_alive = keep_alive
        self.display_time = display_time

        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.bar_length = bar_length

    def set_progress(self, progress):
        """

        :param progress:
        :return:
        """
        _progress = progress
        if _progress > self.total:
            _progress = self.total

        # Stop task chrono if needed
        if _progress == self.total and self.display_time:
            self.end_time = time.time() * 1000

        has_changed = self.progress != _progress

        if has_changed:
            self.progress = _progress

        return has_changed


class FancyLogger(object):

    queue = None

    default_message_number = 20
    default_permanent_progressbar_slots = 0
    default_redraw_frequency_millis = 500
    default_level = logging.INFO
    default_task_millis_to_removal = 500

    def __init__(self,
                 message_number=default_message_number,
                 permanent_progressbar_slots=default_permanent_progressbar_slots,
                 redraw_frequency_millis=default_redraw_frequency_millis,
                 level=default_level,
                 task_millis_to_removal=default_task_millis_to_removal):
        """
        Defines the logger behavior
        :param message_number:                  Number of simultaneous messages below the progress bars
        :param permanent_progressbar_slots:     The amount of vertical space (in bar number) to keep at all times
                                                between progress bars section and messages section
        :param redraw_frequency_millis:         Minimum time lapse in milliseconds between two redrawings. It may be
                                                more because the redraw rate depends upon chrono AND method calls
        :param level:                           The logging level (from standard logging module)
        :param task_millis_to_removal:          Minimum number of milliseconds at maximum completion before a progress
                                                bar is removed from display. The progress bar may vanish at a further
                                                time as the redraw rate depends upon chrono AND method calls
        :return:
        """
        super(FancyLogger, self).__init__()

        if not self.queue:
            self.queue = Queue()
            self.process = MultiprocessingLogger(queue=self.queue,
                                                 level=level,
                                                 message_number=message_number,
                                                 permanent_progressbar_slots=permanent_progressbar_slots,
                                                 redraw_frequency_millis=redraw_frequency_millis,
                                                 task_millis_to_removal=task_millis_to_removal)
            self.process.start()

    def flush(self):
        """
        Flushes the remaining messages by forcing redraw. Can be useful if you want to be sure a message or progress has
        been updated in display, like when you are exiting an application.
        :return:
        """
        self.queue.put(dill.dumps(FlushCommand()))

    def terminate(self):
        """
        Tells the logger process to exit.
        :return:
        """
        self.queue.put(dill.dumps(ExitCommand()))

        if self.process:
            self.process.join()

    def set_configuration(self,
                          message_number=default_message_number,
                          permanent_progressbar_slots=default_permanent_progressbar_slots,
                          redraw_frequency_millis=default_redraw_frequency_millis,
                          level=default_level,
                          task_millis_to_removal=default_task_millis_to_removal):
        self.queue.put(dill.dumps(SetConfigurationCommand(task_millis_to_removal=task_millis_to_removal,
                                                          level=level,
                                                          permanent_progressbar_slots=permanent_progressbar_slots,
                                                          message_number=message_number,
                                                          redraw_frequency_millis=redraw_frequency_millis)))

    def set_level(self,
                  level,
                  console_only=False):
        """
        Sets the logging level for log messages
        :return:
        """
        self.queue.put(dill.dumps(SetLevelCommand(level=level,
                                                  console_only=console_only)))

    def set_task_object(self,
                        task_id,
                        task_progress_object):
        """
        Defines a new task with the given information using a TaskProgress object
        :param task_id:                 To be registered in task list
        :param task_progress_object:    Total number of iterations before completed
        :return:
        """
        self.set_task(task_id=task_id,
                      total=task_progress_object.total,
                      prefix=task_progress_object.prefix,
                      suffix=task_progress_object.suffix,
                      decimals=task_progress_object.decimals,
                      bar_length=task_progress_object.bar_length,
                      keep_alive=task_progress_object.keep_alive,
                      display_time=task_progress_object.display_time)

    def set_task(self,
                 task_id,
                 total,
                 prefix,
                 suffix='',
                 decimals=0,
                 bar_length=60,
                 keep_alive=False,
                 display_time=False):
        """
        Defines a new task with the given information
        :param task_id:     To be registered in task list
        :param total:       Total number of iterations before completed
        :param prefix:      Title to display before progress bar
        :param suffix:      Title to display after percentage
        :param decimals:    Number of decimals for percentage
        :param bar_length:  Bar length on screen (in chars)
        :param keep_alive:        Defines if the progress bar should stay display even when completed
        :param display_time:      Display the elapsed time in human readable format after the suffix
        :return:
        """
        self.queue.put(dill.dumps(NewTaskCommand(task_id=task_id,
                                                 task=TaskProgress(total,
                                                                   prefix,
                                                                   suffix,
                                                                   decimals,
                                                                   bar_length,
                                                                   keep_alive,
                                                                   display_time))))

    def update(self,
               task_id,
               progress):
        """
        If the given id exists, update the task's progress and trigger redrawing
        :param task_id:     Task to update (must be existing)
        :param progress:    Progress relative to the 'task.total' attribute
        :return:
        """
        self.queue.put(dill.dumps(UpdateProgressCommand(task_id=task_id,
                                                        progress=progress)))

    def debug(self, text):
        """
        Posts a debug message adding a timestamp and logging level
        :param text:
        :return:
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.DEBUG)))

    def info(self, text):
        """
        Posts an info message adding a timestamp and logging level
        :param text:
        :return:
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.INFO)))

    def warning(self, text):
        """
        Posts a warning message adding a timestamp and logging level
        :param text:
        :return:
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.WARNING)))

    def error(self, text):
        """
        Posts an error message adding a timestamp and logging level
        :param text:
        :return:
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.ERROR)))

    def critical(self, text):
        """
        Posts a critical message adding a timestamp and logging level
        :param text:
        :return:
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.CRITICAL)))

    # --------------------------------------------------------------------
    # Iterator implementation
    def progress(self, enumerable, task_progress_object=None):

        self.list = enumerable
        self.list_length = len(enumerable)
        self.task_id = uuid.uuid4()
        self.index = 0

        if task_progress_object:
            # Force total attribute
            task_progress_object.total = self.list_length
        else:
            task_progress_object = TaskProgress(total=self.list_length,
                                                display_time=True,
                                                prefix='Progress')

        # Create a task progress
        self.set_task_object(task_id=self.task_id,
                             task_progress_object=task_progress_object)

        return self

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= self.list_length:
            raise StopIteration
        else:
            self.index += 1
            self.update(task_id=self.task_id,
                        progress=self.index)

            return self.list[self.index - 1]
    # ---------------------------------------------------------------------
