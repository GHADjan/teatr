from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

back_message = '🔙 Вернуться в меню'
confirm_message = '✅ Подтвердить заказ'
all_right_message = '✅ Все верно'
cancel_message = '🚫 Отменить'
phone_number = '👤 Поделиться контактом'


def confirm_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(confirm_message)
    markup.add(back_message)

    return markup

def back_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(back_message)

    return markup

def check_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.row(back_message, all_right_message)

    return markup

def submit_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.row(cancel_message, all_right_message)

    return markup

def phone_number_kb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    phone_kb = KeyboardButton('👤 Поделиться контактом', request_contact=True)

    markup.add(phone_kb)

    return markup


