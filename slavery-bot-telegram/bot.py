import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import Message, CallbackQuery
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from configparser import ConfigParser
from aiogram.utils.deep_linking import get_start_link, decode_payload
from aiogram.utils.markdown import hlink
import time
import hashlib
import aioschedule
import asyncio

import database as db
import keyboard as kb
import functions as fc
import robot_slaves as rs

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Path to config file
config_path = os.path.join(script_dir, 'config.ini')

config = ConfigParser()
config.read(config_path)

token = config.get('main', 'token')
admin = config.get('main', 'admin')


logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=token)
dp = Dispatcher(bot, storage=storage)

# Initialize the robot slave manager
robot_manager = rs.RobotSlaveManager(bot)

timeout = {}


class adm(StatesGroup):
	text = State()
	balance = State()


@dp.message_handler(commands='start', chat_type=['private'])
async def start(message: Message):
	await db.insert(message.chat.id)
	slaves = await db.get_slaves(message.chat.id)
	await db.change_field(message.chat.id, 'count', slaves)
	args = message.get_args()
	if args == 'no':
		await message.answer('👋 Добро пожаловать в игру "Рабство"! Используйте меню для навигации:', reply_markup=kb.menu_inline)
	else:
		if args != '':
			payload = decode_payload(args)
			if str(message.chat.id) == str(payload):
				await message.answer('⚠️ Нельзя наткнуться на свою же ловушку!', reply_markup=kb.menu_inline)
			else:
				user = await db.get_document(message.chat.id)
				if user['owner'] == 0:
					await db.change_field(message.chat.id, 'owner', int(payload))
					await message.answer('🪤 Вы попались на <b>ловушку</b>!\nТеперь вы являетесь рабом пользователя <b>{}</b>, вы можете освободиться за определенную сумму.'.format(payload), parse_mode='HTML', reply_markup=kb.menu_inline)
				else:
					await message.answer('🙅 Вы попались на <b>ловушку</b>, но вы не станете рабом пользователя <b>{}</b>, так как вы уже являетесь чьей-то собственностью!'.format(payload), parse_mode='HTML', reply_markup=kb.menu_inline)
		else:
			await message.answer('👋 Добро пожаловать в игру "Рабство"! Используйте меню для навигации:', reply_markup=kb.menu_inline)


@dp.message_handler(text='👥Привлечь рабов', chat_type=['private'])
async def slaves_trap(message: Message):
	await db.insert(message.chat.id)
	slaves = await db.get_slaves(message.chat.id)
	await db.change_field(message.chat.id, 'count', slaves)
	link = await get_start_link(message.chat.id, encode=True)
	keyboard = kb.send_link(link)
	await message.answer(
		'✨ Вот твоя ссылка для <b>привлечения рабов</b>:\n{}\n\n'
		'<b>Делись ссылкой с друзьями и знакомыми, каждый новый игрок, перешедший по твоей ссылке, становится твоим рабом.\n'
		'Каждый раб приносит тебе определенный доход, рабов можно усовершенствовать.</b>'.format(link), parse_mode='HTML', reply_markup=keyboard)


async def profile_handler(message: Message):
	await db.insert(message.chat.id)
	earn = await db.earning(message.chat.id)
	user = await db.get_document(message.chat.id)
	slaves = await db.get_slaves(message.chat.id)
	await db.change_field(message.chat.id, 'count', slaves)
	if user['owner'] != 0:
		try:
			chat = await bot.get_chat(user['owner'])
			name = chat.first_name
			url = hlink(name, f"tg://user?id={user['owner']}")
			owner = 'Вы явялетесь <b>рабом</b>!\nВаш <b>владелец</b> {}'.format(url)
		except Exception as e:
			logging.error(f"Error getting owner chat: {e}")
			owner = 'Вы явялетесь <b>рабом</b>!\nВаш <b>владелец</b> имеет ID: {}'.format(user['owner'])
			
		if user['ransom'] != 0:
			cost = user['ransom'] * 500
		else:
			cost = 500
		keyboard = kb.ranout(cost, 1)
	else:
		owner = ''
		keyboard = kb.ranout(123, 0)
	await message.answer('Ваш <b>профиль</b>:\n\n👤 ID: <b>{}</b>\n💰 Баланс: <b>{}</b>💰\n👥 Рабов: <b>{}</b>\n💵 Доход: <b>{}</b>💰\n\n{}'.format(message.chat.id, user['balance'], slaves, earn, owner), parse_mode='HTML', reply_markup=keyboard)


@dp.message_handler(text='👤Профиль', chat_type=['private'])
async def user_doc(message: Message):
	await profile_handler(message)


