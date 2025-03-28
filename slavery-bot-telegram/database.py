import motor.motor_asyncio
import certifi
import os
from configparser import ConfigParser
from datetime import datetime

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Path to config file
config_path = os.path.join(script_dir, 'config.ini')

config = ConfigParser()
config.read(config_path)

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
            'count': 0,
            'is_robot': False,
            'last_activity': datetime.now().isoformat()
        }
        await posts.insert_one(post_data)


async def update_activity(chat_id):
    """Update the user's last activity timestamp"""
    await posts.update_one(
        {'chat_id': chat_id},
        {'$set': {'last_activity': datetime.now().isoformat()}}
    )


async def sender():
    cnt = await posts.distinct("chat_id")
    return cnt


async def change_field(chat_id, field, key):
    await posts.update_one({'chat_id': chat_id}, {'$set': {field: key}})
    # Update activity timestamp when interacting with the user
    if field != 'last_activity':
        await update_activity(chat_id)


async def get_document(chat_id):
    doc = await posts.find_one({'chat_id': chat_id})
    # Update activity timestamp when getting user document
    if doc and not doc.get('is_robot', False):
        await update_activity(chat_id)
    return doc


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


async def get_real_users_count():
    """Get the count of real (non-robot) users"""
    count = await posts.count_documents({'is_robot': {'$ne': True}})
    return count


async def get_active_users_count(hours=24):
    """Get the count of active real users in the last X hours"""
    from datetime import datetime, timedelta
    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    count = await posts.count_documents({
        'is_robot': {'$ne': True},
        'last_activity': {'$gte': cutoff_time}
    })
    
    return count


async def get_user_statistics():
    """Get various statistics about users and slaves"""
    total_users = await posts.count_documents({})
    real_users = await get_real_users_count()
    robot_users = await posts.count_documents({'is_robot': True})
    active_users = await get_active_users_count(24)
    
    total_slaves = sum([doc['count'] async for doc in posts.find({})])
    total_balance = sum([doc['balance'] async for doc in posts.find({})])
    
    return {
        "total_users": total_users,
        "real_users": real_users,
        "robot_users": robot_users,
        "active_users_24h": active_users,
        "total_slaves": total_slaves,
        "total_balance": total_balance
    }
