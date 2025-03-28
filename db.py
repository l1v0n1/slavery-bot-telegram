import sqlite3


connection = sqlite3.connect("data.db")
q = connection.cursor()


def insert(peerid):
    q.execute(
        """CREATE TABLE IF NOT EXISTS users (
		chat_id INT DEFAULT {}, 
		owner INT DEFAULT 0, 
		earn INT DEFAULT 1, 
        ransom INT DEFAULT 0,
        balance INT DEFAULT 0
		)""".format(
            peerid
        )
    )
    cursor = q.execute("SELECT * FROM users")

    if cursor.fetchall() == [] or cursor.fetchall() is None:
        q.execute(
            "INSERT INTO users (chat_id, owner, earn, ransom, balance) VALUES (?, ?, ?, ?, ?)".format(peerid),
            (peerid, 0, 1, 0, 0),
        )
    connection.commit()


def fullbase(peerid):
    cursor = q.execute("SELECT * FROM users")
    data = q.execute("SELECT * FROM users").fetchall()
    data = data[0]
    chat_id = data[0]
    talk = data[1]
    speed = data[2]

    return dict(
        peer_id=chat_id,
        talk=talk,
        speed=speed,
        textbase=[i for i in texts if i is not None],
    )


def update_text_base(peerid, text):
    q.execute("INSERT INTO users (textbase) VALUES (?)", (text,))
    connection.commit()


def clear_text_base(peerid):
    q.execute("UPDATE users SET textbase = Null")
    connection.commit()


def change_field(peerid, field, key):
    q.execute("UPDATE users SET {} = {}".format(str(peerid), field, key))
    connection.commit()


def count():
    cursor = q.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return len(cursor.fetchall())


def add_new_field():
    all = q.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for i in all:
        peer = i[0].split("peer")[1]
        q.execute("ALTER TABLE users ADD COLUMN nextgen INT;".format(peer))
    connection.commit()
