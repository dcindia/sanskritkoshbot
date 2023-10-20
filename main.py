import logging
import re
import urllib.parse
import urllib.request
import json
from telegram import Update, MessageEntity, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, InlineQueryHandler, CallbackQueryHandler
from indic_transliteration import sanscript, detect
from lxml import html
import scraper as sc
import analytics

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_URL = "http://kosha.sanskrit.today"
NOT_FOUND_MESSAGE = "कोई बेहतर अर्थ नहीं पाया।"

CONFIGURATION = {'spoken-skt': {'name': "Spoken Sanskrit", 'short_name': "sp", 'function': sc.spoken_sanskrit},
                 'shabda-sagara': {'name': "Shabda Sagara", 'short_name': "sh", 'function': sc.shabda_sagara},
                 'mwes': {'name': "Monier Williams", 'short_name': "mw", 'function': sc.monier_wiliams},
                 'Monier Williamsb': {'name': None, 'short_name': None, 'function': sc.monier_williams2},  # hidden for inline mode
                 'hindi': {'name': "Hindi", 'short_name': "hi", 'function': sc.hindi_dict},
                 'apte-sa': {'name': "Apte", 'short_name': "apte", 'function': sc.apte},
                 'wilson': {'name': "Wilson", 'short_name': "wilson", 'function': sc.wilson},
                 'yates': {'name': "Yates", 'short_name': "yates", 'function': sc.yates}
                 }


def config(operation, value=None):

    def dicts(*args):
        return CONFIGURATION.keys()

    def name(short_name):
        for dict in CONFIGURATION:
            if CONFIGURATION[dict]['short_name'] == short_name:
                return dict

    def function(name):
        for dict in CONFIGURATION:
            if dict == name:
                return CONFIGURATION[dict]['function']

    mapping = {"dicts": dicts, "name": name, "function": function}

    return mapping[operation](value)


def fetch_meaning(word) -> dict:

    word = str.lower(word)
    if detect.detect(word) == sanscript.DEVANAGARI:
        # replaces anusvara with corresponding pancham varna
        word = sanscript.SCHEMES[sanscript.DEVANAGARI].fix_lazy_anusvaara(word, omit_sam=True, omit_yrl=True)
    transformed_word = urllib.parse.quote(word)  # remove html tags present, if any

    # fetch api response in json format
    url = RAW_URL + "/api/search?q=" + transformed_word
    headers = {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"}
    request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request, timeout=3)
    pre_data = json.loads(response.read().decode('UTF-8'))

    # check if searched word is available
    for item in pre_data:
        if item["string"] == word:
            data_url = urllib.parse.quote(RAW_URL + item["url"], safe="/:?=")
            break
    else:
        return {}  # matching word not found

    # fetch meaning data, after matching word found
    request = urllib.request.Request(data_url, headers=headers)
    response = urllib.request.urlopen(request, timeout=3)
    data = response.read()

    tree = html.fromstring(data)
    content = json.loads(tree.find(".//script[@id='__NEXT_DATA__']").text)
    result_content = content['props']['pageProps']['results']

    available_dict = {}

    for part in result_content:
        if part in config("dicts"):
            if part in ["spoken-skt", "shabda-sagara", "wilson", "yates", "hindi", "mwes", "apte-sa"]:
                available_dict[part] = config("function", part)(word, result_content[part][0]['text'])
            else:
                available_dict[part] = result_content[part][0]['text']

    return available_dict


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
    sets = [(CONFIGURATION[dict]['short_name'], CONFIGURATION[dict]['name']) for dict in CONFIGURATION if CONFIGURATION[dict]['name'] is not None]
    for count, set in enumerate(sets, start=1):
        message += f"{count}. {set[0]} - {set[1]}\n"

    update.message.reply_html(message)


def get_meaning(update: Update, context: CallbackContext) -> None:

    if update.callback_query:
        data = update.callback_query.data
        command = context.match.group(1)
        preference = config("name", command)
        search_term = context.match.group(2)
    else:
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

    meanings = fetch_meaning(search_term)
    if not meanings:
        update.message.reply_html(NOT_FOUND_MESSAGE)
        analytics.track(update, search_term, preference)
    else:
        available_sources = list(meanings.keys())

        if preference is not None and preference in available_sources:  # if preference set and available also
            answer = meanings[preference]
            source = preference
        else:  # if preference not found or not set at all
            for dict in config("dicts"):
                if dict in available_sources:
                    answer = meanings[dict]
                    source = dict
                    break

        answer_html = '\n'.join(answer) + "\n\n" + f"<i><u>📖 {CONFIGURATION[source]['name']}</u></i>"
        analytics.track(update, search_term, preference, available_sources, source)

        available_sources.remove(source)  # source removed from here

        keymap = []
        while available_sources:
            row = [InlineKeyboardButton(text=CONFIGURATION[x_source]['name'],
                                        callback_data="/" + CONFIGURATION[x_source]['short_name'] + " " + search_term)
                   for x_source in available_sources[:2]]
            keymap.append(row)
            available_sources = available_sources[2:]  # sources continuosly getting removed as added to keymap
    if update.callback_query:
        update.callback_query.message.edit_text(answer_html, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keymap))
    else:
        update.message.reply_html(answer_html, reply_markup=InlineKeyboardMarkup(keymap))


def get_meaning_inline(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    if not query:
        return
    results = list()
    meanings = fetch_meaning(query)
    available_sources = meanings.keys()
    analytics.track(update, query, available_sources=available_sources, inline=True)

    if meanings:
        for service in available_sources:
            id = service
            title = CONFIGURATION[service]['name']
            description = "".join(meanings[service][1:3])  # for particular dict, first part is answer_list
            source = CONFIGURATION[service]['name']
            message = InputTextMessageContent('\n'.join(meanings[service]) + "\n\n" + f"<i><u>📖 {source}</u></i>", parse_mode="HTML")
            results.append(InlineQueryResultArticle(id=id, title=title, description=description, input_message_content=message))

    else:
        results.append(InlineQueryResultArticle(id="none", title=NOT_FOUND_MESSAGE, input_message_content=InputTextMessageContent(NOT_FOUND_MESSAGE)))

    context.bot.answer_inline_query(update.inline_query.id, results)


def unknown(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("माफ़ कीजिये ! आपकी मांग मुझे समझ नहीं आई।")


def set_up(BOT_TOKEN, DETA_TOKEN):
    global updater, dispatcher
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CallbackQueryHandler(get_meaning, pattern=r"^/(\w+) (\S+)"))
    dispatcher.add_handler(CommandHandler(['start', 'help'], on_start))
    dispatcher.add_handler(CommandHandler(['kosha'], kosha_list))
    dispatcher.add_handler(CommandHandler(['arth', 'sh', 'sp', 'hi', 'apte', 'wilson', 'mw', 'yates'], get_meaning))
    dispatcher.add_handler(MessageHandler(Filters.text & ~(Filters.via_bot(allow_empty=True) | Filters.command), get_meaning))
    dispatcher.add_handler(MessageHandler(Filters.command & ~Filters.chat_type.groups, unknown))
    dispatcher.add_handler(InlineQueryHandler(get_meaning_inline))

    analytics.initialize(DETA_TOKEN)
