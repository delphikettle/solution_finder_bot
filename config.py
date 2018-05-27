import os
import sqlite3

token = '584233350:AAETHIoLoFzGB9ie9goYXxP7HLDLhC1_14k'
db = sqlite3.connect('local.sqlite', check_same_thread=False)


def migrate():
    cursor = db.cursor()
    migrations_log = open('.migrations.log', 'a+')
    migrations_log.seek(0)
    migrations = set([line.replace('\n', '') for line in migrations_log.readlines()])

    for filename in filter(lambda x: x.endswith('.sql'), os.listdir('migrations/')):
        if filename not in migrations:
            with open('migrations/' + filename) as queryfile:
                cursor.executescript(queryfile.read())
            migrations_log.write(filename + '\n')
    migrations_log.close()
    cursor.close()


db.create_function('myLower', 1, lambda x: x.lower())


migrate()
