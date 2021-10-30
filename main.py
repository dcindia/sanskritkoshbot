from html.parser import HTMLParser
from io import StringIO
import urllib.request
import urllib.parse
import re
import logging
from telegram import Update
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, InlineQueryHandler


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_URL = "http://kosha.sanskrit.today/word/"


class HTMLStripper(HTMLParser):
    def __init__(self, *, convert_charrefs: bool = ...) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, data: str) -> None:
        self.text.write(data)
        return super().handle_data(data)

    def strip(self, html_text):
        html_text = str.strip(html_text)
        self.feed(html_text)
        return self.text.getvalue()


def meaning(word):
    transformed_word = urllib.parse.quote(word)
    url = RAW_URL + transformed_word

    print("**************************************************************************")
    print(url)
    headers = {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"}
    request = urllib.request.Request(url, headers=headers)
    instance = urllib.request.urlopen(request, timeout=3)
    result = instance.read().decode('utf-8')
    file = open(r"result.html", 'w')
    file.write(urllib.parse.unquote(str(result)))
    extracted_parts = re.findall(r'<h5>.*?</h5>.*?div class="card-body".*?</div>', str(result), re.DOTALL)

    for part in extracted_parts:
        service = re.search(r'<h5>(.*?)</h5>', part)
        print(service.group(1))

        if service.group(1) == "Spoken Sanskrit":
            answer_inside = re.search(r'<table>.*?<tr>(.*?)</tr>.*?</table>', part)
            answer_row = re.sub(r'<span.*?>|</span>', '', str(answer_inside.group(1)))
            answer_row = re.findall(r'<td>(.*?)</td>', answer_row)
            answer_list = ["* " + HTMLStripper().strip(k) + "\n" for k in answer_row if k != '']

            answer_string = ''.join(answer_list)
            return answer_string

        elif service.group(1) == "Hindi":
            answer_inside = re.search(r'<p class="card-text">(.*?)</p>', part)
            answer = str(answer_inside.group(1))
            answer_table = f'* {word}\n* {HTMLStripper().strip(answer)}'
            print(answer_table)
            return answer_table

    else:
        return "No better meaning found."


token_file = open(r'TOKEN.txt', "r")
BOT_TOKEN = token_file.readline()

updater = Updater(BOT_TOKEN)
dispatcher = updater.dispatcher


def on_start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f'Hello {update.effective_user.username}.\nJust send me the word in sanskrit of which meaning you want to know.')


def get_meaning(update: Update, context: CallbackContext) -> None:
    update.message.reply_html(meaning(update.message.text))


def get_meaning_inline(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    if not query:
        return
    results = list()
    _meaning = meaning(query)
    results.append(InlineQueryResultArticle(id=query,
                                            title="Click to send",
                                            description=_meaning.splitlines()[-1],
                                            input_message_content=InputTextMessageContent(_meaning, parse_mode="HTML")))
    context.bot.answer_inline_query(update.inline_query.id, results)


def unknown(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Sorry, I didn't understand that command.")


dispatcher.add_handler(CommandHandler('start', on_start))
dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), get_meaning))
dispatcher.add_handler(MessageHandler(Filters.command, unknown))
dispatcher.add_handler(InlineQueryHandler(get_meaning_inline))

updater.start_polling()
updater.idle()
