import sys
import os
import main

if __name__ == "__main__":

    arguments = sys.argv[1:]

    if "heroku" in arguments:
        BOT_TOKEN = os.environ.get('BOT_TOKEN')
        main.set_up(BOT_TOKEN)

        PORT = int(os.environ.get('PORT', 8443))
        main.updater.start_webhook(listen="0.0.0.0",
                                   port=int(PORT),
                                   url_path=BOT_TOKEN,
                                   webhook_url='https://test-sanskritkoshbot.herokuapp.com/' + BOT_TOKEN)

        main.updater.idle()

    else:
        token_file = open(r"TOKEN.txt", "r")
        BOT_TOKEN = token_file.readline()
        main.set_up(BOT_TOKEN)

        main.updater.start_polling()
        main.updater.idle()
