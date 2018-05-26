from math import copysign

import telebot
from telebot import apihelper
from telebot import types

from config import token, db

markup_common = types.ReplyKeyboardMarkup()
markup_common.row('/↩ назад', '/⤵️ открыть')

apihelper.proxy = {
    # 'http':'socks5://138.201.46.150:1080',
    # 'https':'socks5://138.201.46.150:1080'
    'http': 'socks5://46.8.32.238:8080',
    'https': 'socks5://46.8.32.238:8080'
}
bot = telebot.TeleBot(token)


@bot.message_handler(commands=['↩', '🔙'])
def back_command(message):
    cursor = db.cursor()
    cursor.execute('select state from User where id=?', [message.from_user.id])
    state, = cursor.fetchall()[0]
    path = state.split('/')
    while len(path) > 1 and path[-1] == '':
        path = path[:-1]
    path = path[:-1]
    state = '/'.join(path) + '/'
    cursor.execute('update User set state=? where id=?', [state, message.from_user.id])
    db.commit()
    cursor.close()
    send_stuff_by_state(message.from_user.id)


@bot.message_handler(commands=['⤵️'], func=lambda message: message.reply_to_message is not None)
def open_command(message):
    cursor = db.cursor()
    text = str(message.text.strip())

    cursor.execute('select dispute_id, feedback_id from Messages WHERE chat_id={0} and message_id={1} limit 1'.format(
        message.chat.id, message.reply_to_message.message_id))
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(message.chat.id, 'Ты чот попутал, не на что отвечать)', reply_markup=markup_common)
        cursor.close()
        return

    dispute_id, feedback_id = rows[0]
    if dispute_id is not None:
        step_type = 'd'
    else:
        cursor.execute('select is_answer from Feedback where id=?', [feedback_id])
        is_answer, = cursor.fetchall()[0]
        if is_answer:
            step_type = 'a'
        else:
            step_type = 'c'
    item_id = dispute_id or feedback_id
    cursor.execute('update User set state=state||? WHERE id=?',
                   ['{}{}/'.format(step_type, item_id), message.from_user.id])
    db.commit()
    cursor.close()
    send_stuff_by_state(message.from_user.id)


def connect_message(message, dispute_id=None, feedback_id=None):
    cursor = db.cursor()
    cursor.execute("insert into Messages(chat_id, message_id, dispute_id,feedback_id) VALUES (?,?,?,?)",
                   [message.chat.id, message.message_id, dispute_id, feedback_id])
    db.commit()
    cursor.close()