@dp.message_handler(text='💰Купить рабов', chat_type=['private'])
async def buy_slaves(message: Message, state: FSMContext):
	await db.insert(message.chat.id)
	myslaves = await db.get_slaves(message.chat.id)
	await db.change_field(message.chat.id, 'count', myslaves)
	slaves = await db.get_all_slaves(message.chat.id)
	if not slaves:
		await message.answer('⚠️ Не найдено пользователей для приобретения', reply_markup=kb.menu_inline)
		return
		
	try:
		slave_id = slaves[0]
		user = await db.get_document(slave_id)
		if not user:
			await message.answer('⚠️ Ошибка при получении информации о рабе', reply_markup=kb.menu_inline)
			return
			
		# Safely get the user link
		try:
			if await is_robot_user(slave_id):
				# Handle robot users
				robot_name = user.get('robot_name', f"Робот ID: {slave_id}")
				name = f"🤖 {robot_name}"
				url = f"🤖 {robot_name}"
			else:
				# Handle real users
				chat = await bot.get_chat(slave_id)
				name = chat.first_name
				url = hlink(name, f"tg://user?id={slave_id}")
		except Exception as e:
			logging.error(f"Error getting user info: {e}")
			name = f"Пользователь ID: {slave_id}"
			url = f"ID: {slave_id}"
			
		# Handle owner info
		owner_text = ""
		if user['owner'] != 0:
			try:
				if await is_robot_user(user['owner']):
					owner_doc = await db.get_document(user['owner'])
					if owner_doc and 'robot_name' in owner_doc:
						owner_name = f"🤖 {owner_doc['robot_name']}"
					else:
						owner_name = f"🤖 Робот ID: {user['owner']}"
					owner_url = owner_name
				else:
					owner = await bot.get_chat(user['owner'])
					owner_name = owner.first_name
					owner_url = hlink(owner_name, f"tg://user?id={user['owner']}")
				owner_text = f"⛓ В <b>рабстве</b> у {owner_url}\n"
			except Exception as e:
				logging.error(f"Error getting owner info: {e}")
				owner_text = f"⛓ В <b>рабстве</b> у ID: {user['owner']}\n"
				
		await message.answer(f'👤 Пользователь <b>{url}</b>\n{owner_text}💰 Доход: {user["earn"]}💰', 
			parse_mode='HTML', 
			reply_markup=kb.pagination(0, slave_id, slaves, user['earn'] * 50))
	except Exception as e:
		logging.error(f"Error in buy_slaves: {e}")
		await message.answer('⚠️ Ошибка при получении информации о рабах', reply_markup=kb.menu_inline)
		
	await state.update_data(slaves=slaves)


@dp.message_handler(text='🔝Топ', chat_type=['private'])
async def top_handler(message: Message):
	await db.insert(message.chat.id)
	slaves = await db.get_slaves(message.chat.id)
	await db.change_field(message.chat.id, 'count', slaves)
	sorted = await db.sort_by_slaves()
	top = []
	for index, i in enumerate(sorted, 1):
		try:
			chat = await bot.get_chat(i['chat_id'])
			name = chat.first_name
			url = hlink(name, f"tg://user?id={i['chat_id']}")
			top.append(f'{fc.emojies(index)} место: {url} - {i["count"]} раб(ов)')
		except Exception as e:
			logging.error(f"Error getting chat info for {i['chat_id']}: {e}")
			# Add a placeholder for the user we couldn't retrieve
			top.append(f'{fc.emojies(index)} место: ID {i["chat_id"]} - {i["count"]} раб(ов)')
	await message.answer('🏆 Топ по количеству рабов:\n{}'.format('\n'.join(str(v) for v in top)), reply_markup=kb.topbuttons, parse_mode='HTML')


@dp.message_handler(commands='admin', chat_type=['private'])
async def admin_panel(message: types.Message):
	if int(message.chat.id) == int(admin):
		await message.answer('🔑 Админ-панель', reply_markup=kb.apanel)


@dp.callback_query_handler(lambda call: call.data == 'admin_bots')
async def admin_robot_panel(call: types.CallbackQuery):
	if int(call.message.chat.id) == int(admin):
		stats = await robot_manager.get_robot_stats()
		active_users = await db.get_active_users_count(24)
		
		await call.message.edit_text(
			f"🤖 Управление ботами-рабами\n\n"
			f"📊 Статистика:\n"
			f"Активных ботов: {stats['total_robots']}\n"
			f"Рабов у ботов: {stats['total_robot_slaves']}\n"
			f"Общий доход ботов: {stats['total_robot_earnings']}💰\n"
			f"Активных пользователей (24ч): {active_users}\n\n"
			f"Используйте кнопки для управления ботами:",
			reply_markup=kb.bot_management
		)
		await call.answer()


@dp.callback_query_handler(lambda call: call.data == 'add_bot')
async def add_robot(call: types.CallbackQuery):
	if int(call.message.chat.id) == int(admin):
		robot = await robot_manager.create_robot()
		if robot:
			await call.answer(f"Создан новый бот: {robot.name} (ID: {robot.robot_id})", show_alert=True)
		else:
			await call.answer("Не удалось создать бота", show_alert=True)


