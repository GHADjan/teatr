import logging
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, \
    InlineKeyboardButton, ContentTypes
from keyboards.inline.products_from_cart import product_markup, product_cb
from aiogram.utils.callback_data import CallbackData
from keyboards.default.markups import *
from aiogram.types.chat import ChatActions
from states import CheckoutState
from loader import dp, db, bot
from filters import IsUser
from .menu import cart
from .menu import user_menu_kb


@dp.message_handler(IsUser(), text=cart)
async def process_cart(message: Message, state: FSMContext):
    cart_data = db.fetchall('SELECT * FROM cart WHERE cid=?', (message.chat.id,))

    if len(cart_data) == 0:
        await message.answer('Ваша корзина пуста.')
    else:
        await bot.send_chat_action(message.chat.id, ChatActions.TYPING)
        async with state.proxy() as data:
            data['products'] = {}

        order_cost = 0

        for _, idx, count_in_cart in cart_data:
            product = db.fetchone('SELECT * FROM products WHERE idx=?', (idx,))

            if product is None:
                db.query('DELETE FROM cart WHERE idx=?', (idx,))
            else:
                _, title, body, image, price, _ = product
                order_cost += price

                async with state.proxy() as data:
                    data['products'][idx] = [title, price, count_in_cart]

                markup = product_markup(idx, count_in_cart)
                text = f'{title}\n\n{body}\n\nЦена: {price} сумм.'

                await message.answer_photo(photo=image, caption=text, reply_markup=markup)

        if order_cost != 0:
            markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
            markup.add('📦 Оформить заказ')
            markup.add('🔙 Вернуться в меню')

            await message.answer('Чтобы удалить товар с корзины уменьшите кол-во на: 0'
                                 '\nПерейти к оформлению?', reply_markup=markup)


@dp.callback_query_handler(IsUser(), product_cb.filter(action='count'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='increase'))
@dp.callback_query_handler(IsUser(), product_cb.filter(action='decrease'))
async def product_callback_handler(query: CallbackQuery, callback_data: dict, state: FSMContext):
    idx = callback_data['id']
    action = callback_data['action']

    if action == 'count':
        async with state.proxy() as data:
            if 'products' not in data.keys():
                await process_cart(query.message, state)
            else:
                await query.answer('Количество - ' + data['products'][idx][2])
    else:
        async with state.proxy() as data:
            if 'products' not in data.keys():
                await process_cart(query.message, state)
            else:
                data['products'][idx][2] += 1 if action == 'increase' else -1
                count_in_cart = data['products'][idx][2]

                if count_in_cart == 0:
                    db.query('DELETE FROM cart WHERE cid = ? AND idx = ?', (query.message.chat.id, idx))
                    await query.message.delete()
                else:
                    db.query('UPDATE cart SET quantity = ? WHERE cid = ? AND idx = ?', (count_in_cart, query.message.chat.id, idx))
                    await query.message.edit_reply_markup(product_markup(idx, count_in_cart))

@dp.message_handler(IsUser(), text='📦 Оформить заказ')
async def process_checkout(message: Message, state: FSMContext):
    await CheckoutState.check_cart.set()
    await checkout(message, state)


async def checkout(message, state):
    answer = ''
    total_price = 0

    async with state.proxy() as data:
        for title, price, count_in_cart in data['products'].values():
            tp = count_in_cart * price
            answer += f'{title} * {count_in_cart}шт. = {tp}сумм\n'
            total_price += tp

    await message.answer(f'{answer}\nОбщая сумма заказа: {total_price}сумм.', reply_markup=check_markup())


@dp.message_handler(IsUser(), lambda message: message.text not in [all_right_message, back_message], state=CheckoutState.check_cart)
async def process_check_cart_invalid(message: Message):
    await message.reply('Такого варианта не было.')


@dp.message_handler(IsUser(), text='✅ Все верно', state=CheckoutState.check_cart)
async def process_check_cart_all_right(message: Message, state: FSMContext):
    await CheckoutState.name.set()
    await message.answer('Укажите свое имя.', reply_markup=back_markup())


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.name)
async def process_name_back(message: Message, state: FSMContext):
    await state.finish()
    await message.answer('Вы вернулись в меню.', reply_markup=user_menu_kb())


@dp.message_handler(IsUser(), text='🔙 Вернуться в меню', state='*')
async def process_back_to_menu(message: Message, state: FSMContext):
    await state.finish()
    await message.answer('Вы вернулись в меню.', reply_markup=user_menu_kb())


