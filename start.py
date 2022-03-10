"""Sets up telegram bot and Flask app"""
import os
import sys
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, Updater
from main import set_handlers

if __name__ == "__main__":

    arguments = sys.argv[1:]

    if "heroku" in arguments:
        # webhook method for running on servers
        BOT_TOKEN = os.environ.get('BOT_TOKEN')

        from queue import Queue
        from threading import Thread

        bot = Bot(BOT_TOKEN)
        update_queue = Queue()
        dispatcher = Dispatcher(bot, update_queue)
        set_handlers(dispatcher)
        Thread(target=dispatcher.start, name='dispatcher').start()

        bot.set_webhook('https://test-sanskritkoshbot.herokuapp.com/' + '/telegram/' + BOT_TOKEN)

    else:
        # polling method for testing on local machine
        BOT_TOKEN = open(r"TOKEN.txt", "r").readline()

        updater = Updater(BOT_TOKEN)
        bot = updater.bot
        dispatcher = updater.dispatcher
        set_handlers(dispatcher)

        updater.bot.delete_webhook()  # remove webhook for local testing
        updater.start_polling()

    WebApp = Flask(__name__)

    @WebApp.route('/')
    def index_page():
        print('index')
        return r"<a href=https://t.me/sanskritkoshbot>Click here to use me on Telegram !</a>"

    @WebApp.route('/telegram/' + BOT_TOKEN, methods=['GET', 'POST'])
    def response():
        """Receive webhook requests from telegram
        """
        req = request.get_json()
        update = Update.de_json(req, bot)
        dispatcher.update_queue.put(update)
        return "Processed."

    # Run Flask App
    PORT = int(os.environ.get('PORT', 8443))
    WebApp.run(host='0.0.0.0', port=PORT, threaded=True)
