import sys
import os
import main

if __name__ == "__main__":

    arguments = sys.argv[1:]
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    DETA_TOKEN = os.environ.get('DETA_TOKEN')

    if "webhook" in arguments:
        WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
        main.set_up(BOT_TOKEN, DETA_TOKEN)

        PORT = int(os.environ.get('PORT', 8443))
        main.updater.start_webhook(listen="0.0.0.0",
                                   port=int(PORT),
                                   url_path=BOT_TOKEN,
                                   webhook_url=WEBHOOK_URL + BOT_TOKEN)

        main.updater.idle()

    else:  # For personal local testing

        main.set_up(BOT_TOKEN, DETA_TOKEN)

        main.updater.start_polling()
        main.updater.idle()
