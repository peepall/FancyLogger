#!/bin/env/python
# -*- coding: utf-8 -*-

import time, sys, os, logging, uuid
from collections import OrderedDict

from logging import getLogger, Formatter
from logging.handlers import RotatingFileHandler


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


    def setProgress(self, progress):
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

        hasChanged = self.progress != _progress

        if hasChanged:
            self.progress = _progress

        return hasChanged


class FancyLogger(object):
    """
    Handle file logging along with cycling message logger and progress bars
    """

    # The logging.log for files only
    log = None
    os_flush_command = 'cls' if os.name == 'nt' else 'clear'
    # Defines the longest task prefix in order to align progress bars
    longest_bar_prefix_size = 0

    # The redraw chrono
    refresh_chrono = time.time() * 1000
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
    # Defines the minimum time in milliseconds between two redrawings. It may be more because the redraw rate depends upon chrono AND method calls
    redraw_frequency_millis = None
    # Logging level
    level = None
    # Minimum number of seconds at maximum completion before a progress bar is removed from display
    # The progress bar may vanish at a further time as the redraw rate depends upon chrono AND method calls
    task_millis_to_removal = None
    # -------------


    @classmethod
    def init(cls,
             message_number=20,
             permanent_progressbar_slots=0,
             redraw_frequency_millis=500,
             level=logging.INFO,
             task_millis_to_removal=500):
        """
        Defines the logger behavior
        :param message_number:                  Number of simultaneous messages below the progress bars
        :param permanent_progressbar_slots:     The amount of vertical space (in bar number) to keep at all times between progress bars section and messages section
        :param redraw_frequency_millis:         Minimum time lapse in milliseconds between two redrawings. It may be more because the redraw rate depends upon chrono AND method calls
        :param level:                           The logging level (from standard logging module)
        :param task_millis_to_removal:          Minimum number of milliseconds at maximum completion before a progress bar is removed from display. The progress bar may vanish at a further time as the redraw rate depends upon chrono AND method calls
        :return:
        """
        cls.permanent_progressbar_slots = permanent_progressbar_slots
        cls.redraw_frequency_millis = redraw_frequency_millis
        cls.level = level
        cls.task_millis_to_removal = task_millis_to_removal

        # If messages already exists
        if cls.messages:
            current_length = len(cls.messages)

            if message_number < current_length:
                # Delete messages from 0 to desired index to keep most recent messages
                range_to_delete = current_length - message_number
                for i in range(range_to_delete):
                    del cls.messages[0]

            elif message_number > current_length:
                # Add empty slots at 0
                range_to_add = message_number - current_length
                for i in range(range_to_add):
                    cls.messages.insert(0, '')
        else:
            # Else, initialize a new list
            cls.messages = message_number * ['']

        # Initialize the logging.log
        cls.log = getLogger()

        fileHandler = RotatingFileHandler('logging.log',
                                          maxBytes=10485760, # 10 MB
                                          backupCount=5)
        fileHandler.setFormatter(Formatter('%(asctime)s [%(levelname)s] %(message)s'))

        cls.log.addHandler(fileHandler)

        cls.log.setLevel(logging.INFO)


    @classmethod
    def flush(cls):
        """
        Flushes the remaining messages by forcing redraw. Can be useful if you want to be sure a message or progress has
        been updated in display, like when you are exiting an application.
        :return:
        """
        cls.refresh_chrono = 0
        cls.changes_made = True

        cls.redraw()


    @classmethod
    def currentTime(cls):
        """
        Get the current time for log messages
        :return:
        """
        return time.strftime('%d %B %Y %H:%M:%S').lower()


    @classmethod
    def setLevel(cls,
                 level,
                 console_only=False):
        """
        Sets the logging level for log messages
        :return:
        """
        if not console_only:
            cls.log.setLevel(level)

        cls.level = level


    @classmethod
    def longestBarPrefixValue(cls):
        """
        Calculates the longest task prefix in order to keep all progress bars left-aligned
        :return: Length of the longest task prefix (number of chars)
        """
        max = 0
        for id, t in cls.tasks.items():
            size = len(t.prefix)
            if size > max:
                max = size

        return max


    @classmethod
    def millisToHumanReadable(cls, time_millis):
        """
        Calculates the equivalent time of given milliseconds into human readable time
        :param time_millis:
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


    @classmethod
    def printProgressBar(cls, task):
        """
        Draws a progress bar based on given information
        :param iteration:   Required  : current iteration (Int)
        :param total:       Required  : total iterations (Int)
        :param prefix:      Optional  : prefix string (Str)
        :param suffix:      Optional  : suffix string (Str)
        :param decimals:    Optional  : positive number of decimals in percent complete (Int)
        :param bar_length:  Optional  : character length of bar (Int)
        :return:
        """
        str_format = "{0:." + str(task.decimals) + "f}"
        percents = str_format.format(100 * (task.progress / float(task.total)))
        filled_length = int(round(task.bar_length * task.progress / float(task.total)))
        bar = '█' * filled_length + '-' * (task.bar_length - filled_length)

        # Build elapsed time if needed
        if task.display_time:
            if task.end_time:
                # If the task has ended, stop the chrono
                if not task.elapsed_time_at_end:
                    task.elapsed_time_at_end = cls.millisToHumanReadable(task.end_time - task.begin_time)
                elapsed_time = task.elapsed_time_at_end
            else:
                # If task is new then start the chrono
                if not task.begin_time:
                    task.begin_time = time.time() * 1000
                elapsed_time = cls.millisToHumanReadable(time.time() * 1000 - task.begin_time)

        prefix_pattern = '%{}s'.format(cls.longest_bar_prefix_size)
        time_container_pattern = '(%s)' if task.display_time and not task.end_time else '[%s]'

        if len(task.suffix) > 0 and task.display_time:
            sys.stdout.write('\n {} |%s| %3s %% {} - %s'.format(prefix_pattern, time_container_pattern) % (task.prefix, bar, percents, elapsed_time, task.suffix))
        elif len(task.suffix) > 0 and not task.display_time:
            sys.stdout.write('\n {} |%s| %3s %% - %s'.format(prefix_pattern) % (task.prefix, bar, percents, task.suffix))
        elif task.display_time and not len(task.suffix) > 0:
            sys.stdout.write('\n {} |%s| %3s %% {}'.format(prefix_pattern, time_container_pattern) % (task.prefix, bar, percents, elapsed_time))
        else:
            sys.stdout.write('\n {} |%s| %3s %%'.format(prefix_pattern) % (task.prefix, bar, percents))

        sys.stdout.write('\n')
        sys.stdout.flush()

    @classmethod
    def setTaskObject(cls,
                      task_id,
                      task_progress_object):
        """
        Defines a new task with the given information using a TaskProgress object
        :param task_id:                 To be registered in task list
        :param task_progress_object:    Total number of iterations before completed
        :return:
        """
        cls.setTask(task_id, task_progress_object.total,
                    task_progress_object.prefix,
                    task_progress_object.suffix,
                    task_progress_object.decimals,
                    task_progress_object.bar_length,
                    task_progress_object.keep_alive,
                    task_progress_object.display_time)


    @classmethod
    def setTask(cls,
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
        :keep_alive:        Defines if the progress bar should stay display even when completed
        :display_time:      Display the elapsed time in human readable format after the suffix
        :return:
        """
        cls.tasks[task_id] = TaskProgress(total,
                                          prefix,
                                          suffix,
                                          decimals,
                                          bar_length,
                                          keep_alive,
                                          display_time)

        cls.longest_bar_prefix_size = cls.longestBarPrefixValue()

        cls.changes_made = True


    @classmethod
    def update(cls,
               task_id,
               progress):
        """
        If the given id exists, update the task's progress and trigger redrawing
        :param task_id:     Task to update (must be existing)
        :param progress:    Progress relative to the 'task.total' attribute
        :return:
        """
        # If the given task id exists, update the task
        if task_id in cls.tasks and cls.tasks[task_id].setProgress(progress):
            cls.changes_made = True

            # Redraw
            cls.redraw()


    @classmethod
    def redraw(cls):
        """
        Clear the console and perform a complete redraw of progress bars and messages if the minimum time elapsed since
        the last redraw is enough
        :return:
        """

        # Check if the refresh time lapse has elapsed and if a change requires to redraw
        lapse_since_last_refresh = time.time() * 1000 - cls.refresh_chrono
        if not lapse_since_last_refresh > cls.redraw_frequency_millis or not cls.changes_made:
            return
        # If yes, then reset change indicator and chrono
        cls.changes_made = False
        cls.refresh_chrono = time.time() * 1000

        # Clear the system console
        os.system(cls.os_flush_command)

        # For each task, check if it has complete. If so, start its chrono
        # Once the chrono has reached the maximum timeout time, delete the task
        # For the other tasks that have not completed yet, redraw them

        # Delete tasks that have been marked for deletion
        if len(cls.todelete) > 0:
            for id in cls.todelete:
                del cls.tasks[id]
            cls.todelete = []
            # If a task has been deleted, recalculate the maximum prefix length to keep progress bars aligned
            cls.longest_bar_prefix_size = cls.longestBarPrefixValue()


        for id, task in cls.tasks.items():

            # If a task has completed, force its value to its maximum to prevent progress bar overflow
            # Then start its timeout chrono
            if task.progress >= task.total and not task.keep_alive:
                # Prevent bar overflow
                task.progress = task.total

                # Start task's timeout chrono
                if not task.timeout_chrono:
                    task.timeout_chrono = time.time() * 1000
                # If task's chrono has reached the maximum timeout time, mark it for deletion
                elif time.time() * 1000 - task.timeout_chrono >= cls.task_millis_to_removal:
                    cls.todelete.append(id)

            # Redraw the task's progress bar
            cls.printProgressBar(task=task)


        # Keep space for future tasks if needed
        slots = cls.permanent_progressbar_slots - len(cls.tasks)
        if slots > 0:
            for i in range(slots):
                sys.stdout.write('\n\t\t---\n')

        # Draw some space between bars and messages
        if cls.permanent_progressbar_slots > 0 or len(cls.tasks) > 0:
            sys.stdout.write('\n\n')

        # Print all the last log messages
        for m in cls.messages:
            sys.stdout.write(m)


    @classmethod
    def appendMessage(cls,
                      message):
        """
        Append the given message at the end of the message list and delete the oldest one
        :param message:
        :return:
        """
        # Delete the first message of the list
        del cls.messages[0]

        # Append the new message at the end
        cls.messages.append(message)
        cls.changes_made = True

        # Redraw
        cls.redraw()


    @classmethod
    def debug(cls, text):
        """
        Posts a debug message adding a timestamp and logging level
        :param text:
        :return:
        """
        if cls.level == logging.DEBUG:
            message = '{} [{}]\t{}\n'.format(cls.currentTime(), 'DEBUG', text)
            cls.appendMessage(message)

        cls.log.debug('\t{}'.format(text))


    @classmethod
    def info(cls, text):
        """
        Posts an info message adding a timestamp and logging level
        :param text:
        :return:
        """
        if ( cls.level == logging.DEBUG
                or cls.level == logging.INFO ):
            message = '{} [{}]\t{}\n'.format(cls.currentTime(), 'INFO', text)
            cls.appendMessage(message)

        cls.log.info('\t\t{}'.format(text))


    @classmethod
    def warning(cls, text):
        """
        Posts a warning message adding a timestamp and logging level
        :param text:
        :return:
        """
        if ( cls.level == logging.DEBUG
                or cls.level == logging.INFO
                or cls.level == logging.WARNING ):
            message = '{} [{}]\t{}\n'.format(cls.currentTime(), 'WARNING', text)
            cls.appendMessage(message)

        cls.log.warning('\t{}'.format(text))


    @classmethod
    def error(cls, text):
        """
        Posts an error message adding a timestamp and logging level
        :param text:
        :return:
        """
        if ( cls.level == logging.DEBUG
                or cls.level == logging.INFO
                or cls.level == logging.WARNING
                or cls.level == logging.ERROR ):
            message = '{} [{}]\t{}\n'.format(cls.currentTime(), 'ERROR', text)
            cls.appendMessage(message)

        cls.log.error('\t{}'.format(text))


    @classmethod
    def critical(cls, text):
        """
        Posts a critical message adding a timestamp and logging level
        :param text:
        :return:
        """
        if ( cls.level == logging.DEBUG
                or cls.level == logging.INFO
                or cls.level == logging.WARNING
                or cls.level == logging.ERROR
                or cls.level == logging.CRITICAL ):
            message = '{} [{}]\t{}\n'.format(cls.currentTime(), 'CRITICAL', text)
            cls.appendMessage(message)

        cls.log.critical('\t{}'.format(text))


    # --------------------------------------------------------------------
    # Iterator implementation
    def __init__(self, list, task_progress_object=None):
        self.list = list
        self.list_length = len(list)
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
        FancyLogger.setTaskObject(task_id=self.task_id,
                                  task_progress_object=task_progress_object)


    def __iter__(self):
        return self


    def __next__(self):
        if self.index >= self.list_length:
            raise StopIteration
        else:
            self.index += 1
            FancyLogger.update(task_id=self.task_id,
                               progress=self.index)

            return self.list[self.index - 1]
    #---------------------------------------------------------------------