def send_stuff_by_state(user_id):
    cursor = db.cursor()
    cursor.execute('select state from User where id={0}'.format(user_id))
    state = cursor.fetchall()[0][0]
    path = state.split('/')
    for step in reversed(path):
        if step:
            step_type = step[0]
            if step_type == 'd':
                dispute_id = int(step[1:])
                cursor.execute('select caption, content from Dispute where id=?', [dispute_id])
                d_caption, d_content = cursor.fetchall()[0]

                # get answers
                answers = []
                pluses, minuses = 0, 0
                cursor.execute(
                    'select id, content, for, rating from Feedback where parent_id=? and is_answer ORDER BY rating',
                    [dispute_id])
                for answer_id, content, is_for, rating in cursor.fetchall():
                    if is_for is not None:
                        if is_for:
                            pluses += 1
                        else:
                            minuses += 1
                    if content:
                        answers.append((answer_id, content, rating))

                # send messages
                message = bot.send_message(user_id, '{0}➕ {1}➖\nВопрос: {2}\n\n{3}'.format(pluses, minuses, d_caption,
                                                                                           d_content),
                                           reply_markup=markup_common)
                connect_message(message, dispute_id=dispute_id)

                for answer_id, content, rating in answers:
                    mess = bot.send_message(user_id,
                                            '{0}✔\nОтвет №{1}: {2}'.format(round(rating, 2), answer_id, content),
                                            reply_to_message_id=message.message_id)
                    connect_message(mess, feedback_id=answer_id)

            elif step_type == 'a':
                answer_id = int(step[1:])
                cursor.execute('select content, rating from Feedback where id=? and is_answer', [answer_id])
                a_content, a_rating = cursor.fetchall()[0]

                # get comments
                comments = []
                pluses, minuses = 0, 0
                cursor.execute(
                    'select id, content, for, rating from Feedback where parent_id=? and not is_answer ORDER BY rating',
                    [answer_id])
                for comment_id, content, is_for, rating in cursor.fetchall():
                    if is_for is not None:
                        if is_for:
                            pluses += 1
                        else:
                            minuses += 1
                    if content:
                        comments.append((comment_id, content, rating, is_for))

                # send messages
                message = bot.send_message(user_id, '{0}➕ {1}➖\n{2}✔\nОтвет №{3}: {4}'.format(pluses, minuses,
                                                                                              round(a_rating, 2),
                                                                                              answer_id, a_content),
                                           reply_markup=markup_common)
                connect_message(message, feedback_id=answer_id)

                for comment_id, content, rating, is_for in comments:
                    mess = bot.send_message(user_id, (
                        '' if is_for is None else ('➕ ' if is_for else '➖ ')) + 'Коммент (id={1})({0}✔): {2}'.format(
                        round(rating, 2), comment_id, content),
                                            reply_to_message_id=message.message_id, reply_markup=markup_common)
                    connect_message(mess, feedback_id=comment_id)

            elif step_type == 'c':
                main_comment_id = int(step[1:])
                cursor.execute('select content, for, rating from Feedback where id=? and not is_answer',
                               [main_comment_id])
                c_content, is_for, a_rating = cursor.fetchall()[0]

                # get comments
                comments = []
                pluses, minuses = 0, 0
                cursor.execute(
                    'select id, content, for, rating from Feedback where parent_id=? and not is_answer ORDER BY rating',
                    [main_comment_id])
                for comment_id, content, is_for, rating in cursor.fetchall():
                    if is_for is not None:
                        if is_for:
                            pluses += 1
                        else:
                            minuses += 1
                    if content:
                        comments.append((comment_id, content, rating, is_for))

                # send messages
                message = bot.send_message(user_id, ('' if is_for is None else (
                    '➕ ' if is_for else '➖ ')) + 'Коммент (id={3})({0}➕ {1}➖)({2}✔): {4}'.format(pluses, minuses,
                                                                                                 round(a_rating, 2),
                                                                                                 main_comment_id,
                                                                                                 c_content),
                                           reply_markup=markup_common)
                connect_message(message, feedback_id=main_comment_id)

                for comment_id, content, rating, is_for in comments:
                    mess = bot.send_message(user_id, (
                        '' if is_for is None else ('➕ ' if is_for else '➖ ')) + 'Коммент (id={1})({0}✔): {2}'.format(
                        round(rating, 2), comment_id, content),
                                            reply_to_message_id=message.message_id, reply_markup=markup_common)
                    connect_message(mess, feedback_id=comment_id)

            cursor.close()
            return

    cursor.close()


def func_for_rating(x):
    return copysign(abs(x / 2) ** 0.9, x) + 1


def update_feedback_rating(feedback_id):
    s = 0
    cursor = db.cursor()
    cursor.execute('select for,rating from Feedback where parent_id=? and for is not null', [feedback_id])
    for sign, rating in cursor.fetchall():
        s += (1 if sign else -1) * func_for_rating(rating)
    cursor.execute('update Feedback set rating=? where id=?', [s, feedback_id])
    db.commit()
    cursor.execute('select is_answer,parent_id from Feedback where id=?', [feedback_id])
    is_answer, parent_id = cursor.fetchall()[0]
    if not is_answer:
        update_feedback_rating(parent_id)
    cursor.close()


