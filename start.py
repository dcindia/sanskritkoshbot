import sys
import os
import main
from flask import Flask


webapp = Flask(__name__)


@webapp.route('/')
def index_page():
    return "Hello World!"


def setup_flask():
    port = int(os.environ.get('PORT', 5000))
    webapp.run(host='0.0.0.0', port=port, threaded=True)

if __name__ == "__main__":

    arguments = sys.argv[1:]

    if "heroku" in arguments:
        BOT_TOKEN = os.environ.get('BOT_TOKEN')
        main.set_up(BOT_TOKEN)

        PORT = int(os.environ.get('PORT', 8443))
        main.updater.start_webhook(listen="0.0.0.0",
                                   port=int(PORT),
                                   url_path="telegram/" + BOT_TOKEN,
                                   webhook_url='https://test-sanskritkoshbot.herokuapp.com/' + BOT_TOKEN)
        setup_flask()

        main.updater.idle()

    else:
        token_file = open(r"TOKEN.txt", "r")
        BOT_TOKEN = token_file.readline()
        main.set_up(BOT_TOKEN)

        main.updater.start_polling()
        setup_flask()
        main.updater.idle()