@dp.callback_query_handler(lambda call: call.data == 'bot_stats')
async def robot_stats(call: types.CallbackQuery):
	if int(call.message.chat.id) == int(admin):
		stats = await robot_manager.get_robot_stats()
		user_stats = await db.get_user_statistics()
		
		await call.message.edit_text(
			f"📊 Статистика ботов и пользователей\n\n"
			f"👥 Пользователи:\n"
			f"Всего пользователей: {user_stats['total_users']}\n"
			f"Реальных пользователей: {user_stats['real_users']}\n"
			f"Ботов: {user_stats['robot_users']}\n"
			f"Активных за 24ч: {user_stats['active_users_24h']}\n\n"
			f"🤖 Боты:\n"
			f"Количество ботов: {stats['total_robots']}\n"
			f"Рабов у ботов: {stats['total_robot_slaves']}\n"
			f"Общий доход ботов: {stats['total_robot_earnings']}💰\n\n"
			f"💰 Экономика:\n"
			f"Всего рабов: {user_stats['total_slaves']}\n"
			f"Всего денег: {user_stats['total_balance']}💰",
			reply_markup=kb.bot_management
		)
		await call.answer()


@dp.callback_query_handler(lambda call: call.data == 'bot_settings')
async def robot_settings(call: types.CallbackQuery):
	if int(call.message.chat.id) == int(admin):
		status = "Запущена" if robot_manager.is_running else "Остановлена"
		
		settings_kb = types.InlineKeyboardMarkup(row_width=1)
		
		if robot_manager.is_running:
			settings_kb.add(types.InlineKeyboardButton("⏹ Остановить симуляцию", callback_data="stop_simulation"))
		else:
			settings_kb.add(types.InlineKeyboardButton("▶️ Запустить симуляцию", callback_data="start_simulation"))
			
		settings_kb.add(
			types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_bots"),
			types.InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_menu")
		)
		
		await call.message.edit_text(
			f"⚙️ Настройки симуляции ботов\n\n"
			f"Статус симуляции: {status}\n"
			f"Минимум ботов: {robot_manager.min_robots}\n"
			f"Максимум ботов: {robot_manager.max_robots}\n"
			f"Текущее количество: {len(robot_manager.robots)}",
			reply_markup=settings_kb
		)
		await call.answer()


@dp.callback_query_handler(lambda call: call.data == "start_simulation")
async def start_robot_simulation(call: types.CallbackQuery):
	if int(call.message.chat.id) == int(admin):
		if not robot_manager.is_running:
			# Start robot simulation in background
			asyncio.create_task(robot_manager.start_simulation())
			await call.answer("Симуляция запущена", show_alert=True)
			await robot_settings(call)
		else:
			await call.answer("Симуляция уже запущена", show_alert=True)


@dp.callback_query_handler(lambda call: call.data == "stop_simulation")
async def stop_robot_simulation(call: types.CallbackQuery):
	if int(call.message.chat.id) == int(admin):
		if robot_manager.is_running:
			robot_manager.stop_simulation()
			await call.answer("Симуляция остановлена", show_alert=True)
			await robot_settings(call)
		else:
			await call.answer("Симуляция уже остановлена", show_alert=True)


@dp.callback_query_handler(lambda call: call.data.startswith('by'))
async def topcallback(call: types.CallbackQuery):
	if call.data == 'byslaves':
		sorted = await db.sort_by_slaves()
		top = []
		for index, i in enumerate(sorted, 1):
			try:
				chat = await bot.get_chat(i['chat_id'])
				name = chat.first_name
				url = hlink(name, f"tg://user?id={i['chat_id']}")
				top.append(f'{fc.emojies(index)} место: {url} - {i["count"]} раб(ов)')
			except Exception as e:
				logging.error(f"Error getting chat info for {i['chat_id']}: {e}")
				top.append(f'{fc.emojies(index)} место: ID {i["chat_id"]} - {i["count"]} раб(ов)')
		try:
			await call.message.edit_text('🏆 Топ по количеству рабов:\n{}'.format('\n'.join(str(v) for v in top)), reply_markup=kb.topbuttons, parse_mode='HTML')
		except BaseException:
			await call.answer('Вы и так уже на этой кнопке!', show_alert=True)
	elif call.data == 'bybalance':
		sorted = await db.sort_by_balance()
		top = []
		for index, i in enumerate(sorted, 1):
			try:
				chat = await bot.get_chat(i['chat_id'])
				name = chat.first_name
				url = hlink(name, f"tg://user?id={i['chat_id']}")
				top.append(f'{fc.emojies(index)} место: {url} - {i["balance"]}💰')
			except Exception as e:
				logging.error(f"Error getting chat info for {i['chat_id']}: {e}")
				top.append(f'{fc.emojies(index)} место: ID {i["chat_id"]} - {i["balance"]}💰')
		try:
			await call.message.edit_text('💰Топ по количеству денег:\n{}'.format('\n'.join(str(v) for v in top)), reply_markup=kb.topbuttons, parse_mode='HTML')
		except BaseException:
			await call.answer('Вы и так уже на этой кнопке!', show_alert=True)


