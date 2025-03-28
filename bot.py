import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import Message
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


config = ConfigParser()
config.read('config.ini')

token = config.get('main', 'token')
admin = config.get('main', 'admin')


logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=token)
dp = Dispatcher(bot, storage=storage)

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
		await message.answer('Привет, вот меню', reply_markup=kb.menu)
	else:
		if args != '':
			payload = decode_payload(args)
			if str(message.chat.id) == str(payload):
				await message.answer('Нельзя наткнуться на свою же ловушку!', reply_markup=kb.menu)
			else:
				user = await db.get_document(message.chat.id)
				if user['owner'] == 0:
					await db.change_field(message.chat.id, 'owner', int(payload))
					await message.answer('🪤Вы попались на <b>ловушку</b>!\nТеперь вы являетесь рабом пользователя <b>{}</b>, вы можете освободиться за определенную сумму.'.format(payload), parse_mode='HTML', reply_markup=kb.menu)
				else:
					await message.answer('🙅Вы попались на <b>ловушку</b>, но вы не станете рабом пользователя <b>{}</b>, так как вы уже являетесь чьей-то собственностью!'.format(payload), parse_mode='HTML', reply_markup=kb.menu)
		else:
			await message.answer('Привет, вот меню', reply_markup=kb.menu)


@dp.message_handler(text='👥Привлечь рабов', chat_type=['private'])
async def slaves_trap(message: Message):
	await db.insert(message.chat.id)
	slaves = await db.get_slaves(message.chat.id)
	await db.change_field(message.chat.id, 'count', slaves)
	link = await get_start_link(message.chat.id, encode=True)
	keyboard = kb.send_link(link)
	await message.answer(
		'Вот твоя ссылка для <b>привлечения рабов</b>:\n{}\n\n'
		'<b>Делись ссылкой с друзьями и знакомыми, каждый новый игрок, перешедший по твоей ссылке, становится твоим рабом.\n'
		'Каждый раб приносит тебе определенный доход, рабов можно усовершенствовать.</b>'.format(link), parse_mode='HTML', reply_markup=keyboard)


@dp.message_handler(text='👤Профиль', chat_type=['private'])
async def user_doc(message: Message):
	await db.insert(message.chat.id)
	earn = await db.earning(message.chat.id)
	user = await db.get_document(message.chat.id)
	slaves = await db.get_slaves(message.chat.id)
	await db.change_field(message.chat.id, 'count', slaves)
	if user['owner'] != 0:
		chat = await bot.get_chat(user['owner'])
		name = chat.first_name
		url = hlink(name, f"tg://user?id={user['owner']}")
		owner = 'Вы явялетесь <b>рабом</b>!\nВаш <b>владелец</b> {}'.format(
				url)
		if user['ransom'] != 0:
			cost = user['ransom'] * 500
		else:
			cost = 500
		keyboard = kb.ranout(cost, 1)
	else:
		owner = ''
		keyboard = kb.ranout(123, 0)
	await message.answer('Ваш <b>профиль</b>:\n\nID: <b>{}</b>\nБаланс: <b>{}</b>💰\nРабов: <b>{}</b>\nДоход: <b>{}</b>💰\n\n{}'.format(message.chat.id, user['balance'], slaves, earn, owner), parse_mode='HTML', reply_markup=keyboard)


@dp.message_handler(text='💰Купить рабов', chat_type=['private'])
async def buy_slaves(message: Message, state: FSMContext):
	await db.insert(message.chat.id)
	myslaves = await db.get_slaves(message.chat.id)
	await db.change_field(message.chat.id, 'count', myslaves)
	slaves = await db.get_all_slaves(message.chat.id)
	if slaves == []:
		await message.answer('Не найдено пользователей для приобретения', reply_markup=kb.menu)
	else:
		chat = await bot.get_chat(slaves[0])
		user = await db.get_document(slaves[0])
		name = chat.first_name
		url = hlink(name, f"tg://user?id={slaves[0]}")
		if user['owner'] != 0:
			owner = await bot.get_chat(user['owner'])
			owner_name = owner.first_name
			owner_url = hlink(owner_name, f"tg://user?id={user['owner']}")
			await message.answer('Пользователь <b>{}</b>\nВ <b>рабстве</b> у {}\nДоход: {}💰'.format(url, owner_url, user['earn']), parse_mode='HTML', reply_markup=kb.pagination(0, slaves[0], slaves, user['earn'] * 50))
		else:
			await message.answer('Пользователь <b>{}</b>\nДоход: {}💰'.format(url, user['earn']), parse_mode='HTML', reply_markup=kb.pagination(0, slaves[0], slaves, user['earn'] * 50))
		await state.update_data(slaves=slaves)


