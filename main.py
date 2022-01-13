from html.parser import HTMLParser
from io import StringIO
import urllib.request
import urllib.parse
import re
import os
import logging
from telegram import Update, MessageEntity
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, InlineQueryHandler
from indic_transliteration import sanscript, detect


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_URL = "http://kosha.sanskrit.today/word/"
SUPPORTED_DICTIONARIES = ['Spoken Sanskrit', 'Shabda Sagara', 'Hindi']


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


class Meaning:

    def fetch(self, word, preference=None):
        # TODO: Feature to display meaning from preferred dictionary
        print("**************************************************************************")
        print("Searched for:", word)

        word = str.lower(word)
        transformed_word = urllib.parse.quote(word)  # remove html tags present, if any
        if detect.detect(word) == sanscript.DEVANAGARI:
            # replaces anusvara with corresponding pancham varna
            transformed_word = sanscript.SCHEMES[sanscript.DEVANAGARI].fix_lazy_anusvaara(transformed_word, omit_sam=True, omit_yrl=True)
        url = RAW_URL + transformed_word

        headers = {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"}
        request = urllib.request.Request(url, headers=headers)
        instance = urllib.request.urlopen(request, timeout=3)
        result = instance.read().decode('utf-8')
        with open(r"result.html", 'w') as file:
            file.write(urllib.parse.unquote(str(result)))

        extracted_parts = re.findall(r'<h5>.*?</h5>.*?div class="card-body".*?</div>', str(result), re.DOTALL)
        available_dict = {}

        for part in extracted_parts:
            service = re.search(r'<h5>(.*?)</h5>', part).group(1)

            if service not in SUPPORTED_DICTIONARIES:
                continue

            if service in available_dict.keys():
                continue

            if service == "Spoken Sanskrit":
                available_dict[service] = self.spoken_sanskrit(word, part)

            elif service == "Shabda Sagara":
                available_dict[service] = self.shabda_sagara(word, part)

            elif service == "Hindi":
                available_dict[service] = self.hindi_dict(word, part)

        else:

            if not available_dict:
                return "कोई बेहतर अर्थ नहीं पाया।"
            else:
                if preference is not None and preference in available_dict.keys():
                    return available_dict[preference]
                else:
                    for dict in SUPPORTED_DICTIONARIES:
                        if dict in available_dict.keys():
                            return available_dict[dict]

    def spoken_sanskrit(self, word, part):
        answer_inside = re.search(r'<table>.*?<tr>(.*?)</tr>.*?</table>', part)
        answer_row = re.sub(r'<span.*?>|</span>', '', str(answer_inside.group(1)))
        answer_row = re.findall(r'<td>(.*?)</td>', answer_row)
        answer_list = ["* " + HTMLStripper().strip(k) + "\n" for k in answer_row if (not None) and (not k.isspace())]
        answer_list.append("\n<i><u>From Spoken Sanskrit</u></i>")

        answer_string = ''.join(answer_list)
        return answer_string

    def shabda_sagara(self, word, part):
        answer_inside = re.search(r'<p class="card-text">(.*?)</p>', part)
        answer_list = ["* " + k.strip() for k in str(answer_inside.group(1)).split("<BR>") if not k.startswith("E.")]
        if len(answer_list) > 5:
            answer_list = answer_list[:6]
        answer_list.append("\n<i><u>From Shabda Sagara</u></i>")
        answer_string = '\n'.join(answer_list)
        return answer_string

    def hindi_dict(self, word, part):
        answer_inside = re.search(r'<p class="card-text">(.*?)</p>', part)
        answer = str(answer_inside.group(1))
        answer_table = [f'* {word}\n', f'* {HTMLStripper().strip(answer)}\n']
        answer_table.append("\n<i><u>From Hindi Dictionary</u></i>")

        print(answer_table)
        answer_string = ''.join(answer_table)
        return answer_string


meaning = Meaning()


def on_start(update: Update, context: CallbackContext) -> None:
    help_message = f"""
<i>नमस्कार {update.effective_user.username}!</i>
संस्कृत शब्द का मतलब जानने के लिए आप केवल अपने शब्द को लिख कर मुझे भेज सकते हैं।

शब्दकोष को उपलब्धि और उपयोगिता के आधार पर चुना जाता है। अगर आपको अपने पसंदीदा शब्दकोष से अर्थ जानना है तो आप <code>\"/&lt;lang_id&gt;&lt;शब्द&gt;\"</code> का इस्तेमाल कर सकते हैं।
तत्काल में आप निम्नलिखित शब्दकोष में से चुन सकते हैं:
1. sh - Shabda Sagara
2. sp - Spoken Sanskrit
3. hi - hindi
उदाहरण : \"<code>/sh कृति</code>\"

आप इसे सीधे किसी भी समूह या निजी लिखचित में भी इस्तेमाल कर सकते हैं। इसके लिए आपको मुझे बुला कर अपना शब्द देना होगा
जैसे \"<code>@sanskritkoshbot कृति</code>\"
इतना लिखने मात्र पर आपके शब्द का अर्थ कुछ पल के अंदर सन्देश के ऊपर दिखा दिया जायेगा।

इस संदेश को दोबारा पढ़ने के लिए आप /start या /help का इस्तेमाल कर सकते हैं।
"""
    update.message.reply_html(help_message)


def get_meaning(update: Update, context: CallbackContext) -> None:

    search_term = update.message.text
    preference = None

    if update.message.entities and update.message.entities[0].type == MessageEntity.BOT_COMMAND:
        command = update.message.text[1: update.message.entities[0].length].split('@')[0]
        search_term = " ".join(context.args)
        if command.startswith("sh"):
            preference = "Shabda Sagara"
        elif command.startswith("sp"):
            preference = "Spoken Sanskrit"
        elif command.startswith("hi"):
            preference = "Hindi"

    update.message.reply_html(meaning.fetch(search_term, preference))


def get_meaning_inline(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    if not query:
        return
    results = list()
    _meaning = meaning.fetch(query)
    results.append(InlineQueryResultArticle(id=query,
                                            title="Click to send",
                                            description=_meaning.splitlines()[-1],
                                            input_message_content=InputTextMessageContent(_meaning, parse_mode="HTML")))
    context.bot.answer_inline_query(update.inline_query.id, results)


def unknown(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("माफ़ कीजिये ! आपकी मांग मुझे समझ नहीं आई।")


def set_up(BOT_TOKEN):
    global updater, dispatcher
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler(['start', 'help'], on_start))
    dispatcher.add_handler(CommandHandler(['sh', 'sp', 'hi'], get_meaning))
    dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), get_meaning))
    dispatcher.add_handler(MessageHandler(Filters.command, unknown))
    dispatcher.add_handler(InlineQueryHandler(get_meaning_inline))
