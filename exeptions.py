# coding: utf-8
"""Кастомные исключения для программы Homework Bot."""


class EmptyListError(Exception):
    """Ошибка пустого списка."""


class EnviriableError(Exception):
    """Отсутствует константа окружения."""


class PracticumStatusError(Exception):
    """Ошибка статуса Практикума."""


class UnexpectedStatusError(Exception):
    """Неожиданный статус домашней работы."""
