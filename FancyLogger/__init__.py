#!/bin/env/python
# coding: utf-8

import logging
import time
import uuid
import dill
import os
from multiprocessing import Queue

from .commands import *
from .processing import MultiprocessingLogger


class TaskProgress(object):
    """
    Holds both data and graphics-related information for a task's progress bar.
    The logger will iterate over TaskProgress objects to draw progress bars on screen.
    """

    def __init__(self,
                 total,
                 prefix='',
                 suffix='',
                 decimals=0,
                 bar_length=60,
                 keep_alive=False,
                 display_time=False):
        """
        Creates a new progress bar using the given information.
        :param total:           The total number of iteration for this progress bar.
        :param prefix:          [Optional] The text that should be displayed at the left side of the progress bar. Note
                                that progress bars will always stay left-aligned at the shortest possible.
        :param suffix:          [Optional] The text that should be displayed at the very right side of the progress bar.
        :param decimals:        [Optional] The number of decimals to display for the percentage.
        :param bar_length:      [Optional] The graphical bar size displayed on screen. Unit is character.
        :param keep_alive:      [Optional] Specify whether the progress bar should stay displayed forever once completed
                                or if it should vanish.
        :param display_time:    [Optional] Specify whether the duration since the progress has begun should be
                                displayed. Running time will be displayed between parenthesis, whereas it will be
                                displayed between brackets when the progress has completed.
        """
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
        Defines the current progress for this progress bar in iteration units (not percent).
        :param progress:    Current progress in iteration units regarding its total (not percent).
        :return:            True if the progress has changed. If the given progress is higher than the total or lower
                            than 0 then it will be ignored.
        """
        _progress = progress
        if _progress > self.total:
            _progress = self.total
        elif _progress < 0:
            _progress = 0

        # Stop task chrono if needed
        if _progress == self.total and self.display_time:
            self.end_time = time.time() * 1000

            # If the task has completed instantly then define its begin_time too
            if not self.begin_time:
                self.begin_time = self.end_time

        has_changed = self.progress != _progress

        if has_changed:
            self.progress = _progress

        return has_changed


class FancyLogger(object):
    """
    Defines a multiprocess logger object. Logger uses a redraw rate because of console flickering. That means it will
    not draw new messages or progress at the very time they are being logged but their timestamp will be captured at the
    right time. Logger will redraw at a given time period AND when new messages or progress are logged.
    If you still want to force redraw immediately (may produce flickering) then call 'flush' method.
    Logger uses one file handler and then uses standard output (stdout) to draw on screen.
    """

    queue = None
    "Handles all messages and progress to be sent to the logger process."

    default_message_number = 20
    "Default value for the logger configuration."
    default_exception_number = 5
    "Default value for the logger configuration."
    default_permanent_progressbar_slots = 0
    "Default value for the logger configuration."
    default_redraw_frequency_millis = 500
    "Default value for the logger configuration."
    default_level = logging.INFO
    "Default value for the logger configuration."
    default_task_millis_to_removal = 500
    "Default value for the logger configuration."

    def __init__(self,
                 message_number=default_message_number,
                 exception_number=default_exception_number,
                 permanent_progressbar_slots=default_permanent_progressbar_slots,
                 redraw_frequency_millis=default_redraw_frequency_millis,
                 level=default_level,
                 task_millis_to_removal=default_task_millis_to_removal):
        """
        Initializes a new logger and starts its process immediately using given configuration.
        :param message_number:              [Optional] Number of simultaneously displayed messages below progress bars.
        :param exception_number:            [Optional] Number of simultaneously displayed exceptions below messages.
        :param permanent_progressbar_slots: [Optional] The amount of vertical space (bar slots) to keep at all times,
                                            so the message logger will not move anymore if the bar number is equal or
                                            lower than this parameter.
        :param redraw_frequency_millis:     [Optional] Minimum time lapse in milliseconds between two redraws. It may be
                                            more because the redraw rate depends upon time AND method calls.
        :param level:                       [Optional] The logging level (from standard logging module).
        :param task_millis_to_removal:      [Optional] Minimum time lapse in milliseconds at maximum completion before
                                            a progress bar is removed from display. The progress bar may vanish at a
                                            further time as the redraw rate depends upon time AND method calls.
        """
        super(FancyLogger, self).__init__()

        if not self.queue:
            self.queue = Queue()
            self.process = MultiprocessingLogger(queue=self.queue,
                                                 level=level,
                                                 message_number=message_number,
                                                 exception_number=exception_number,
                                                 permanent_progressbar_slots=permanent_progressbar_slots,
                                                 redraw_frequency_millis=redraw_frequency_millis,
                                                 task_millis_to_removal=task_millis_to_removal)
            self.process.start()

    def flush(self):
        """
        Flushes the remaining messages and progress bars state by forcing redraw. Can be useful if you want to be sure
        that a message or progress has been updated in display at a given moment in code, like when you are exiting an
        application or doing some kind of synchronized operations.
        """
        self.queue.put(dill.dumps(FlushCommand()))

    def terminate(self):
        """
        Tells the logger process to exit immediately. If you do not call 'flush' method before, you may lose some
        messages of progresses that have not been displayed yet. This method blocks until logger process has stopped.
        """
        self.queue.put(dill.dumps(ExitCommand()))

        if self.process:
            self.process.join()

    def set_configuration(self,
                          message_number=default_message_number,
                          exception_number=default_exception_number,
                          permanent_progressbar_slots=default_permanent_progressbar_slots,
                          redraw_frequency_millis=default_redraw_frequency_millis,
                          level=default_level,
                          task_millis_to_removal=default_task_millis_to_removal):
        """
        Defines the current configuration of the logger. Can be used at any moment during runtime to modify the logger
        behavior.
        :param message_number:              [Optional] Number of simultaneously displayed messages below progress bars.
        :param exception_number:            [Optional] Number of simultaneously displayed exceptions below messages.
        :param permanent_progressbar_slots: [Optional] The amount of vertical space (bar slots) to keep at all times,
                                            so the message logger will not move anymore if the bar number is equal or
                                            lower than this parameter.
        :param redraw_frequency_millis:     [Optional] Minimum time lapse in milliseconds between two redraws. It may be
                                            more because the redraw rate depends upon time AND method calls.
        :param level:                       [Optional] The logging level (from standard logging module).
        :param task_millis_to_removal:      [Optional] Minimum time lapse in milliseconds at maximum completion before
                                            a progress bar is removed from display. The progress bar may vanish at a
                                            further time as the redraw rate depends upon time AND method calls.
        """
        self.queue.put(dill.dumps(SetConfigurationCommand(task_millis_to_removal=task_millis_to_removal,
                                                          level=level,
                                                          permanent_progressbar_slots=permanent_progressbar_slots,
                                                          message_number=message_number,
                                                          exception_number=exception_number,
                                                          redraw_frequency_millis=redraw_frequency_millis)))

    def set_level(self,
                  level,
                  console_only=False):
        """
        Defines the logging level (from standard logging module) for log messages.
        :param level:           Level of logging for the file logger.
        :param console_only:    [Optional] If True then the file logger will not be affected.
        """
        self.queue.put(dill.dumps(SetLevelCommand(level=level,
                                                  console_only=console_only)))

    def set_task_object(self,
                        task_id,
                        task_progress_object):
        """
        Defines a new progress bar with the given information using a TaskProgress object.
        :param task_id:                 Unique identifier for this progress bar. Will erase if already existing.
        :param task_progress_object:    TaskProgress object holding the progress bar information.
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
        Defines a new progress bar with the given information.
        :param task_id:         Unique identifier for this progress bar. Will erase if already existing.
        :param total:           The total number of iteration for this progress bar.
        :param prefix:          The text that should be displayed at the left side of the progress bar. Note that
                                progress bars will always stay left-aligned at the shortest possible.
        :param suffix:          [Optional] The text that should be displayed at the very right side of the progress bar.
        :param decimals:        [Optional] The number of decimals to display for the percentage.
        :param bar_length:      [Optional] The graphical bar size displayed on screen. Unit is character.
        :param keep_alive:      [Optional] Specify whether the progress bar should stay displayed forever once completed
                                or if it should vanish.
        :param display_time:    [Optional] Specify whether the duration since the progress has begun should be
                                displayed. Running time will be displayed between parenthesis, whereas it will be
                                displayed between brackets when the progress has completed.
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
        Defines the current progress for this progress bar id in iteration units (not percent).
        If the given id does not exist or the given progress is identical to the current, then does nothing.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param task_id:     Unique identifier for this progress bar. Will erase if already existing.
        :param progress:    Current progress in iteration units regarding its total (not percent).
        """
        self.queue.put(dill.dumps(UpdateProgressCommand(task_id=task_id,
                                                        progress=progress)))

    def debug(self, text):
        """
        Posts a debug message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param text: The text to log into file and console.
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.DEBUG)))

    def info(self, text):
        """
        Posts an info message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param text: The text to log into file and console.
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.INFO)))

    def warning(self, text):
        """
        Posts a warning message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param text: The text to log into file and console.
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.WARNING)))

    def error(self, text):
        """
        Posts an error message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param text: The text to log into file and console.
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.ERROR)))

    def critical(self, text):
        """
        Posts a critical message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param text: The text to log into file and console.
        """
        self.queue.put(dill.dumps(LogMessageCommand(text=text, level=logging.CRITICAL)))

    def throw(self, stacktrace):
        """
        Sends an exception to the logger so it can display it as a special message. Prevents console refresh cycles from
        hiding exceptions that could be thrown by processes.
        :param stacktrace: Stacktrace string as returned by 'traceback.format_exc()' in an 'except' block.
        """
        self.queue.put(dill.dumps(StacktraceCommand(pid=os.getpid(), stacktrace=stacktrace)))

    # --------------------------------------------------------------------
    # Iterator implementation
    def progress(self,
                 enumerable,
                 task_progress_object=None):
        """
        Enables the object to be used as an iterator. Each iteration will produce a progress update in the logger.
        :param enumerable:              Collection to iterate over.
        :param task_progress_object:    [Optional] TaskProgress object holding the progress bar information.
        :return:                        The logger instance.
        """
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
        """
        Enables the object to be used as an iterator. Each iteration will produce a progress update in the logger.
        :return: The logger instance.
        """
        return self

    def __next__(self):
        """
        Enables the object to be used as an iterator. Each iteration will produce a progress update in the logger.
        :return: The current object of the iterator.
        """
        if self.index >= self.list_length:
            raise StopIteration
        else:
            self.index += 1
            self.update(task_id=self.task_id,
                        progress=self.index)

            return self.list[self.index - 1]
    # ---------------------------------------------------------------------