@dp.callback_query_handler(lambda call: call.data.startswith('next'))
async def next_page(call: types.CallbackQuery, state: FSMContext):
	# Check if it's an inline menu navigation
	if call.data == 'next_page':
		await call.answer('Переход на следующую страницу', show_alert=False)
		return
		
	try:
		page = int(call.data.split('_')[1])
	except (ValueError, IndexError):
		logging.error(f"Error parsing page number from callback data: {call.data}")
		await call.answer('Неверный формат данных', show_alert=True)
		return
		
	data = await state.get_data()
	slaves = data.get('slaves')
	
	if not slaves:
		await call.answer('Список рабов пуст', show_alert=True)
		return
		
	if len(slaves) <= page:
		await call.answer('Пользователей для приобретения больше нет', show_alert=True)
		return
		
	try:
		selected = slaves[page]
		user = await db.get_document(selected)
		if not user:
			await call.answer('Информация о пользователе не найдена', show_alert=True)
			return
			
		# Get user link safely
		user_link = await safe_get_chat_link(selected)
		
		# Get owner info safely
		if user['owner'] != 0:
			owner_link = await safe_get_chat_link(user['owner'])
			await call.message.edit_text(
				f'Пользователь <b>{user_link}</b>\nВ <b>рабстве</b> у {owner_link}\nДоход: {user["earn"]}💰',
				parse_mode='HTML',
				reply_markup=kb.pagination(page, selected, slaves, user['earn'] * 50)
			)
		else:
			await call.message.edit_text(
				f'Пользователь <b>{user_link}</b>\nДоход: {user["earn"]}💰',
				parse_mode='HTML',
				reply_markup=kb.pagination(page, selected, slaves, user['earn'] * 50)
			)
	except Exception as e:
		logging.error(f"Error in next_page: {e}")
		await call.answer('Ошибка при получении информации о пользователе', show_alert=True)


@dp.callback_query_handler(lambda call: call.data.startswith('back'))
async def back_page(call: types.CallbackQuery, state: FSMContext):
	# Check if it's a menu navigation
	if call.data == 'back_to_menu':
		await back_to_menu(call)
		return
		
	try:
		page = int(call.data.split('_')[1])
	except (ValueError, IndexError):
		await call.answer('Неверный формат данных', show_alert=True)
		return
		
	data = await state.get_data()
	slaves = data.get('slaves')
	
	if not slaves:
		await call.answer('Список рабов пуст', show_alert=True)
		return
		
	try:
		selected = slaves[page]
		user = await db.get_document(selected)
		if not user:
			await call.answer('Информация о пользователе не найдена', show_alert=True)
			return
			
		# Get user link safely
		user_link = await safe_get_chat_link(selected)
		
		# Get owner info safely
		if user['owner'] != 0:
			owner_link = await safe_get_chat_link(user['owner'])
			await call.message.edit_text(
				f'Пользователь <b>{user_link}</b>\nВ <b>рабстве</b> у {owner_link}\nДоход: {user["earn"]}💰',
				parse_mode='HTML',
				reply_markup=kb.pagination(page, selected, slaves, user['earn'] * 50)
			)
		else:
			await call.message.edit_text(
				f'Пользователь <b>{user_link}</b>\nДоход: {user["earn"]}💰',
				parse_mode='HTML',
				reply_markup=kb.pagination(page, selected, slaves, user['earn'] * 50)
			)
	except Exception as e:
		logging.error(f"Error in back_page: {e}")
		await call.answer('Ошибка при получении информации о пользователе', show_alert=True)


