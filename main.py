import logging
import re
import urllib.parse
import urllib.request
from telegram import Update, MessageEntity
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, InlineQueryHandler
from indic_transliteration import sanscript, detect
from lxml import html
import scraper as sc

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_URL = "http://kosha.sanskrit.today/word/"

CONFIGURATION = {'Spoken Sanskrit': {'name': "Spoken Sanskrit", 'short_name': "sp", 'function': sc.spoken_sanskrit},
                 'Shabda Sagara': {'name': "Shabda Sagara", 'short_name': "sh", 'function': sc.shabda_sagara},
                 'Monier Williams Cologne': {'name': "Monier Williams", 'short_name': "mw", 'function': sc.monier_wiliams},
                 'Monier Williams': {'name': None, 'short_name': None, 'function': sc.monier_williams2},  # hidden for inline mode
                 'Hindi': {'name': "Hindi", 'short_name': "hi", 'function': sc.hindi_dict},
                 'Apte': {'name': "Apte", 'short_name': "apte", 'function': sc.apte},
                 'Wilson': {'name': "Wilson", 'short_name': "wilson", 'function': sc.wilson},
                 'Yates': {'name': "Yates", 'short_name': "yates", 'function': sc.yates}
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


def fetch_meaning(word, preference=None):
    print("**************************************************************************")
    print("Searched for:", word)

    word = str.lower(word)
    if detect.detect(word) == sanscript.DEVANAGARI:
        # replaces anusvara with corresponding pancham varna
        word = sanscript.SCHEMES[sanscript.DEVANAGARI].fix_lazy_anusvaara(word, omit_sam=True, omit_yrl=True)
    transformed_word = urllib.parse.quote(word)  # remove html tags present, if any
    url = RAW_URL + transformed_word

    headers = {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"}
    request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request, timeout=3)
    data = response.read().decode('UTF-8')
    tree = html.fromstring(data)

    extracted_parts = tree.findall(".//section[@id='word']//div[@class='card-header']")
    available_dict = {}

    for part in extracted_parts:
        service = part.find("h5")
        if service is not None:  # checks if extracted part really has <h5> tag
            service = service.text
        else:
            continue

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
    sets = [(CONFIGURATION[dict]['short_name'], CONFIGURATION[dict]['name']) for dict in CONFIGURATION if CONFIGURATION[dict]['name'] is not None]
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