@dp.message_handler(text='🔝Топ', chat_type=['private'])
async def buy_slaves(message: Message, state: FSMContext):
	await db.insert(message.chat.id)
	slaves = await db.get_slaves(message.chat.id)
	await db.change_field(message.chat.id, 'count', slaves)
	sorted = await db.sort_by_slaves()
	top = []
	for index, i in enumerate(sorted, 1):
		chat = await bot.get_chat(i['chat_id'])
		name = chat.first_name
		url = hlink(name, f"tg://user?id={i['chat_id']}")
		top.append(f'{fc.emojies(index)} место: {url} - {i["count"]} раб(ов)')
	await message.answer('⛓Топ по количеству рабов:\n{}'.format('\n'.join(str(v) for v in top)), reply_markup=kb.topbuttons, parse_mode='HTML')


@dp.message_handler(commands='admin', chat_type=['private'])
async def admin_panel(message: types.Message):
	if int(message.chat.id) == int(admin):
		await message.answer('Админ-панель', reply_markup=kb.apanel)


@dp.callback_query_handler(lambda call: call.data.startswith('by'))
async def topcallback(call: types.CallbackQuery):
	if call.data == 'byslaves':
		sorted = await db.sort_by_slaves()
		top = []
		for index, i in enumerate(sorted, 1):
			chat = await bot.get_chat(i['chat_id'])
			name = chat.first_name
			url = hlink(name, f"tg://user?id={i['chat_id']}")
			top.append(
				f'{fc.emojies(index)} место: {url} - {i["count"]} раб(ов)')
		try:
			await call.message.edit_text('⛓Топ по количеству рабов:\n{}'.format('\n'.join(str(v) for v in top)), reply_markup=kb.topbuttons, parse_mode='HTML')
		except BaseException:
			await call.answer('Вы и так уже на этой кнопке!', show_alert=True)
	elif call.data == 'bybalance':
		sorted = await db.sort_by_balance()
		top = []
		for index, i in enumerate(sorted, 1):
			chat = await bot.get_chat(i['chat_id'])
			name = chat.first_name
			url = hlink(name, f"tg://user?id={i['chat_id']}")
			top.append(f'{fc.emojies(index)} место: {url} - {i["balance"]}💰')
		try:
			await call.message.edit_text('💰Топ по количеству денег:\n{}'.format('\n'.join(str(v) for v in top)), reply_markup=kb.topbuttons, parse_mode='HTML')
		except BaseException:
			await call.answer('Вы и так уже на этой кнопке!', show_alert=True)


@dp.callback_query_handler(lambda call: call.data.startswith('next'))
async def next_page(call: types.CallbackQuery, state: FSMContext):
	page = int(call.data.split('_')[1])
	data = await state.get_data()
	slaves = data.get('slaves')
	if len(slaves) == page:
		await call.answer('Пользователей для приобретения больше нет', show_alert=True)
	else:
		selected = slaves[page]
		chat = await bot.get_chat(selected)
		user = await db.get_document(selected)
		name = chat.first_name
		url = hlink(name, f"tg://user?id={selected}")
		if user['owner'] != 0:
			owner = await bot.get_chat(user['owner'])
			owner_name = owner.first_name
			owner_url = hlink(owner_name, f"tg://user?id={user['owner']}")
			await call.message.edit_text('Пользователь <b>{}</b>\nВ <b>рабстве</b> у {}\nДоход: {}💰'.format(url, owner_url, user['earn']), parse_mode='HTML', reply_markup=kb.pagination(page, selected, slaves, user['earn'] * 50))
		else:
			await call.message.edit_text('Пользователь <b>{}</b>\nДоход: {}💰'.format(url, user['earn']), parse_mode='HTML', reply_markup=kb.pagination(page, selected, slaves, user['earn'] * 50))