@dp.callback_query_handler(lambda call: call.data.startswith('buy'))
async def buy_slave(call: types.CallbackQuery, state: FSMContext):
	# Handle inline menu button
	if call.data == 'buy_slaves':
		await inline_buy_slaves(call, state)
		return
	
	try:
		# Extract the slave ID and cost from the callback data
		parts = call.data.split('_', 1)  # Split only at the first underscore
		if len(parts) < 2:
			await call.answer('Неверный формат данных (недостаточно частей)', show_alert=True)
			return
			
		id_cost = parts[1]
		if ':' not in id_cost:
			await call.answer('Неверный формат данных (отсутствует разделитель стоимости)', show_alert=True)
			return
			
		# Get ID and cost using : as separator
		id_part, cost_part = id_cost.split(':', 1)  # Split at the colon
		
		# Convert to integers, handling any format issues
		try:
			slave = int(id_part)
			cost = int(cost_part)
		except ValueError as e:
			logging.error(f"Error converting ID or cost to integer: {e}, data: {call.data}")
			await call.answer('Ошибка преобразования ID или стоимости', show_alert=True)
			return
			
		logging.info(f"Attempting to buy slave ID: {slave} for cost: {cost}")
		
		# Get slaves list from state
		data = await state.get_data()
		slaves = data.get('slaves')
		if not slaves:
			await call.answer('Список рабов пуст', show_alert=True)
			return
			
		# Get user data
		me = await db.get_document(call.message.chat.id)
		if not me:
			await call.answer('Ошибка получения данных пользователя', show_alert=True)
			return
			
		# Get slave data
		slavedoc = await db.get_document(slave)
		if not slavedoc:
			await call.answer('Раб не найден в базе данных', show_alert=True)
			return
			
		# Check if user already owns this slave
		if slavedoc['owner'] == call.message.chat.id:
			await call.answer('Данный раб и так уже ваш', show_alert=True)
			return
			
		# Check if trying to buy their own owner
		if me['owner'] == slavedoc['chat_id']:
			await call.answer('Нельзя купить своего владельца', show_alert=True)
			return
			
		# Check if user has enough money
		if me['balance'] < cost:
			await call.answer('Недостаточно денег на балансе', show_alert=True)
			return
			
		# Process the purchase
		await db.change_field(call.message.chat.id, 'balance', me['balance'] - cost)
		await db.change_field(slave, 'owner', call.message.chat.id)
		
		# Update slaves list
		try:
			slaves.remove(slave)
			await state.update_data(slaves=slaves)
			
			# If there are more slaves, show the next one
			if slaves:
				next_slave_id = slaves[0]
				user = await db.get_document(next_slave_id)
				if not user:
					await call.answer('Раб успешно куплен. Ошибка получения данных следующего раба', show_alert=True)
					return
					
				user_link = await safe_get_chat_link(next_slave_id)
				
				# Show owner info if slave has one
				if user['owner'] != 0:
					owner_link = await safe_get_chat_link(user['owner'])
					await call.message.edit_text(
						f'Пользователь <b>{user_link}</b>\nВ <b>рабстве</b> у {owner_link}\nДоход: {user["earn"]}💰',
						parse_mode='HTML',
						reply_markup=kb.pagination(0, next_slave_id, slaves, user['earn'] * 50)
					)
				else:
					await call.message.edit_text(
						f'Пользователь <b>{user_link}</b>\nДоход: {user["earn"]}💰',
						parse_mode='HTML',
						reply_markup=kb.pagination(0, next_slave_id, slaves, user['earn'] * 50)
					)
				
				await call.answer('Раб успешно куплен', show_alert=True)
			else:
				# No more slaves to show
				await call.message.edit_text(f'{call.message.html_text}\n\nРаб <b>приобретен</b>\nБольше рабов для покупки нет', parse_mode='HTML')
				await call.answer('Раб успешно куплен. Больше рабов для покупки нет', show_alert=True)
				
		except Exception as e:
			logging.error(f"Error updating slaves list after purchase: {e}")
			await call.answer('Раб куплен, но возникла ошибка при обновлении списка', show_alert=True)
			
	except Exception as e:
		logging.error(f"Error in buy_slave: {e}, data: {call.data}")
		await call.answer('Произошла ошибка при покупке раба', show_alert=True)


@dp.callback_query_handler(lambda call: call.data.startswith('unext'))
async def next_page_slaves(call: types.CallbackQuery, state: FSMContext):
	try:
		page = int(call.data.split('_')[1])
		data = await state.get_data()
		slaves = data.get('slaves')
		
		if not slaves:
			await call.answer('Список рабов пуст', show_alert=True)
			return
			
		if len(slaves) <= page:
			await call.answer('Рабов больше нет', show_alert=True)
			return
			
		selected = slaves[page]
		user = await db.get_document(selected)
		if not user:
			await call.answer('Информация о рабе не найдена', show_alert=True)
			return
			
		# Get user link safely
		user_link = await safe_get_chat_link(selected)
		
		await call.message.edit_text(
			f'Раб: <b>{user_link}</b>\nДоход: {user["earn"]}💰', 
			reply_markup=kb.slave_menu(page, slaves, selected, user['earn'] * 50), 
			parse_mode='HTML'
		)
		await state.update_data(page=page)
	except Exception as e:
		logging.error(f"Error in next_page_slaves: {e}")
		await call.answer('Ошибка при навигации по списку рабов', show_alert=True)


@dp.callback_query_handler(lambda call: call.data.startswith('go'))
async def lethimgo(call: types.CallbackQuery):
	try:
		slave_id = int(call.data.split('_')[1])
		
		# Update the database to free the slave
		await db.change_field(slave_id, 'owner', 0)
		
		# Get slave info for confirmation message
		slave_link = await safe_get_chat_link(slave_id)
		
		await call.message.edit_text(
			f'{call.message.html_text}\n\n<b>Раб {slave_link} отпущен на свободу!</b>', 
			parse_mode='HTML'
		)
		await call.answer('Раб успешно отпущен', show_alert=True)
	except Exception as e:
		logging.error(f"Error in lethimgo: {e}")
		await call.answer('Ошибка при освобождении раба', show_alert=True)


@dp.callback_query_handler(lambda call: call.data.startswith('uback'))
async def back_page_upgrade(call: types.CallbackQuery, state: FSMContext):
	try:
		page = int(call.data.split('_')[1])
		data = await state.get_data()
		slaves = data.get('slaves')
		
		if not slaves:
			await call.answer('Список рабов пуст', show_alert=True)
			return
			
		if page < 0 or page >= len(slaves):
			await call.answer('Неверный номер страницы', show_alert=True)
			return
			
		selected = slaves[page]
		user = await db.get_document(selected)
		if not user:
			await call.answer('Информация о рабе не найдена', show_alert=True)
			return
			
		# Get user link safely
		user_link = await safe_get_chat_link(selected)
		
		await call.message.edit_text(
			f'Раб: <b>{user_link}</b>\nДоход: {user["earn"]}💰', 
			reply_markup=kb.slave_menu(page, slaves, selected, user['earn'] * 50), 
			parse_mode='HTML'
		)
		await state.update_data(page=page)
	except Exception as e:
		logging.error(f"Error in back_page_upgrade: {e}")
		await call.answer('Ошибка при навигации по списку рабов', show_alert=True)