@dp.message_handler(IsUser(), state=CheckoutState.name)
async def process_name(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text

    await CheckoutState.phone_number.set()
    await message.answer('Отправьте свой номер телефона, чтобы мы могли связаться с вами:', reply_markup=phone_number_kb())


@dp.message_handler(IsUser(), state=CheckoutState.phone_number, content_types=ContentTypes.CONTACT)
async def process_phone_number(message: Message, state: FSMContext):
    async with state.proxy() as data:
        phone_number = message.contact.phone_number
        data['phone_number'] = phone_number

    await CheckoutState.address.set()
    await message.answer('Отправьте номер своей машины, чтобы мы могли вас найти:', reply_markup=back_markup())


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.phone_number)
async def process_phone_number_back(message: Message, state: FSMContext):
    await CheckoutState.name.set()
    async with state.proxy() as data:
        await message.answer('Изменить имя с ' + data['name'] + '?', reply_markup=back_markup())


@dp.message_handler(IsUser(), state=CheckoutState.address)
async def process_address(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['address'] = message.text

    await confirm(message)
    await CheckoutState.confirm.set()


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.address)
async def process_address_back(message: Message, state: FSMContext):
    await CheckoutState.phone_number.set()
    async with state.proxy() as data:
        await message.answer('Изменить номер телефона с ' + data['phone_number'] + '?', reply_markup=back_markup())


async def confirm(message):
    await message.answer('Убедитесь, что все правильно оформлено и подтвердите заказ.', reply_markup=confirm_markup())


@dp.message_handler(IsUser(), lambda message: message.text not in [confirm_message, back_message], state=CheckoutState.confirm)
async def process_confirm_invalid(message: Message):
    await message.reply('Такого варианта не было.')


@dp.message_handler(IsUser(), text=back_message, state=CheckoutState.confirm)
async def process_confirm_back(message: Message, state: FSMContext):
    await CheckoutState.address.set()
    async with state.proxy() as data:
        await message.answer('Изменить номер машины с: ' + data['address'] + '?', reply_markup=back_markup())


@dp.message_handler(IsUser(), text=confirm_message, state=CheckoutState.confirm)
async def process_confirm(message: Message, state: FSMContext):
    enough_money = True  # достаточно денег на счете
    markup = user_menu_kb()
    answer = ''
    total_price = 0
    if enough_money:
        logging.info('Deal was made.')
        async with state.proxy() as data:
            for title, price, count_in_cart in data['products'].values():
                tp = count_in_cart * price
                answer += f'{title} * {count_in_cart}шт. = {tp}сумм\n'
                total_price += tp
            cid = message.chat.id
            products = db.fetchall('SELECT * FROM cart WHERE cid=?', (cid,))
            product_info = [f'{title} ({count_in_cart}шт.) - {price}сум' for title, price, count_in_cart in products]
            db.query('INSERT INTO orders VALUES (?, ?, ?, ?)', (cid, data['name'], data['address'], ', '.join(product_info)))
            db.query('DELETE FROM cart WHERE cid=?', (cid,))
            await message.answer(f'Ок! Ваш заказ уже в пути 🚀\nИмя: {data["name"]}'
                                 f'\nНомер машины: {data["address"]}'
                                 f'\n Номер телефона: {data["phone_number"]}'
                                 f'\n{answer}\nОбщая сумма заказа: {total_price}сумм.', reply_markup=markup)

            await bot.send_message(6311984798, f'Имя: {data["name"]}'
                                               f'\nНомер машины: {data["address"]}'
                                               f'\nНомер телефона:{data["phone_number"]}'
                                               f'\n{answer}\nОбщая сумма заказа: {total_price}сумм.')
            await bot.send_message(1088568707, f'Имя: {data["name"]}'
                                               f'\nНомер машины: {data["address"]}'
                                               f'\nНомер телефона:{data["phone_number"]}'
                                               f'\n{answer}\nОбщая сумма заказа: {total_price}сумм.')
    else:
        await message.answer('У вас недостаточно денег на счете. Пополните баланс!', reply_markup=markup)

    await state.finish()

    # answer = ''
    # total_price = 0
    #
    # async with state.proxy() as data:
    #     for title, price, count_in_cart in data['products'].values():
    #         tp = count_in_cart * price
    #         answer += f'{title} * {count_in_cart}шт. = {tp}сумм\n'
    #         total_price += tp
    #
    # await message.answer(f'{answer}\nОбщая сумма заказа: {total_price}сумм.'