@bot.message_handler(commands=['start'])
def start(message):
    cursor = db.cursor()
    try:
        cursor.execute("insert into User(id,state) values ({0},'{1}')".format(message.from_user.id, '/'))
        db.commit()
    except Exception as e:
        if 'UNIQUE' in e.args[0]:
            pass
        else:
            raise
    cursor.close()


@bot.message_handler(commands=['new_dispute'])
def new_dispute(message):
    cursor = db.cursor()
    text = str(message.text).replace('/new_dispute', '').strip()
    caption = text.split('\n')[0]
    content = ''
    try:
        content = text.split('\n', 1)[1]
    except IndexError:
        pass

    if caption:
        cursor.execute(
            "insert into Dispute(user_id,caption,content) VALUES  ({0},'{1}','{2}')".format(message.from_user.id,
                                                                                            caption, content))

        sent_message = bot.send_message(message.chat.id, 'Вопрос "{0}" создан'.format(caption),
                                        reply_markup=markup_common)
        connect_message(message, dispute_id=cursor.lastrowid)
        connect_message(sent_message, dispute_id=cursor.lastrowid)

        cursor.execute('update User set state=state||? WHERE id=?',
                       ['d{}/'.format(cursor.lastrowid), message.from_user.id])
        db.commit()

    cursor.close()


@bot.message_handler(func=lambda message: message.reply_to_message is not None)
def reply_messages(message):
    cursor = db.cursor()
    text = str(message.text.strip())

    cursor.execute('select dispute_id, feedback_id from Messages WHERE chat_id={0} and message_id={1} limit 1'.format(
        message.chat.id, message.reply_to_message.message_id))
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(message.chat.id, 'Ты чот попутал, не на что отвечать)', reply_markup=markup_common)
        cursor.close()
        return

    dispute_id, feedback_id = rows[0]

    is_answer = dispute_id is not None
    parent_id = dispute_id or feedback_id

    first_line = text.splitlines()[0].strip()
    if first_line == '+':
        for_sign = True
    elif first_line == '-':
        for_sign = False
    else:
        for_sign = None
    if for_sign is not None:
        try:
            content = text.split('\n', 1)[1].strip()
        except IndexError:
            content = None
    else:
        content = text

    if is_answer and for_sign is not None and content:
        bot.send_message(message.chat.id, 'Ты тупой? Нельзя отвечать, оценивая вопрос, дубина',
                         reply_markup=markup_common)
        cursor.close()
        return

    params = [message.from_user.id, for_sign, parent_id, content, is_answer]
    cursor.execute("insert into Feedback(user_id, for, parent_id, rating, content, is_answer) VALUES (?,?,?,0,?,?)",
                   params)
    sent_message = bot.send_message(message.chat.id,
                                    (('Ответ' if is_answer else 'Коммент') + ' успешно создан') if content else (
                                            ('Вопрос' if is_answer else 'Ответ/коммент') + ' успешно оценён'),
                                    reply_markup=markup_common)
    if content:
        connect_message(message, feedback_id=cursor.lastrowid)
        connect_message(sent_message, feedback_id=cursor.lastrowid)
    feedback_id = cursor.lastrowid
    cursor.execute('update User set state=state||? WHERE id=?',
                   ['{}{}/'.format('a' if is_answer else 'c', cursor.lastrowid), message.from_user.id])
    db.commit()
    update_feedback_rating(feedback_id)
    send_stuff_by_state(message.from_user.id)
    cursor.close()


@bot.message_handler(content_types=['text'])
def repeat_all_messages(message):
    print(dir(message))
    print(message.text)
    print(message.message_id)
    print(message.forward_from)
    print(message.reply_to_message)
    print(message.entities)
    print('user', message.from_user)
    print('chat', message.chat)
    bot.send_message(message.chat.id, message.text, reply_markup=markup_common)
    send_stuff_by_state(message.from_user.id)


if __name__ == '__main__':
    print('starting')
    bot.polling(none_stop=True)
