#!/bin/env/python
# coding: utf-8


class FlushCommand(object):

    def __init__(self):
        super(FlushCommand, self).__init__()
        pass


class ExitCommand(object):

    def __init__(self):
        super(ExitCommand, self).__init__()
        pass


class SetLevelCommand(object):

    def __init__(self, level, console_only=False):
        super(SetLevelCommand, self).__init__()

        self.level = level
        self.console_only = console_only


class NewTaskCommand(object):

    def __init__(self, task_id, task):
        super(NewTaskCommand, self).__init__()

        self.task_id = task_id
        self.task = task


class UpdateProgressCommand(object):

    def __init__(self, task_id, progress):
        super(UpdateProgressCommand, self).__init__()

        self.task_id = task_id
        self.progress = progress


class LogMessageCommand(object):

    def __init__(self, text, level):
        super(LogMessageCommand, self).__init__()

        self.text = text
        self.level = level


class SetConfigurationCommand(object):

    def __init__(self,
                 message_number,
                 permanent_progressbar_slots,
                 redraw_frequency_millis,
                 level,
                 task_millis_to_removal):
        super(SetConfigurationCommand, self).__init__()

        self.message_number = message_number
        self.permanent_progressbar_slots = permanent_progressbar_slots
        self.redraw_frequency_millis = redraw_frequency_millis
        self.level = level
        self.task_millis_to_removal = task_millis_to_removal
