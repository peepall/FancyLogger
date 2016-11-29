#!/bin/env/python
# coding: utf-8


class ProcessCommand(object):
    """
    Defines a command to be dispatched from a working process to the logger process.
    """

    def __init__(self):
        super(ProcessCommand, self).__init__()
        pass


class FlushCommand(ProcessCommand):
    """
    Calls to flush the remaining messages and progress bars state by forcing redraw. Can be useful if you want to be
    sure that a message or progress has been updated in display at a given moment in code, like when you are exiting an
    application or doing some kind of synchronized operations.
    """

    def __init__(self):
        super(FlushCommand, self).__init__()
        pass


class ExitCommand(ProcessCommand):
    """
    Calls to exit immediately. If you do not send a FlushCommand before, you may lose some messages of progresses that
    have not been displayed yet.
    """

    def __init__(self):
        super(ExitCommand, self).__init__()
        pass


class SetLevelCommand(ProcessCommand):
    """
    Calls to define the logging level (from standard logging module) for log messages.
    """

    def __init__(self,
                 level,
                 console_only=False):
        """
        Defines the logging level (from standard logging module) for log messages.
        :param level:           Level of logging for the file logger.
        :param console_only:    [Optional] If True then the file logger will not be affected.
        """
        super(SetLevelCommand, self).__init__()

        self.level = level
        self.console_only = console_only


class NewTaskCommand(ProcessCommand):
    """
    Calls to define a new progress bar.
    """

    def __init__(self,
                 task_id,
                 task):
        """
        Defines a new progress bar with the given information using a TaskProgress object.
        :param task_id: Unique identifier for this progress bar. Will erase if already existing.
        :param task:    TaskProgress object holding the progress bar information.
        """
        super(NewTaskCommand, self).__init__()

        self.task_id = task_id
        self.task = task


class UpdateProgressCommand(ProcessCommand):
    """
    Posts a progress update for a progress bar.
    """

    def __init__(self,
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
        super(UpdateProgressCommand, self).__init__()

        self.task_id = task_id
        self.progress = progress


class LogMessageCommand(ProcessCommand):
    """
    Posts a message using a timestamp and logging level.
    """

    def __init__(self,
                 text,
                 level):
        """
        Posts a message adding a timestamp and logging level to it for both file and console handlers.
        Logger uses a redraw rate because of console flickering. That means it will not draw new messages or progress
        at the very time they are being logged but their timestamp will be captured at the right time. Logger will
        redraw at a given time period AND when new messages or progress are logged. If you still want to force redraw
        immediately (may produce flickering) then call 'flush' method.
        :param text:    The text to log into file and console.
        :param level:   Level of logging for this message.
        """
        super(LogMessageCommand, self).__init__()

        self.text = text
        self.level = level


class SetConfigurationCommand(ProcessCommand):
    """
    Calls to define the current configuration of the logger.
    """

    def __init__(self,
                 message_number,
                 exception_number,
                 permanent_progressbar_slots,
                 redraw_frequency_millis,
                 level,
                 task_millis_to_removal):
        """
        Defines the current configuration of the logger.
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
        super(SetConfigurationCommand, self).__init__()

        self.message_number = message_number
        self.exception_number = exception_number
        self.permanent_progressbar_slots = permanent_progressbar_slots
        self.redraw_frequency_millis = redraw_frequency_millis
        self.level = level
        self.task_millis_to_removal = task_millis_to_removal


class StacktraceCommand(ProcessCommand):
    """
    Posts an exception's stacktrace to the logger.
    """

    def __init__(self,
                 pid,
                 stacktrace,
                 process_title):
        """
        Sends an exception's stacktrace to the logger.
        :param pid:             The current process's pid.
        :param stacktrace:      Stacktrace string as returned by 'traceback.format_exc()' in an 'except' block.
        :param process_title:   Define the current process title to display into the logger for this exception..
        """
        super(StacktraceCommand, self).__init__()

        self.pid = pid
        self.stacktrace = stacktrace
        self.process_title = process_title
