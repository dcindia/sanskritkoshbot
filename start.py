import sys
import os
import main

if __name__ == "__main__":

    arguments = sys.argv[1:]

    if "heroku" in arguments:
        BOT_TOKEN = os.environ.get('BOT_TOKEN')
        DETA_TOKEN = os.environ.get('DETA_TOKEN')
        main.set_up(BOT_TOKEN, DETA_TOKEN)

        PORT = int(os.environ.get('PORT', 8443))
        main.updater.start_webhook(listen="0.0.0.0",
                                   port=int(PORT),
                                   url_path=BOT_TOKEN,
                                   webhook_url='https://web-production-1dc6.up.railway.app/' + BOT_TOKEN)

        main.updater.idle()

    else:  # For personal local testing
        token_file = open(r"TOKEN.txt", "r")  # file(hidden) containing secret tokens
        BOT_TOKEN = token_file.readline().strip()  # on first line
        DETA_TOKEN = token_file.readline().strip()  # on second line
        main.set_up(BOT_TOKEN, DETA_TOKEN)

        main.updater.start_polling()
        main.updater.idle()