@dp.callback_query_handler(lambda call: call.data.startswith('upgrade'))
async def upgrade_slave(call: types.CallbackQuery, state: FSMContext):
	try:
		parts = call.data.split('_', 1)
		if len(parts) < 2:
			await call.answer('Неверный формат данных (недостаточно частей)', show_alert=True)
			return
			
		id_cost = parts[1]
		if ':' not in id_cost:
			await call.answer('Неверный формат данных (отсутствует разделитель стоимости)', show_alert=True)
			return
			
		# Get ID and cost using : as separator
		id_part, cost_part = id_cost.split(':', 1)
		
		try:
			slave = int(id_part)
			cost = int(cost_part)
		except ValueError as e:
			logging.error(f"Error converting ID or cost to integer in upgrade: {e}, data: {call.data}")
			await call.answer('Ошибка преобразования ID или стоимости', show_alert=True)
			return
		
		data = await state.get_data()
		slaves = data.get('slaves')
		
		if not slaves:
			await call.answer('Список рабов пуст', show_alert=True)
			return
			
		page = data.get('page', 0)
		
		me = await db.get_document(call.message.chat.id)
		if not me:
			await call.answer('Ошибка получения данных пользователя', show_alert=True)
			return
			
		slavedoc = await db.get_document(slave)
		if not slavedoc:
			await call.answer('Раб не найден в базе данных', show_alert=True)
			return
			
		if me['balance'] < cost:
			await call.answer('Недостаточно денег на балансе', show_alert=True)
			return
			
		await db.change_field(call.message.chat.id, 'balance', me['balance'] - cost)
		await db.change_field(slave, 'earn', slavedoc['earn'] * 5)
		
		try:
			# Use safe_get_chat_link for getting user link
			user_link = await safe_get_chat_link(slaves[page])
			user = await db.get_document(slaves[page])
			
			await call.message.edit_text(
				f'Раб: <b>{user_link}</b>\nДоход: {user["earn"]}💰',
				reply_markup=kb.slave_menu(int(page), slaves, slave, user['earn'] * 50), 
				parse_mode='HTML'
			)
		except Exception as e:
			logging.error(f"Error displaying upgraded slave: {e}")
			await call.message.edit_text(
				'Раб успешно улучшен!', 
				reply_markup=kb.slave_menu(int(page), slaves, slave, slavedoc['earn'] * 5), 
				parse_mode='HTML'
			)
			
		await call.answer(f'Раб {slave} успешно улучшен.\nТеперь его доход составляет: {slavedoc["earn"] * 5}💰', show_alert=True)
	except Exception as e:
		logging.error(f"Error upgrading slave: {e}")
		await call.answer('Ошибка при улучшении раба', show_alert=True)


@dp.callback_query_handler(text='slaves')
async def user_slaves(call: types.CallbackQuery, state: FSMContext):
	slaves = await db.get_slaves_spisok(call.message.chat.id)
	if slaves == []:
		await call.answer('У вас пока нет рабов.', show_alert=True)
	else:
		user = await db.get_document(slaves[0])
		try:
			chat = await bot.get_chat(slaves[0])
			name = chat.first_name
			url = hlink(name, f"tg://user?id={slaves[0]}")
			msg = await call.message.answer('Список ваших рабов:')
			await msg.reply('Раб: <b>{}</b>\nДоход: {}'.format(url, user['earn']), reply_markup=kb.slave_menu(0, slaves, slaves[0], user['earn'] * 50), parse_mode='HTML')
		except Exception as e:
			logging.error(f"Error getting chat info for slave {slaves[0]}: {e}")
			await call.answer('Ошибка при получении информации о рабе.', show_alert=True)
		await state.update_data(slaves=slaves)


@dp.callback_query_handler(lambda call: call.data.startswith('redeem'))
async def redeem(call: types.CallbackQuery):
	data = call.data.split('_')[1]
	user = await db.get_document(call.message.chat.id)
	slaves = await db.get_slaves(call.message.chat.id)
	if user['owner'] != 0:
		if user['balance'] < int(data):
			await call.answer('Недостаточно денег на балансе', show_alert=True)
		else:
			await db.change_field(call.message.chat.id, 'balance', user['balance'] - int(data))
			await db.change_field(call.message.chat.id, 'owner', 0)
			await db.change_field(call.message.chat.id, 'ransom', user['ransom']+1)
			earn = await db.earning(call.message.chat.id)
			await call.message.edit_text('Ваш <b>профиль</b>:\n\nID: <b>{}</b>\nБаланс: <b>{}</b>💰\nРабов: <b>{}</b>\nДоход: <b>{}</b>💰'.format(call.message.chat.id, user['balance'] - int(data), slaves, earn), parse_mode='HTML', reply_markup=kb.ranout(1334, 0))
			await call.answer('Вы освободились от рабства за {}💰'.format(data), show_alert=True)
	else:
		await call.answer('Вами никто не владеет.', show_alert=True)


