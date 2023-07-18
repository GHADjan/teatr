
import os
import handlers
from aiogram import executor, types
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from data import config
from loader import dp, db, bot
from handlers .user import menu
import filters
import logging

filters.setup(dp)

user_message = 'Пользователь'
admin_message = 'Админ'


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):

    markup = ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row(user_message, admin_message)

    await message.answer('''Привет! 👋 Что умеет этот бот? 
Этот бот создан ради комфорта посетителей
Закажите себе что-либо из нашего меню и вам его доставят прямо в машину

    ''', reply_markup=markup)


@dp.message_handler(text=user_message)
async def user_mode(message: types.Message):
    cid = message.chat.id
    if cid in config.ADMINS:
        config.ADMINS.remove(cid)
    await message.answer('Включен пользовательский режим. \nОтправьте /menu', reply_markup=menu.user_menu_kb())


@dp.message_handler(text=admin_message)
async def admin_mode(message: types.Message):
    user_id = message.from_user.id

    if user_id in [1088568707, 6311984798]:
        cid = user_id
        if cid not in config.ADMINS:
            config.ADMINS.append(cid)
        else:
            config.ADMINS.remove(cid)
        await message.answer('Включен админский режим.', reply_markup=menu.admin_menu_kb())
    else:
        await message.answer('Куда без разрешения?')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)