@dp.callback_query_handler(lambda call: call.data.startswith('back'))
async def back_page(call: types.CallbackQuery, state: FSMContext):
	page = int(call.data.split('_')[1])
	data = await state.get_data()
	slaves = data.get('slaves')
	selected = slaves[page]
	chat = await bot.get_chat(selected)
	user = await db.get_document(selected)
	name = chat.first_name
	url = hlink(name, f"tg://user?id={selected}")
	if user['owner'] != 0:
		owner = await bot.get_chat(user['owner'])
		owner_name = owner.first_name
		owner_url = hlink(owner_name, f"tg://user?id={user['owner']}")
		await call.message.edit_text('Пользователь <b>{}</b>\nВ <b>рабстве</b> у {}\nДоход: {}💰'.format(url, owner_url, user['earn']), parse_mode='HTML', reply_markup=kb.pagination(page, selected, slaves, user['earn'] * 50))
	else:
		await call.message.edit_text('Пользователь <b>{}</b>\nДоход: {}💰'.format(url, user['earn']), parse_mode='HTML', reply_markup=kb.pagination(page, selected, slaves, user['earn'] * 50))


@dp.callback_query_handler(lambda call: call.data.startswith('buy'))
async def buy_slave(call: types.CallbackQuery, state: FSMContext):
	splitted = call.data.split('_')[1].split('-')
	slave = int(splitted[0])
	cost = int(splitted[1])
	data = await state.get_data()
	slaves = data.get('slaves')
	me = await db.get_document(call.message.chat.id)
	slavedoc = await db.get_document(slave)
	if slavedoc['owner'] == call.message.chat.id:
		await call.answer('Данный раб и так уже ваш.', show_alert=True)
	elif me['owner'] == slavedoc['chat_id']:
		await call.answer('Нельзя купить своего владельца', show_alert=True)
	else:
		if me['balance'] < cost:
			await call.answer('Недостаточно денег на балансе', show_alert=True)
		else:
			await db.change_field(call.message.chat.id, 'balance', me['balance'] - cost)
			await db.change_field(slave, 'owner', call.message.chat.id)
			slaves.remove(slave)
			if slaves != []:
				await state.update_data(slaves=slaves)
				chat = await bot.get_chat(slaves[0])
				user = await db.get_document(slaves[0])
				name = chat.first_name
				url = hlink(name, f"tg://user?id={slaves[0]}")
				if user['owner'] != 0:
					owner = await bot.get_chat(user['owner'])
					owner_name = owner.first_name
					owner_url = hlink(
						owner_name, f"tg://user?id={user['owner']}")
					await call.message.edit_text('Пользователь <b>{}</b>\nВ <b>рабстве</b> у {}\nДоход: {}💰'.format(url, owner_url, user['earn']), parse_mode='HTML', reply_markup=kb.pagination(0, slaves[0], slaves, user['earn'] * 50))
				else:
					await call.message.edit_text('Пользователь <b>{}</b>\nДоход: {}💰'.format(url, user['earn']), parse_mode='HTML', reply_markup=kb.pagination(0, slaves[0], slaves, user['earn'] * 50))
				await call.answer('Раб {} теперь ваша собственность'.format(slave), show_alert=True)
			else:
				await call.message.edit_text('{}\n\nРаб <b>приобретен</b>'.format(call.message.html_text), parse_mode='HTML')


@dp.callback_query_handler(lambda call: call.data.startswith('go'))
async def lethimgo(call: types.CallbackQuery):
	slave = int(call.data.split('_')[1])
	await db.change_field(slave, 'owner', 0)
	await call.message.edit_text('{}\n\n<b>Раб отпущен</b>!'.format(call.message.html_text), parse_mode='HTML')


@dp.callback_query_handler(lambda call: call.data.startswith('unext'))
async def next_page_slaves(call: types.CallbackQuery, state: FSMContext):
	page = int(call.data.split('_')[1])
	data = await state.get_data()
	slaves = data.get('slaves')
	if len(slaves) == page:
		await call.answer('Рабов больше нет', show_alert=True)
	else:
		selected = slaves[page]
		chat = await bot.get_chat(selected)
		user = await db.get_document(selected)
		name = chat.first_name
		url = hlink(name, f"tg://user?id={selected}")
		await call.message.edit_text('Раб: <b>{}</b>\nДоход: {}💰'.format(url, user['earn']), reply_markup=kb.slave_menu(page, slaves, selected, user['earn'] * 50), parse_mode='HTML')
		await state.update_data(page=page)


