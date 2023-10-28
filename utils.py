"""Utilities and presets for Teledate bot."""
import datetime
import io
from dataclasses import dataclass
from math import floor

import matplotlib.pyplot as plt
from telegram import KeyboardButton, ReplyKeyboardMarkup


@dataclass
class ReplyMarkups:
    """Reply markups custom presets."""

    start = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton('Manage database')]],
        resize_keyboard=True,
        is_persistent=True,
    )
    db_delete = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton('Delete database'), KeyboardButton('Cancel')],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    db_create = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton('Create database'), KeyboardButton('Cancel')],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    db_activity = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton('Default'), KeyboardButton('Cancel')],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    main = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton('Status'), KeyboardButton('Add record')],
            [KeyboardButton('Graph'), KeyboardButton('Reminder: Off')],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    main_reminder = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton('Status'), KeyboardButton('Add record')],
            [KeyboardButton('Graph'), KeyboardButton('Reminder: On')],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
    set = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton('Set'), KeyboardButton('Cancel')]],
        resize_keyboard=True,
        is_persistent=True,
    )
    unset = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton('Unset'), KeyboardButton('Cancel')]],
        resize_keyboard=True,
        is_persistent=True,
    )
    end = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton('Start')]],
        resize_keyboard=True,
        is_persistent=True,
    )


def get_time_since(record_dt: datetime.datetime) -> str:
    """Get the time passed since the date in human-readable format."""
    diff_dt = datetime.datetime.today() - record_dt
    hours_diff = floor(diff_dt.total_seconds() / 60 / 60) - diff_dt.days * 24
    min_diff = floor(diff_dt.total_seconds() / 60) - hours_diff * 60
    sec_diff = round(diff_dt.total_seconds()) - min_diff * 60
    days_case = 'day' if diff_dt.days == 1 else 'days'
    hours_case = 'hour' if hours_diff == 1 else 'hours'
    if diff_dt.days:
        return f'{diff_dt.days} {days_case} {hours_diff} {hours_case}'
    if hours_diff:
        return f'{hours_diff} {hours_case} {min_diff} min'
    if min_diff:
        return f'{min_diff} min {sec_diff} sec'
    return f'{sec_diff} sec'


async def get_graph(
    records_dt: list[datetime.datetime], title: str = 'Default',
) -> bytes | None:
    """Get a graph of the user's records."""
    x = []
    y = []
    for record in records_dt:
        conv_record = record + datetime.timedelta(hours=3)
        x.append(conv_record.strftime('%d.%m'))
        if not y:
            prev_date = conv_record - datetime.timedelta(hours=48)
        y.append(floor((conv_record - prev_date).total_seconds() / 60 / 60))
        prev_date = conv_record
    fig, ax = plt.subplots()
    ax.plot(
        x,
        y,
        marker='o',
    )
    ax.set_title(title)
    ax.set_ylabel('Hours')
    ax.set_xlabel('Date')
    with io.BytesIO() as buf:
        fig.savefig(buf)
        return buf.getvalue()
