from aiogram import types
from bot import admin


menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
menu.add(
    types.KeyboardButton('👤Профиль'),
    types.KeyboardButton('👥Привлечь рабов'),
    types.KeyboardButton('🔝Топ'),
    types.KeyboardButton('💰Купить рабов')
)


def ranout(cost, rab):
    redeem = types.InlineKeyboardMarkup()
    if rab == 1:
        redeem.add(
            types.InlineKeyboardButton(
                text='🙇Мои рабы',
                callback_data='slaves'),
            types.InlineKeyboardButton(
                text='💰Собрать доход',
                callback_data='claim'))
        redeem.add(
            types.InlineKeyboardButton(
                text=f'Выкупиться за {cost}💰',
                callback_data=f'redeem_{cost}'))
    else:
        redeem.add(
            types.InlineKeyboardButton(
                text='🙇Мои рабы',
                callback_data='slaves'))
        redeem.add(
            types.InlineKeyboardButton(
                text='💰Собрать доход',
                callback_data='claim'))
    return redeem


def pagination(page, id, users, cost):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton('Купить за {}💰'.format(
        cost), callback_data='buy_{}-{}'.format(id, cost)))
    if len(users) != page + 1 and page != 0:
        kb.add(
            types.InlineKeyboardButton(
                'Назад',
                callback_data='back_{}'.format(
                    page - 1)),
            types.InlineKeyboardButton(
                'Дальше',
                callback_data='next_{}'.format(
                    page + 1)))
    elif len(users) != page + 1 and page == 0:
        kb.add(
            types.InlineKeyboardButton(
                'Дальше',
                callback_data='next_{}'.format(
                    page + 1)))
    elif len(users) == page + 1 and page != 0:
        kb.add(
            types.InlineKeyboardButton(
                'Назад',
                callback_data='back_{}'.format(
                    page - 1)))
    return kb


def slave_menu(page, users, id, cost):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton('Улучшить за {}💰'.format(
        cost), callback_data='upgrade_{}-{}'.format(id, cost)))
    kb.add(
        types.InlineKeyboardButton(
            'Отпустить',
            callback_data='go_{}'.format(id)))
    if len(users) != page + 1 and page != 0:
        kb.add(
            types.InlineKeyboardButton(
                'Назад',
                callback_data='uback_{}'.format(
                    page - 1)),
            types.InlineKeyboardButton(
                'Дальше',
                callback_data='unext_{}'.format(
                    page + 1)))
    elif len(users) != page + 1 and page == 0:
        kb.add(
            types.InlineKeyboardButton(
                'Дальше',
                callback_data='unext_{}'.format(
                    page + 1)))
    elif len(users) == page + 1 and page != 0:
        kb.add(
            types.InlineKeyboardButton(
                'Назад',
                callback_data='uback_{}'.format(
                    page - 1)))
    return kb


apanel = types.InlineKeyboardMarkup(row_width=2)
apanel.add(
    types.InlineKeyboardButton(text='Рассылка', callback_data='admin_rass'),
    types.InlineKeyboardButton(text='Статистика', callback_data='admin_stats'),
    types.InlineKeyboardButton(text='Изменить баланс', callback_data='admin_bal')
)


cancel = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancel.add(types.KeyboardButton('Отмена'))


senderkb = types.InlineKeyboardMarkup(row_width=1)
senderkb.add(
    types.InlineKeyboardButton(
        text='🆘По всем вопросам',
        url=f'tg://user?id={admin}'),
)


def send_link(link):
    url = 'https://t.me/share/url?url={}'.format(link)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton('🔗Поделиться ссылкой', url))
    return kb


topbuttons = types.InlineKeyboardMarkup()
topbuttons.add(
    types.InlineKeyboardButton('⛓По рабам', callback_data='byslaves'),
    types.InlineKeyboardButton('🤑По балансу', callback_data='bybalance')
)
