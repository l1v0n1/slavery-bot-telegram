from aiogram import types
import os
from configparser import ConfigParser
import logging

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Path to config file
config_path = os.path.join(script_dir, 'config.ini')

config = ConfigParser()
config.read(config_path)

admin = config.get('main', 'admin')

# Main menu with inline keyboard instead of reply keyboard
menu_inline = types.InlineKeyboardMarkup(row_width=2)
menu_inline.add(
    types.InlineKeyboardButton('👤 Профиль', callback_data='profile'),
    types.InlineKeyboardButton('👥 Привлечь рабов', callback_data='invite_slaves'),
    types.InlineKeyboardButton('🏆 Топ игроков', callback_data='top'),
    types.InlineKeyboardButton('💰 Купить рабов', callback_data='buy_slaves')
)

# Keep old reply keyboard for backward compatibility
menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
menu.add(
    types.KeyboardButton('👤Профиль'),
    types.KeyboardButton('👥Привлечь рабов'),
    types.KeyboardButton('🔝Топ'),
    types.KeyboardButton('💰Купить рабов')
)

def ranout(cost, rab):
    redeem = types.InlineKeyboardMarkup(row_width=2)
    if rab == 1:
        redeem.add(
            types.InlineKeyboardButton(
                text='🧑‍🔧 Мои рабы',
                callback_data='slaves'),
            types.InlineKeyboardButton(
                text='💵 Собрать доход',
                callback_data='claim'))
        redeem.add(
            types.InlineKeyboardButton(
                text=f'🔓 Выкупиться за {cost} 💰',
                callback_data=f'redeem_{cost}'))
        redeem.add(
            types.InlineKeyboardButton(
                text='🏠 Главное меню',
                callback_data='back_to_menu')
        )
    else:
        redeem.add(
            types.InlineKeyboardButton(
                text='🧑‍🔧 Мои рабы',
                callback_data='slaves'),
            types.InlineKeyboardButton(
                text='💵 Собрать доход',
                callback_data='claim'))
        redeem.add(
            types.InlineKeyboardButton(
                text='🏠 Главное меню',
                callback_data='back_to_menu')
        )
    return redeem

def pagination(page, id, users, cost):
    kb = types.InlineKeyboardMarkup()
    try:
        # Use a different separator for ID and cost (use ":" instead of "-")
        callback_data = f'buy_{id}:{cost}'
        kb.add(types.InlineKeyboardButton(f'💸 Купить за {cost}💰', callback_data=callback_data))
        
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton('⬅️ Назад', callback_data=f'back_{page - 1}'))
        
        if len(users) > page + 1:
            nav_buttons.append(types.InlineKeyboardButton('➡️ Вперед', callback_data=f'next_{page + 1}'))
        
        if nav_buttons:
            kb.add(*nav_buttons)
        
        kb.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='back_to_menu'))
    except Exception as e:
        logging.error(f"Error creating pagination keyboard: {e}")
        # Add fallback button
        kb.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='back_to_menu'))
        
    return kb

def slave_menu(page, users, id, cost):
    kb = types.InlineKeyboardMarkup()
    try:
        # Use colon as separator for ID and cost
        kb.add(types.InlineKeyboardButton(
            f'⬆️ Улучшить за {cost}💰', 
            callback_data=f'upgrade_{id}:{cost}'))
        kb.add(
            types.InlineKeyboardButton(
                '🔓 Отпустить',
                callback_data=f'go_{id}'))
        
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton('⬅️ Назад', callback_data=f'uback_{page - 1}'))
        
        if len(users) > page + 1:
            nav_buttons.append(types.InlineKeyboardButton('➡️ Вперед', callback_data=f'unext_{page + 1}'))
        
        if nav_buttons:
            kb.add(*nav_buttons)
        
        kb.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='back_to_menu'))
    except Exception as e:
        logging.error(f"Error creating slave menu: {e}")
        # Fallback button
        kb.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='back_to_menu'))
        
    return kb

# Admin panel with improved button layout
apanel = types.InlineKeyboardMarkup(row_width=1)
apanel.add(
    types.InlineKeyboardButton(text='📣 Рассылка', callback_data='admin_rass'),
    types.InlineKeyboardButton(text='📊 Статистика', callback_data='admin_stats'),
    types.InlineKeyboardButton(text='💰 Изменить баланс', callback_data='admin_bal'),
    types.InlineKeyboardButton(text='🤖 Управление ботами', callback_data='admin_bots')
)

cancel = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancel.add(types.KeyboardButton('Отмена'))

# Cancel as inline keyboard
cancel_inline = types.InlineKeyboardMarkup()
cancel_inline.add(types.InlineKeyboardButton(text='❌ Отмена', callback_data='cancel_action'))

senderkb = types.InlineKeyboardMarkup(row_width=1)
senderkb.add(
    types.InlineKeyboardButton(
        text='🆘 По всем вопросам',
        url=f'tg://user?id={admin}'),
)

def send_link(link):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton('🔗 Поделиться ссылкой', url=f'https://t.me/share/url?url={link}'),
        types.InlineKeyboardButton('📊 Статистика рабов', callback_data='slave_stats'),
        types.InlineKeyboardButton('🏠 Главное меню', callback_data='back_to_menu')
    )
    return kb

topbuttons = types.InlineKeyboardMarkup(row_width=2)
topbuttons.add(
    types.InlineKeyboardButton('👥 По рабам', callback_data='byslaves'),
    types.InlineKeyboardButton('💰 По балансу', callback_data='bybalance')
)
topbuttons.add(types.InlineKeyboardButton('🏠 Главное меню', callback_data='back_to_menu'))

# Robot slaves management
bot_management = types.InlineKeyboardMarkup(row_width=2)
bot_management.add(
    types.InlineKeyboardButton('➕ Добавить бота', callback_data='add_bot'),
    types.InlineKeyboardButton('➖ Удалить бота', callback_data='remove_bot'),
    types.InlineKeyboardButton('⚙️ Настройки ботов', callback_data='bot_settings'),
    types.InlineKeyboardButton('📊 Статистика ботов', callback_data='bot_stats'),
    types.InlineKeyboardButton('🏠 Главное меню', callback_data='back_to_menu')
)
