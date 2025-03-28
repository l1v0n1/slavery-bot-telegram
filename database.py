import motor.motor_asyncio
import certifi
from configparser import ConfigParser


config = ConfigParser()

config.read('config.ini')

mongodburl = config.get('main', 'mongourl')

# Работа с базой данных
client = motor.motor_asyncio.AsyncIOMotorClient(
    mongodburl, ssl=False)
db = client.slaves
posts = db.posts


async def check(chat_id):
    check = await posts.find_one({'chat_id': chat_id})
    if check is None:
        return False
    else:
        return True


async def insert(chat_id):
    row = await check(chat_id)
    if row is False:
        post_data = {
            'chat_id': chat_id,
            'owner': 0,
            'earn': 1,
            'ransom': 0,
            'balance': 0,
            'count': 0
        }
        await posts.insert_one(post_data)


async def sender():
    cnt = await posts.distinct("chat_id")
    return cnt


async def change_field(chat_id, field, key):
    await posts.update_one({'chat_id': chat_id}, {'$set': {field: key}})


async def get_document(chat_id):
    return await posts.find_one({'chat_id': chat_id})


async def earning(chat_id):
    list = [doc async for doc in posts.find({'owner': chat_id})]
    earn = [i['earn'] for i in list]
    return sum(earn)


async def get_slaves(chat_id):
    list = [doc async for doc in posts.find({'owner': chat_id})]
    return len(list)


async def get_slaves_spisok(chat_id):
    list = [doc async for doc in posts.find({'owner': chat_id})]
    ids = [i['chat_id'] for i in list]
    return ids


async def claim_earnings(chat_id):
    earn = await earning(chat_id)
    user = await get_document(chat_id)
    await change_field(chat_id, 'balance', user['balance'] + earn)
    return earn


async def get_all_slaves(chat_id):
    list = [doc async for doc in posts.find({'$and': [{'owner': {'$ne': chat_id}}, {'chat_id': {'$ne': chat_id}}]})]
    ids = [i['chat_id'] for i in list]
    return ids


async def sort_by_slaves():
    list = [doc async for doc in posts.find({}).sort('count', -1).limit(10)]
    return list


async def sort_by_balance():
    list = [doc async for doc in posts.find({}).sort('balance', -1).limit(10)]
    return list
