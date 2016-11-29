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
    """
    Gives the current time in milliseconds.
    :return: The current time in milliseconds.
    """
    return time.time() * 1000


class MultiprocessingLogger(Process):
    """
    Core of the multiprocess logger library. Handles message and progress queue from other processes and does all the
    rendering on the screen. Handles the file logger.
    """

    queue = None
    "Queue to receive orders from all processes."
    log = None
    "The python logging's logger for files only."
    os_flush_command = 'cls' if os.name == 'nt' else 'echo -e "\\033c\\e[3J"'
    "The clear command on Unix and cls command on Windows."
    longest_bar_prefix_size = 0
    "Defines the longest task prefix in order to align progress bars to the left."

    refresh_timer = millis()
    "The redraw timer."
    changes_made = False
    "Indicates if a new message has been posted or if a task has updated. If none, then there is no need to redraw."

    tasks = OrderedDict()
    "List of tasks identified by an id. One progress bar per task."
    to_delete = []
    "When a task is marked for deletion, it is added in this list for next redraw to process it."
    exceptions = None
    """
    When a process sends an exception to the logger, the stacktrace will be permanently displayed below log messages."
    So the user can see that a process has failed even if the console is refreshing.
    """

    # ------------- Customizable parameters
    messages = None
    "Cycling list of log messages below the progress bars."
    permanent_progressbar_slots = None
    """
    Defines the vertical space (in bar slots) to keep at all times between progress bars section and messages
    section.
    """
    redraw_frequency_millis = None
    """
    Defines the minimum time in milliseconds between two redraws. It may be more because the redraw rate depends
    upon time AND method calls.
    """
    level = None
    "The logging level (from standard logging module)."
    task_millis_to_removal = None
    """
    Minimum number of milliseconds at maximum completion before a progress bar is removed from display.
    The progress bar may vanish at a further time as the redraw rate depends upon time AND method calls.
    """
    # -------------

    def __init__(self,
                 queue,
                 message_number,
                 exception_number,
                 permanent_progressbar_slots,
                 redraw_frequency_millis,
                 level,
                 task_millis_to_removal):
        """
        Defines the current configuration of the logger and the queue to receive messages from remote processes. Must be
        used one time only.
        :param queue:                       Queue to receive orders from all processes. Must be the same object
                                            reference as processes that send log messages and progress updates.
        :param message_number:              Number of simultaneously displayed messages below progress bars.
        :param exception_number:            Number of simultaneously displayed exceptions below messages.
        :param permanent_progressbar_slots: The amount of vertical space (bar slots) to keep at all times,
                                            so the message logger will not move anymore if the bar number is equal or
                                            lower than this parameter.
        :param redraw_frequency_millis:     Minimum time lapse in milliseconds between two redraws. It may be
                                            more because the redraw rate depends upon time AND method calls.
        :param level:                       The logging level (from standard logging module).
        :param task_millis_to_removal:      Minimum time lapse in milliseconds at maximum completion before
                                            a progress bar is removed from display. The progress bar may vanish at a
                                            further time as the redraw rate depends upon time AND method calls.
        """
        super(MultiprocessingLogger, self).__init__()

        self.queue = queue

        self.set_configuration(SetConfigurationCommand(task_millis_to_removal=task_millis_to_removal,
                                                       level=level,
                                                       permanent_progressbar_slots=permanent_progressbar_slots,
                                                       message_number=message_number,
                                                       exception_number=exception_number,
                                                       redraw_frequency_millis=redraw_frequency_millis))

    def set_configuration(self, command):
        """
        Defines the current configuration of the logger. Can be used at any moment during runtime to modify the logger
        behavior.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        self.permanent_progressbar_slots = command.permanent_progressbar_slots
        self.redraw_frequency_millis = command.redraw_frequency_millis
        self.level = command.level
        self.task_millis_to_removal = command.task_millis_to_removal

        # Do not clear exceptions if the user changes the configuration during runtime
        if self.exceptions:
            # If exceptions already exists
            current_length = len(self.exceptions)

            if command.exception_number < current_length:
                # Delete exceptions from the end to desired index to keep most recent exceptions
                range_to_delete = current_length - command.exception_number
                for i in range(range_to_delete):
                    del self.exceptions[-1]

            elif command.exception_number > current_length:
                # Add empty slots at the end
                range_to_add = command.exception_number - current_length
                for i in range(range_to_add):
                    self.exceptions.append('')
        else:
            # Else, initialize a new list
            self.exceptions = command.exception_number * ['']

        # Do not clear messages if the user changes the configuration during runtime
        if self.messages:
            # If messages already exists
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
        """
        The main loop for the logger process. Will receive remote processes orders one by one and wait for the next one.
        Then return from this method when the main application calls for exit, which is a regular command.
        """
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
                    self.debug(command=o)
                elif o.level == logging.INFO:
                    self.info(command=o)
                elif o.level == logging.WARNING:
                    self.warning(command=o)
                elif o.level == logging.ERROR:
                    self.error(command=o)
                elif o.level == logging.CRITICAL:
                    self.critical(command=o)

            elif isinstance(o, UpdateProgressCommand):
                self.update(command=o)

            elif isinstance(o, NewTaskCommand):
                self.set_task(command=o)

            elif isinstance(o, FlushCommand):
                self.flush()

            elif isinstance(o, StacktraceCommand):
                self.throw(command=o)

            elif isinstance(o, SetConfigurationCommand):
                self.set_configuration(command=o)

            elif isinstance(o, ExitCommand):
                return

            elif isinstance(o, SetLevelCommand):
                self.set_level(command=o)

    def longest_bar_prefix_value(self):
        """
        Calculates the longest progress bar prefix in order to keep all progress bars left-aligned.
        :return: Length of the longest task prefix in character unit.
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
        Calculates the equivalent time of the given milliseconds into a human readable string from seconds to weeks.
        :param time_millis: Time in milliseconds using python time library.
        :return:            Human readable time string. Example: 2 min 3 s.
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
        Draws a progress bar on screen based on the given information using standard output (stdout).
        :param task: TaskProgress object containing all required information to draw a progress bar at the given state.
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
        Clears the console and performs a complete redraw of all progress bars and then awaiting logger messages if the
        minimum time elapsed since the last redraw is enough.
        """

        # Check if the refresh time lapse has elapsed and if a change requires to redraw
        lapse_since_last_refresh = millis() - self.refresh_timer
        if not lapse_since_last_refresh > self.redraw_frequency_millis or not self.changes_made:
            return
        # If yes, then reset change indicator and chrono
        self.changes_made = False
        self.refresh_timer = millis()

        # Clear the system console
        os.system(self.os_flush_command)

        # For each task, check if it has complete. If so, start its chrono
        # Once the chrono has reached the maximum timeout time, delete the task
        # For the other tasks that have not completed yet, redraw them

        # Delete tasks that have been marked for deletion
        if len(self.to_delete) > 0:
            for task_id in self.to_delete:
                del self.tasks[task_id]
            self.to_delete = []
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
                    self.to_delete.append(task_id)

            # Redraw the task's progress bar
            self.print_progress_bar(task=task)

        # Keep space for future tasks if needed
        slots = self.permanent_progressbar_slots - len(self.tasks)
        if slots > 0:
            for i in range(slots):
                sys.stdout.write('\n\t\t---\n')

        # Draw some space between bars and messages
        if len(self.messages) > 0:
            if self.permanent_progressbar_slots > 0 or len(self.tasks) > 0:
                sys.stdout.write('\n\n')

            # Print all the last log messages
            for m in self.messages:
                sys.stdout.write(m)

        # Draw some space between messages and exceptions
        if len(self.exceptions) > 0:
            if len(self.messages) > 0:
                sys.stdout.write('\n\n')

            # Print all the exceptions
            for ex in self.exceptions:
                sys.stdout.write(ex)

    def append_message(self,
                       message):
        """
        Appends the given message at the end of the message list and delete the oldest one (top most).
        :param message: The formatted text to log.
        """
        # Delete the first message of the list
        if len(self.messages) > 0:
            del self.messages[0]

        # Append the new message at the end
        self.messages.append(message)
        self.changes_made = True

        # Redraw
        self.redraw()

    def append_exception(self,
                         stacktrace):
        """
        Appends the given exception at the top of the exception list and delete the oldest one (bottom most).
        :param stacktrace: Stacktrace string as returned by 'traceback.format_exc()' in an 'except' block.
        """
        # Delete the last message of the list
        if len(self.exceptions) > 0:
            del self.exceptions[-1]

        # Append the new message at the top
        self.exceptions.insert(0, stacktrace)
        self.changes_made = True

        # Redraw
        self.redraw()

    def flush(self):
        """
        Flushes the remaining messages, exceptions and progress bars state by forcing redraw. Can be useful if you want
        to be sure that a message or progress has been updated in display at a given moment in code, like when you are
        exiting an application or doing some kind of synchronized operations.
        """
        self.refresh_timer = 0

        # Redraw
        self.changes_made = True
        self.redraw()

    @staticmethod
    def current_timestamp():
        """
        Gets the current timestamp.
        :return: The timestamp string to append to log messages.
        """
        return time.strftime('%d %B %Y %H:%M:%S').lower()

    def set_level(self, command):
        """
        Defines the logging level (from standard logging module) for log messages.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        if not command.console_only:
            self.log.setLevel(command.level)

        self.level = command.level

    def set_task(self, command):
        """
        Defines a new progress bar with the given information.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        self.tasks[command.task_id] = command.task

        self.longest_bar_prefix_size = self.longest_bar_prefix_value()

        # Redraw
        self.changes_made = True
        self.redraw()

    def update(self, command):
        """
        Defines the current progress for this progress bar id in iteration units (not percent).
        If the given id does not exist or the given progress is identical to the current, then does nothing.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        if command.task_id in self.tasks and self.tasks[command.task_id].set_progress(command.progress):

            # Redraw
            self.changes_made = True
            self.redraw()

    def debug(self, command):
        """
        Posts a debug message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        if self.level == logging.DEBUG:
            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'DEBUG', command.text)
            self.append_message(message)

            # Redraw
            self.changes_made = True
            self.redraw()

        self.log.debug('\t{}'.format(command.text))

    def info(self, command):
        """
        Posts an info message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        if (self.level == logging.DEBUG
                or self.level == logging.INFO):

            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'INFO', command.text)
            self.append_message(message)

            # Redraw
            self.changes_made = True
            self.redraw()

        self.log.info('\t\t{}'.format(command.text))

    def warning(self, command):
        """
        Posts a warning message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        if (self.level == logging.DEBUG
                or self.level == logging.INFO
                or self.level == logging.WARNING):

            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'WARNING', command.text)
            self.append_message(message)

            # Redraw
            self.changes_made = True
            self.redraw()

        self.log.warning('\t{}'.format(command.text))

    def error(self, command):
        """
        Posts an error message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        if (self.level == logging.DEBUG
                or self.level == logging.INFO
                or self.level == logging.WARNING
                or self.level == logging.ERROR):

            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'ERROR', command.text)
            self.append_message(message)

            # Redraw
            self.changes_made = True
            self.redraw()

        self.log.error('\t{}'.format(command.text))

    def critical(self, command):
        """
        Posts a critical message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        if (self.level == logging.DEBUG
                or self.level == logging.INFO
                or self.level == logging.WARNING
                or self.level == logging.ERROR
                or self.level == logging.CRITICAL):

            message = '{} [{}]\t{}\n'.format(self.current_timestamp(), 'CRITICAL', command.text)
            self.append_message(message)

            # Redraw
            self.changes_made = True
            self.redraw()

        self.log.critical('\t{}'.format(command.text))

    def throw(self, command):
        """
        Posts an exception's stacktrace string as returned by 'traceback.format_exc()' in an 'except' block.
        :param command: The command object that holds all the necessary information from the remote process.
        """
        message = '{} [{}]\t[Process {}{}]:\n{}\n'.format(self.current_timestamp(), 'EXCEPTION', command.pid, ' - {}'.format(command.process_title) if command.process_title else '', command.stacktrace)
        self.append_exception(message)

        # Redraw
        self.changes_made = True
        self.redraw()

        self.log.critical('\t{}'.format(message))
