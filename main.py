from crypt import methods
import os
import sys
import logging
from turtle import update
import urllib.parse
from flask import Flask, request
from telegram import InputMessageContent, Update, MessageEntity, Bot
from telegram import InlineQueryResultArticle, InputTextMessageContent
import telegram
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, InlineQueryHandler
from indic_transliteration import sanscript, detect
from htmldom import HtmlDom
import kosha

WebApp = Flask(__name__)


@WebApp.route('/')
def index_page():
    print('index')
    return "Hello World !"


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_URL = "http://kosha.sanskrit.today/word/"

CONFIGURATION = [['sp', 'sh', 'mw', 'hindi', 'apte', 'wilson', 'yates'],  # short names
                 ['Spoken Sanskrit', 'Shabda Sagara', 'Monier Williams Cologne', 'Hindi', 'Apte', 'Wilson', 'Yates'],  # names
                 [kosha.spoken_sanskrit, kosha.shabda_sagara, kosha.monier_wiliams, kosha.hindi_dict, kosha.apte, kosha.wilson, kosha.yates]]  # funtions


def config(operation, value=None):

    def dicts(*args):
        return CONFIGURATION[1]

    def name(short_name):
        index = CONFIGURATION[0].index(short_name)
        return CONFIGURATION[1][index]

    def function(name):
        index = CONFIGURATION[1].index(name)
        return CONFIGURATION[2][index]

    mapping = {"dicts": dicts, "name": name, "function": function}

    return mapping[operation](value)


def fetch_meaning(word, preference=None):
    print("**************************************************************************")
    print("Searched for:", word)

    word = str.lower(word)
    if detect.detect(word) == sanscript.DEVANAGARI:
        # replaces anusvara with corresponding pancham varna
        word = sanscript.SCHEMES[sanscript.DEVANAGARI].fix_lazy_anusvaara(word, omit_sam=True, omit_yrl=True)
    transformed_word = urllib.parse.quote(word)  # remove html tags present, if any
    url = RAW_URL + transformed_word

    dom = HtmlDom(url).createDom()

    extracted_parts = dom.find("section#word div.card-header")
    available_dict = {}

    for part in extracted_parts:
        service = part.find("h5").text()

        if service in available_dict.keys():
            continue
        elif service not in config("dicts"):
            continue
        else:
            available_dict[service] = config("function", service)(word, part)

    else:

        if not available_dict:
            return None, "कोई बेहतर अर्थ नहीं पाया।"
        else:
            if preference == "All":   # for inline mode
                return available_dict
            if preference is not None and preference in available_dict.keys():  # if preference set and available also
                return available_dict[preference]
            else:  # if preference not found or not set at all
                for dict in config("dicts"):
                    if dict in available_dict.keys():
                        return available_dict[dict]


def on_start(update: Update, context: CallbackContext) -> None:
    help_message = f"""
<i>नमस्कार {update.effective_user.first_name} 🙏</i>
संस्कृत शब्द का मतलब जानने के लिए आप केवल अपना शब्द लिखकर मुझे भेज सकते हैं या <code>\"/arth &lt;शब्द&gt;\"</code> का उपयोग भी कर सकते हैं।

शब्दकोष को उपलब्धि और उपयोगिता के आधार पर चुना जाता है। अगर आपको अपने पसंदीदा शब्दकोष से अर्थ जानना है तो आप <code>\"/&lt;lang_id&gt;&lt;शब्द&gt;\"</code> का इस्तेमाल कर सकते हैं।
उदाहरण : \"<code>/sh कृति</code>\"
सभी शब्दकोशों की सूचि के लिए /kosha का प्रयोग करें।

आप इसे सीधे किसी भी समूह या निजी संदेश में भी इस्तेमाल कर सकते हैं। इसके लिए आपको टाइपिंग बॉक्स में मेरा हैंडल लिखकर अपना शब्द लिखना होगा।
जैसे \"<code>@sanskritkoshbot कृति</code>\"
इतना लिखने मात्र पर आपके शब्द का अर्थ कुछ क्षणों के अंदर सन्देश के ऊपर दिखा दिया जायेगा।

सहायता संदेश को पढ़ने के लिए आप /help का इस्तेमाल कर सकते हैं।
"""
    update.message.reply_html(help_message)