@dp.callback_query_handler(text='claim')
async def claim_earn(call: types.CallbackQuery):
	if call.message.chat.id not in timeout or time.time() >= timeout[call.message.chat.id]:
		earned = await db.claim_earnings(call.message.chat.id)
		if earned == 0:
			await call.answer('Ваш доход: 0\nВы ничего не заработали.', show_alert=True)
		else:
			timeout[call.message.chat.id] = time.time() + 600
			earn = await db.earning(call.message.chat.id)
			user = await db.get_document(call.message.chat.id)
			slaves = await db.get_slaves(call.message.chat.id)
			await db.change_field(call.message.chat.id, 'count', slaves)
			if user['owner'] != 0:
				try:
					chat = await bot.get_chat(user['owner'])
					name = chat.first_name
					url = hlink(name, f"tg://user?id={user['owner']}")
					owner = 'Вы явялетесь <b>рабом</b>!\nВаш <b>владелец</b> {}'.format(url)
				except Exception as e:
					logging.error(f"Error getting owner chat: {e}")
					owner = 'Вы явялетесь <b>рабом</b>!\nВаш <b>владелец</b> имеет ID: {}'.format(user['owner'])
					
				if user['ransom'] != 0:
					cost = user['ransom'] * 500
				else:
					cost = 500
				keyboard = kb.ranout(cost, 1)
			else:
				owner = ''
				keyboard = kb.ranout(123, 0)
			await call.message.edit_text('Ваш <b>профиль</b>:\n\n👤 ID: <b>{}</b>\n💰 Баланс: <b>{}</b>💰\n👥 Рабов: <b>{}</b>\n💵 Доход: <b>{}</b>💰\n\n{}'.format(call.message.chat.id, user['balance'], slaves, earn, owner), parse_mode='HTML', reply_markup=keyboard)
			await call.answer('Вы успешно собрали доход с ваших рабов.\nЗаработано: {}💰'.format(earned), show_alert=True)
			tasks = [i.get_name() for i in asyncio.all_tasks()]
			if str(call.message.chat.id) not in tasks:
				asyncio.create_task(scheduler(call.message.chat.id), name=call.message.chat.id)
	elif call.message.chat.id in timeout and time.time() <= timeout[call.message.chat.id]:
		await call.answer('Собирать доход можно раз в 10 минут!\nСобрать доход можно будет:\n{}'.format(time.ctime(timeout[call.message.chat.id])), show_alert=True)


async def add_earn(chat_id):
	try:
		await db.claim_earnings(chat_id)
	except:
		pass


async def scheduler(chat_id):	
	aioschedule.every(10).minutes.do(add_earn, chat_id)
	while True:
		await aioschedule.run_pending()
		await asyncio.sleep(1)


@dp.callback_query_handler(lambda call: call.data.startswith('admin'))
async def admin_panel(call: types.CallbackQuery):
	if int(call.message.chat.id) == int(admin):
		if 'stats' in call.data:
			count = await db.sender()
			await call.answer('Всего юзеров: {}'.format(len(count)), show_alert=True)
		elif 'rass' in call.data:
			await call.message.answer('Введите текст для рассылки.\n\nДля отмены нажмите кнопку ниже 👇', reply_markup=kb.cancel)
			await adm.text.set()
		elif 'bal' in call.data:
			await call.message.answer('Введите id пользователя, и баланс, на который нужно изменить.\nВ виде id:balance (123123:400)', reply_markup=kb.cancel)
			await adm.balance.set()


@dp.message_handler(state=adm.balance, chat_type=['private'])
async def changebalance(message: Message, state: FSMContext):
	if message.text == 'Отмена':
		await message.answer('Отмена! Возвращаю в главное меню.', reply_markup=kb.menu)
		await state.finish()
	else:
		spl = message.text.split(':')
		id = int(spl[0])
		bal = int(spl[1])
		await state.finish()
		await db.change_field(id, 'balance', bal)
		await message.answer('Баланс пользователя {} изменен на {}'.format(id, bal), reply_markup=kb.menu)


@dp.message_handler(state=adm.text, chat_type=['private'])
async def textsending(message: Message, state: FSMContext):
	if message.text == 'Отмена':
		await message.answer('Отмена! Возвращаю в главное меню.', reply_markup=kb.menu)
		await state.finish()
	else:
		info = await db.sender()
		await message.answer('Начинаю рассылку...', reply_markup=kb.menu)
		await state.finish()
		x = 0
		for i in range(len(info)):
			try:
				await bot.send_message(info[i], str(message.text), reply_markup=kb.senderkb)
				x += 1
			except BaseException:
				pass
		await message.answer('Рассылка завершена.\nДоставлено сообщений: {}'.format(x))


