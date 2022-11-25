"""Used to collect search analytics data(not user data).
Telegram doesn't provide us any of your sensitive information, so you can be assured.
Also the bot operates under privacy mode of telegram, so we can't read your group messages.

All data related to user is hashed, so no one identify you.
    """
from deta import Deta
from pytz import timezone
from hashlib import shake_128 as hash
import pprint
import time

IST = timezone('Asia/Kolkata')  # Indian Standard Time (+5:30)
INITIALIZED = False  # Check if analytics is set up


def initialize(DETA_TOKEN):
    # We are using Deta Base service from deta.sh to store analytics data
    if DETA_TOKEN is None:  # Mark as analytics is set up
        return

    deta = Deta(DETA_TOKEN)
    global db
    db = deta.Base("skb-database-1")


records = {}  # used to record last time user made an inline query


def track(update, query, preference=None, available_sources=[], provided_from=None, inline=False):
    if not INITIALIZED:  # Don't do anything if analytics is not set up
        return

    data = {}

    # These are infromation about your search and results
    data['query'] = query  # the word you searched
    data['preference'] = str(preference)  # any dictionary you preferred for meaning, otherwise None
    data['available_sources'] = list(available_sources)  # in which dictionaries your word was available
    data['provided_from'] = str(provided_from)  # dictionary whose meaning was shown to you
    data['inline'] = inline  # is search made from inline mode ?
    #

    if update.effective_user is not None:  # will be None for channel posts only
        user_id = update.effective_user.id
        user_name = update.effective_user.name

        user_code = str(user_id) + user_name  # both id & name mixed to make it harder
        user_hash = hash(user_code.encode()).hexdigest(8)  # converted to a unique, meaningless, irreversible code (no one can find you!)

        data['user_hash'] = user_hash  # see, we haven't stored your name or id

    if not inline:  # Inline mode deosn't contain following details
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type  # Type of chat (group, channel, private)
        chat_title = update.effective_chat.title  # name of group, channel
        date_time = update.effective_message.date.astimezone(tz=IST).isoformat()

        chat_code = str(chat_id) + str(chat_title)  # both id & title mixed to make it harder
        chat_hash = hash(chat_code.encode()).hexdigest(8)  # converted to a unique, meaningless, irreversible code (no one can find you!)

        data['chat_hash'] = chat_hash  # We are storing hash, not id or title
        data['chat_type'] = chat_type
        data['date_time'] = date_time  # Time of message

        response = db.put(data)
        pprint.pprint(response)
        return response

    else:  # Section used for verifying duplicate inline results, you can ignore
        chat_type = update.inline_query.chat_type
        data['chat_type'] = chat_type

        if "user_hash" in data:
            if user_hash in records:
                if time.time() - records[user_hash]['time'] < 10:  # If older inline query was made just ago
                    data['key'] = records[user_hash]['key']  # use old key to update values, not insert new

            response = db.put(data)
            pprint.pprint(response)
            records[user_hash] = {'time': time.time(), 'key': response['key']}  # Update record with new time
            return response

    # We have collected chat_hash and user_hash just to know that a person is different from other person
    # We have no way to identify you (period)
    #