def kosha_list(update: Update, context: CallbackContext) -> None:
    message = "<b>शब्दकोशों की सूचि:</b>\n\n"
    sets = zip(CONFIGURATION[0], CONFIGURATION[1])
    for count, set in enumerate(sets, start=1):
        message += f"{count}. {set[0]} - {set[1]}\n"

    update.message.reply_html(message)


def get_meaning(update: Update, context: CallbackContext) -> None:

    search_term = update.message.text
    preference = None

    if context.args == []:
        update.message.reply_text("कृपया, मुझे कोई शब्द प्रदान करें।")
        return

    if update.message.entities and update.message.entities[0].type == MessageEntity.BOT_COMMAND:
        command = update.message.text[1: update.message.entities[0].length].split('@')[0]
        search_term = " ".join(context.args)
        if not command.startswith("arth"):
            preference = config("name", command)

    answer, source = fetch_meaning(search_term, preference)
    if answer is None:
        answer_html = source
    else:
        answer_html = ''.join(answer) + "\n" + f"<i><u>📖 {source}</u></i>"
    update.message.reply_html(answer_html)


def get_meaning_inline(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    if not query:
        return
    results = list()
    _answer = fetch_meaning(query, preference="All")

    if str(type(_answer)) == "<class 'dict'>":  # meaning.fetch() returns dict if preference set to "All" and atleast one meaning found
        for service in _answer.keys():
            id = service
            title = service
            description = "".join(_answer[service][0][1:3])  # for particular dict, first part is anwer_list
            source = _answer[service][1]
            message = InputTextMessageContent(''.join(_answer[service][0]) + "\n" + f"<i><u>📖 {source}</u></i>", parse_mode="HTML")
            results.append(InlineQueryResultArticle(id=id, title=title, description=description, input_message_content=message))

    else:  # meaning.fetch() returns tuple if there is an error
        results.append(InlineQueryResultArticle(id="none", title=_answer[1], input_message_content=InputTextMessageContent(_answer[1])))

    context.bot.answer_inline_query(update.inline_query.id, results)


def unknown(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("माफ़ कीजिये ! आपकी मांग मुझे समझ नहीं आई।")


def set_up(BOT_TOKEN):
    global updater, dispatcher
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler(['start', 'help'], on_start))
    dispatcher.add_handler(CommandHandler(['kosha'], kosha_list))
    dispatcher.add_handler(CommandHandler(['arth', 'sh', 'sp', 'hi', 'apte', 'wilson', 'mw', 'yates'], get_meaning))
    dispatcher.add_handler(MessageHandler(Filters.text & ~(Filters.via_bot(allow_empty=True) | Filters.command), get_meaning))
    dispatcher.add_handler(MessageHandler(Filters.command & ~Filters.chat_type.groups, unknown))
    dispatcher.add_handler(InlineQueryHandler(get_meaning_inline))


if __name__ == "__main__":

    arguments = sys.argv[1:]
    global BOT_TOKEN

    if "heroku" in arguments:
        # webhook method for running on servers
        BOT_TOKEN = os.environ.get('BOT_TOKEN')
        set_up(BOT_TOKEN)

        updater.bot.set_webhook('https://test-sanskritkoshbot.herokuapp.com/telegram/' + BOT_TOKEN)

    else:
        # polling method for testing on local machine
        token_file = open(r"TOKEN.txt", "r")
        BOT_TOKEN = token_file.readline()
        set_up(BOT_TOKEN)
        updater.bot.delete_webhook()  # remove webhook for local testing
        updater.start_polling()

    @WebApp.route('/telegram/', methods=['GET', 'POST'])
    def response():
        print("got response !!")
        req = request.get_json()
        update = telegram.Update.de_json(req, updater.bot)
        updater.update_queue.put(update)

    PORT = int(os.environ.get('PORT', 5000))
    WebApp.run(host='0.0.0.0', port=PORT, threaded=True)