@dp.inline_handler()
async def inline_echo(inline_query: types.InlineQuery):
	check = await db.check(inline_query.from_user.id)
	if check is not False:
		link = await get_start_link(inline_query.from_user.id, encode=True)
		input_content = types.InputTextMessageContent(link)
		result_id: str = hashlib.md5(link.encode()).hexdigest()
		item = types.InlineQueryResultArticle(
			id=result_id,
			title='Ваша ссылка для привлечения рабов',
			input_message_content=input_content,
		)
		await inline_query.answer(results=[item], is_personal=True, switch_pm_text="Рабство Бот", switch_pm_parameter='no')
	else:
		await inline_query.answer([], is_personal=True, switch_pm_text="Вы не зарегистрированы в Рабство Боте", switch_pm_parameter='no')


@dp.message_handler(chat_type=['private'])
async def all_handler(message: Message):
	await db.insert(message.chat.id)
	await message.answer('👋 Добро пожаловать в игру "Рабство"!', reply_markup=kb.menu_inline)


@dp.callback_query_handler(text='back_to_menu')
async def back_to_menu(call: CallbackQuery):
	await call.message.edit_text('👋 Главное меню', reply_markup=kb.menu_inline)
	await call.answer()
	
@dp.callback_query_handler(text='profile')
async def inline_profile(call: CallbackQuery):
	await profile_handler(call.message)
	await call.answer()

@dp.callback_query_handler(text='invite_slaves')
async def inline_invite_slaves(call: CallbackQuery):
	await slaves_trap(call.message)
	await call.answer()

@dp.callback_query_handler(text='top')
async def inline_top(call: CallbackQuery):
	await top_handler(call.message)
	await call.answer()

@dp.callback_query_handler(text='buy_slaves')
async def inline_buy_slaves(call: CallbackQuery, state: FSMContext):
	await buy_slaves(call.message, state)
	await call.answer()

@dp.callback_query_handler(text='slave_stats')
async def slave_statistics(call: CallbackQuery):
	user_id = call.message.chat.id
	slaves_count = await db.get_slaves(user_id)
	slaves_list = await db.get_slaves_spisok(user_id)
	total_earn = await db.earning(user_id)
	
	slaves_info = []
	for i, slave_id in enumerate(slaves_list[:10], 1):  # Show first 10 slaves
		try:
			slave = await db.get_document(slave_id)
			if slave:
				try:
					chat = await bot.get_chat(slave_id)
					name = chat.first_name
					url = hlink(name, f"tg://user?id={slave_id}")
					slaves_info.append(f"{i}. {url} - доход: {slave['earn']}💰")
				except Exception as e:
					logging.error(f"Error getting chat info for slave {slave_id}: {e}")
					slaves_info.append(f"{i}. ID: {slave_id} - доход: {slave['earn']}💰")
		except Exception as e:
			logging.error(f"Error getting slave info: {e}")
	
	stats_text = f"📊 Статистика ваших рабов\n\n" \
				f"Всего рабов: {slaves_count}\n" \
				f"Общий доход: {total_earn}💰\n\n"
	
	if slaves_info:
		stats_text += "Ваши рабы:\n" + "\n".join(slaves_info)
	else:
		stats_text += "У вас пока нет рабов."
	
	try:
		await call.message.edit_text(stats_text, reply_markup=kb.send_link(await get_start_link(user_id, encode=True)), parse_mode="HTML")
	except Exception as e:
		logging.error(f"Error updating slave stats message: {e}")
		await call.answer("Ошибка при обновлении статистики рабов", show_alert=True)
	await call.answer()

async def on_startup(dp):
	# Initialize robot slaves
	try:
		await robot_manager.initialize()
		
		# Start robot simulation if needed
		if config.has_option('robots', 'auto_start') and config.getboolean('robots', 'auto_start'):
			asyncio.create_task(robot_manager.start_simulation())
	except Exception as e:
		logging.error(f"Error initializing robot slaves: {e}")
	
	logging.info("Bot started")

async def is_robot_user(user_id):
	"""Check if a user is a robot user (negative ID) or doesn't exist"""
	if isinstance(user_id, int) and user_id < 0:
		return True
	
	try:
		user_doc = await db.get_document(user_id)
		return user_doc and user_doc.get('is_robot', False)
	except Exception:
		return False

async def safe_get_chat_link(chat_id, default_text=None):
	"""Safely get a chat link with proper error handling"""
	if not chat_id:
		return default_text or "Неизвестный пользователь"
		
	try:
		# Check if it's a robot user first
		if await is_robot_user(chat_id):
			# For robot users, try to get their name from the database
			user_doc = await db.get_document(chat_id)
			if user_doc and 'robot_name' in user_doc:
				return f"🤖 {user_doc['robot_name']} (ID: {chat_id})"
			return f"🤖 Робот (ID: {chat_id})"
			
		# For real users, try to get info from Telegram
		chat = await bot.get_chat(chat_id)
		name = chat.first_name
		return hlink(name, f"tg://user?id={chat_id}")
	except Exception as e:
		logging.error(f"Error getting chat info for {chat_id}: {e}")
		return default_text or f"ID: {chat_id}"

if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
