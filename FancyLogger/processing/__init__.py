#!/bin/env/python
# coding: utf-8

import logging
import os
import sys
import time
import dill
from collections import OrderedDict
from logging import getLogger, Formatter
from logging.handlers import RotatingFileHandler
from multiprocessing import Process

from ..commands import *


def millis():
    return time.time() * 1000


class MultiprocessingLogger(Process):
    """
    Handle file logging along with cycling message logger and progress bars
    """

    # Queue meant to receive orders from all processes
    queue = None
    # The logging.log for files only
    log = None
    os_flush_command = 'cls' if os.name == 'nt' else 'clear'
    # Defines the longest task prefix in order to align progress bars
    longest_bar_prefix_size = 0

    # The redraw chrono
    refresh_chrono = millis()
    # Indicates if a new message has been posted or if a task has updated. If none, then there is no need to redraw
    changes_made = False

    # List of tasks identified by an id. One progress bar per task
    tasks = OrderedDict()
    # When a task is marked for deletion, it is added in this list for next redraw to process it
    todelete = []

    # ------------- Customizable parameters
    # Cycling list of log messages below the progress bars
    messages = None
    # Defines the vertical space (in bar number) to keep at all times between progress bars section and messages section
    permanent_progressbar_slots = None
    # Defines the minimum time in milliseconds between two redrawings. It may be more because the redraw rate depends
    # upon chrono AND method calls
    redraw_frequency_millis = None
    # Logging level
    level = None
    # Minimum number of seconds at maximum completion before a progress bar is removed from display
    # The progress bar may vanish at a further time as the redraw rate depends upon chrono AND method calls
    task_millis_to_removal = None
    # -------------

    def __init__(self,
                 queue,
                 message_number,
                 permanent_progressbar_slots,
                 redraw_frequency_millis,
                 level,
                 task_millis_to_removal):
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
        super(MultiprocessingLogger, self).__init__()

        self.queue = queue

        self.set_configuration(SetConfigurationCommand(task_millis_to_removal=task_millis_to_removal,
                                                       level=level,
                                                       permanent_progressbar_slots=permanent_progressbar_slots,
                                                       message_number=message_number,
                                                       redraw_frequency_millis=redraw_frequency_millis))

    def set_configuration(self, command):

        self.permanent_progressbar_slots = command.permanent_progressbar_slots
        self.redraw_frequency_millis = command.redraw_frequency_millis
        self.level = command.level
        self.task_millis_to_removal = command.task_millis_to_removal

        # If messages already exists
        if self.messages:
            current_length = len(self.messages)

            if command.message_number < current_length:
                # Delete messages from 0 to desired index to keep most recent messages
                range_to_delete = current_length - command.message_number
                for i in range(range_to_delete):
                    del self.messages[0]

            elif command.message_number > current_length:
                # Add empty slots at 0
                range_to_add = command.message_number - current_length
                for i in range(range_to_add):
                    self.messages.insert(0, '')
        else:
            # Else, initialize a new list
            self.messages = command.message_number * ['']

    def run(self):

        # Initialize the logging.log
        self.log = getLogger()

        file_handler = RotatingFileHandler('logging.log',
                                           maxBytes=10485760,  # 10 MB
                                           backupCount=5)
        file_handler.setFormatter(Formatter('%(asctime)s [%(levelname)s] %(message)s'))

        self.log.addHandler(file_handler)

        self.log.setLevel(logging.INFO)

        while True:
            o = dill.loads(self.queue.get())

            if isinstance(o, LogMessageCommand):
                if o.level == logging.DEBUG:
                    self.debug(text=o.text)
                elif o.level == logging.INFO:
                    self.info(text=o.text)
                elif o.level == logging.WARNING:
                    self.warning(text=o.text)
                elif o.level == logging.ERROR:
                    self.error(text=o.text)
                elif o.level == logging.CRITICAL:
                    self.critical(text=o.text)

            elif isinstance(o, UpdateProgressCommand):
                self.update(task_id=o.task_id,
                            progress=o.progress)

            elif isinstance(o, NewTaskCommand):
                self.set_task(task_id=o.task_id,
                              task=o.task)

            elif isinstance(o, FlushCommand):
                self.flush()

            elif isinstance(o, SetConfigurationCommand):
                self.set_configuration(command=o)

            elif isinstance(o, ExitCommand):
                return

            elif isinstance(o, SetLevelCommand):
                self.set_level(level=o.level,
                               console_only=o.console_only)

    def longest_bar_prefix_value(self):
        """
        Calculates the longest task prefix in order to keep all progress bars left-aligned
        :return: Length of the longest task prefix (number of chars)
        """
        longest = 0
        for key, t in self.tasks.items():
            size = len(t.prefix)
            if size > longest:
                longest = size

        return longest

    @staticmethod
    def millis_to_human_readable(time_millis):
        """
        Calculates the equivalent time of given milliseconds into human readable time
        :param time_millis: Time in milliseconds using time library
        :return:            Human readable rime. Example: 2 min 03 s
        """
        weeks = 0
        days = 0
        hours = 0
        minutes = 0
        seconds = round(time_millis / 1000)

        while seconds > 59:
            seconds -= 60
            minutes += 1

        while minutes > 59:
            minutes -= 60
            hours += 1

        while hours > 23:
            hours -= 24
            days += 1

        while days > 6:
            hours -= 7
            weeks += 1

        if weeks > 0:
            output = '{} w {} d {} h {} min {} s'.format(weeks, days, hours, minutes, seconds)
        elif days > 0:
            output = '{} d {} h {} min {} s'.format(days, hours, minutes, seconds)
        elif hours > 0:
            output = '{} h {} min {} s'.format(hours, minutes, seconds)
        elif minutes > 0:
            output = '{} min {} s'.format(minutes, seconds)
        elif seconds > 0:
            output = '{} s'.format(seconds)
        else:
            output = ''

        return output

    def print_progress_bar(self, task):
        """
        Draws a progress bar based on given information
        :param task:    Contains all required information to draw a progress bar at the given state
        :return:
        """
        str_format = "{0:." + str(task.decimals) + "f}"
        percents = str_format.format(100 * (task.progress / float(task.total)))
        filled_length = int(round(task.bar_length * task.progress / float(task.total)))
        bar = '█' * filled_length + '-' * (task.bar_length - filled_length)

        # Build elapsed time if needed
        elapsed_time = None

        if task.display_time:
            if task.end_time:
                # If the task has ended, stop the chrono
                if not task.elapsed_time_at_end:
                    task.elapsed_time_at_end = self.millis_to_human_readable(task.end_time - task.begin_time)
                elapsed_time = task.elapsed_time_at_end
            else:
                # If task is new then start the chrono
                if not task.begin_time:
                    task.begin_time = millis()
                elapsed_time = self.millis_to_human_readable(millis() - task.begin_time)

        prefix_pattern = '%{}s'.format(self.longest_bar_prefix_size)
        time_container_pattern = '(%s)' if task.display_time and not task.end_time else '[%s]'

        if len(task.suffix) > 0 and task.display_time:
            sys.stdout.write('\n {} |%s| %3s %% {} - %s'.format(prefix_pattern, time_container_pattern)
                             % (task.prefix, bar, percents, elapsed_time, task.suffix))
        elif len(task.suffix) > 0 and not task.display_time:
            sys.stdout.write('\n {} |%s| %3s %% - %s'.format(prefix_pattern)
                             % (task.prefix, bar, percents, task.suffix))
        elif task.display_time and not len(task.suffix) > 0:
            sys.stdout.write('\n {} |%s| %3s %% {}'.format(prefix_pattern, time_container_pattern)
                             % (task.prefix, bar, percents, elapsed_time))
        else:
            sys.stdout.write('\n {} |%s| %3s %%'.format(prefix_pattern)
                             % (task.prefix, bar, percents))

        sys.stdout.write('\n')
        sys.stdout.flush()

    def redraw(self):
        """
        Clear the console and perform a complete redraw of progress bars and messages if the minimum time elapsed since
        the last redraw is enough
        :return:
        """

        # Check if the refresh time lapse has elapsed and if a change requires to redraw
        lapse_since_last_refresh = millis() - self.refresh_chrono
        if not lapse_since_last_refresh > self.redraw_frequency_millis or not self.changes_made:
            return
        # If yes, then reset change indicator and chrono
        self.changes_made = False
        self.refresh_chrono = millis()

        # Clear the system console
        os.system(self.os_flush_command)

        # For each task, check if it has complete. If so, start its chrono
        # Once the chrono has reached the maximum timeout time, delete the task
        # For the other tasks that have not completed yet, redraw them

        # Delete tasks that have been marked for deletion
        if len(self.todelete) > 0:
            for task_id in self.todelete:
                del self.tasks[task_id]
            self.todelete = []
            # If a task has been deleted, recalculate the maximum prefix length to keep progress bars aligned
            self.longest_bar_prefix_size = self.longest_bar_prefix_value()

        for task_id, task in self.tasks.items():

            # If a task has completed, force its value to its maximum to prevent progress bar overflow
            # Then start its timeout chrono
            if task.progress >= task.total and not task.keep_alive:
                # Prevent bar overflow
                task.progress = task.total

                # Start task's timeout chrono
                if not task.timeout_chrono:
                    task.timeout_chrono = millis()
                # If task's chrono has reached the maximum timeout time, mark it for deletion
                elif millis() - task.timeout_chrono >= self.task_millis_to_removal:
                    self.todelete.append(task_id)

            # Redraw the task's progress bar
            self.print_progress_bar(task=task)

        # Keep space for future tasks if needed
        slots = self.permanent_progressbar_slots - len(self.tasks)
        if slots > 0:
            for i in range(slots):
                sys.stdout.write('\n\t\t---\n')

        # Draw some space between bars and messages
        if self.permanent_progressbar_slots > 0 or len(self.tasks) > 0:
            sys.stdout.write('\n\n')

        # Print all the last log messages
        for m in self.messages:
            sys.stdout.write(m)

    def append_message(self,
                       message):
        """
        Append the given message at the end of the message list and delete the oldest one
        :param message:
        :return:
        """
        # Delete the first message of the list
        del self.messages[0]

        # Append the new message at the end
        self.messages.append(message)
        self.changes_made = True

        # Redraw
        self.redraw()

    def flush(self):
        """
        Flushes the remaining messages by forcing redraw. Can be useful if you want to be sure a message or progress has
        been updated in display, like when you are exiting an application.
        :return:
        """
        self.refresh_chrono = 0
        self.changes_made = True

        self.redraw()

    @staticmethod
    def current_timestamp():
        """
        Get the current time for log messages
        :return:
        """
        return time.strftime('%d %B %Y %H:%M:%S').lower()

    def set_level(self,
                  level,
                  console_only=False):
        """
        Sets the logging level for log messages
        :return:
        """
        if not console_only:
            self.log.setLevel(level)

        self.level = level

    def set_task(self,
                 task_id,
                 task):
        """
        Defines a new task with the given information
        :param task_id:     To be registered in task list
        :param task:        Task object holding information
        :return:
        """
        self.tasks[task_id] = task

        self.longest_bar_prefix_size = self.longest_bar_prefix_value()

        self.changes_made = True

    def update(self,
               task_id,
               progress):
        """
        If the given id exists, update the task's progress and trigger redrawing
        :param task_id:     Task to update (must be existing)
        :param progress:    Progress relative to the 'task.total' attribute
        :return:
        """
        if task_id in self.tasks and self.tasks[task_id].set_progress(progress):
            self.changes_made = True

            # Redraw
            self.redraw()

    def debug(self, text):
        """
        Posts a debug message adding a timestamp and logging level
        :param text:
        :return:
        """
        if self.level == logging.DEBUG:
            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'DEBUG', text)
            self.append_message(message)

        self.log.debug('\t{}'.format(text))

    def info(self, text):
        """
        Posts an info message adding a timestamp and logging level
        :param text:
        :return:
        """
        if (self.level == logging.DEBUG
                or self.level == logging.INFO):

            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'INFO', text)
            self.append_message(message)

        self.log.info('\t\t{}'.format(text))

    def warning(self, text):
        """
        Posts a warning message adding a timestamp and logging level
        :param text:
        :return:
        """
        if (self.level == logging.DEBUG
                or self.level == logging.INFO
                or self.level == logging.WARNING):

            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'WARNING', text)
            self.append_message(message)

        self.log.warning('\t{}'.format(text))

    def error(self, text):
        """
        Posts an error message adding a timestamp and logging level
        :param text:
        :return:
        """
        if (self.level == logging.DEBUG
                or self.level == logging.INFO
                or self.level == logging.WARNING
                or self.level == logging.ERROR):

            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'ERROR', text)
            self.append_message(message)

        self.log.error('\t{}'.format(text))

    def critical(self, text):
        """
        Posts a critical message adding a timestamp and logging level
        :param text:
        :return:
        """
        if (self.level == logging.DEBUG
                or self.level == logging.INFO
                or self.level == logging.WARNING
                or self.level == logging.ERROR
                or self.level == logging.CRITICAL):

            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'CRITICAL', text)
            self.append_message(message)

        self.log.critical('\t{}'.format(text))