@dp.callback_query_handler(lambda call: call.data.startswith('uback'))
async def back_page_upgrade(call: types.CallbackQuery, state: FSMContext):
	page = int(call.data.split('_')[1])
	data = await state.get_data()
	slaves = data.get('slaves')
	selected = slaves[page]
	chat = await bot.get_chat(selected)
	user = await db.get_document(selected)
	name = chat.first_name
	url = hlink(name, f"tg://user?id={selected}")
	await call.message.edit_text('Раб: <b>{}</b>\nДоход: {}💰'.format(url, user['earn']), reply_markup=kb.slave_menu(page, slaves, selected, user['earn'] * 50), parse_mode='HTML')
	await state.update_data(page=page)


@dp.callback_query_handler(lambda call: call.data.startswith('upgrade'))
async def upgrade_slave(call: types.CallbackQuery, state: FSMContext):
	splitted = call.data.split('_')[1].split('-')
	slave = int(splitted[0])
	cost = int(splitted[1])
	data = await state.get_data()
	slaves = data.get('slaves')
	page = data.get('page')
	if page is not None:
		page = page
	else:
		page = 0
	me = await db.get_document(call.message.chat.id)
	slavedoc = await db.get_document(slave)
	if me['balance'] < cost:
		await call.answer('Недостаточно денег на балансе', show_alert=True)
	else:
		await db.change_field(call.message.chat.id, 'balance', me['balance'] - cost)
		await db.change_field(slave, 'earn', slavedoc['earn'] * 5)
		chat = await bot.get_chat(slaves[page])
		user = await db.get_document(slaves[page])
		name = chat.first_name
		url = hlink(name, f"tg://user?id={slaves[page]}")
		await call.message.edit_text('Раб: <b>{}</b>\nДоход: {}💰'.format(url, user['earn']), reply_markup=kb.slave_menu(int(page), slaves, slave, user['earn'] * 50), parse_mode='HTML')
		await call.answer('Раб {} успешно улучшен.\nТеперь его доход составляет: {}💰'.format(slave, slavedoc['earn'] * 5), show_alert=True)


@dp.callback_query_handler(text='slaves')
async def user_slaves(call: types.CallbackQuery, state: FSMContext):
	slaves = await db.get_slaves_spisok(call.message.chat.id)
	if slaves == []:
		await call.answer('У вас пока нет рабов.', show_alert=True)
	else:
		user = await db.get_document(slaves[0])
		chat = await bot.get_chat(slaves[0])
		name = chat.first_name
		url = hlink(name, f"tg://user?id={slaves[0]}")
		msg = await call.message.answer('Список ваших рабов:')
		await msg.reply('Раб: <b>{}</b>\nДоход: {}'.format(url, user['earn']), reply_markup=kb.slave_menu(0, slaves, slaves[0], user['earn'] * 50), parse_mode='HTML')
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
	if call.message.chat.id not in timeout or time.time(
	) >= timeout[call.message.chat.id]:
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
				chat = await bot.get_chat(user['owner'])
				name = chat.first_name
				url = hlink(name, f"tg://user?id={user['owner']}")
				owner = 'Вы явялетесь <b>рабом</b>!\nВаш <b>владелец</b> {}'.format(
						url)
				if user['ransom'] != 0:
					cost = user['ransom'] * 500
				else:
					cost = 500
				keyboard = kb.ranout(cost, 1)
			else:
				owner = ''
				keyboard = kb.ranout(123, 0)
			await call.message.edit_text('Ваш <b>профиль</b>:\n\nID: <b>{}</b>\nБаланс: <b>{}</b>💰\nРабов: <b>{}</b>\nДоход: <b>{}</b>💰\n\n{}'.format(call.message.chat.id, user['balance'], slaves, earn, owner), parse_mode='HTML', reply_markup=keyboard)
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
	await message.answer('Привет, вот меню', reply_markup=kb.menu)


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)
