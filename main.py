from html.parser import HTMLParser
from io import StringIO
import urllib.request
import urllib.parse
import re
import os
import logging
from telegram import InputMessageContent, Update, MessageEntity
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
                return None, "कोई बेहतर अर्थ नहीं पाया।"
            else:
                if preference == "All":   # for inline mode
                    return available_dict
                if preference is not None and preference in available_dict.keys():  # if preference set and available also
                    return available_dict[preference]
                else:  # if preference not found or not set at all
                    for dict in SUPPORTED_DICTIONARIES:
                        if dict in available_dict.keys():
                            return available_dict[dict]

    def spoken_sanskrit(self, word, part):
        answer_inside = re.search(r'<table>.*?<tr>(.*?)</tr>.*?</table>', part)
        answer_row = re.sub(r'<span.*?>|</span>', '', str(answer_inside.group(1)))
        answer_row = re.findall(r'<td>(.*?)</td>', answer_row)
        answer_list = ["* " + HTMLStripper().strip(k) + "\n" for k in answer_row if (k != '') and (not k.isspace())]
        # answer_list.append("\n<i><u>From Spoken Sanskrit</u></i>")
        # answer_string = ''.join(answer_list)
        return answer_list, "Spoken Sanskrit"

    def shabda_sagara(self, word, part):
        answer_inside = re.search(r'<p class="card-text">(.*?)</p>', part)
        answer_list = ["* " + k.strip() + '\n' for k in str(answer_inside.group(1)).split("<BR>") if not k.startswith("E.")]
        if len(answer_list) > 5:
            answer_list = answer_list[:6]
        # answer_list.append("\n<i><u>From Shabda Sagara</u></i>")
        # answer_string = ''.join(answer_list)
        return answer_list, "Shabda Sagara"

    def hindi_dict(self, word, part):
        answer_inside = re.search(r'<p class="card-text">(.*?)</p>', part)
        answer = str(answer_inside.group(1))
        answer_list = [f'* {word}\n', f'* {HTMLStripper().strip(answer)}\n']
        # answer_table.append("\n<i><u>From Hindi Dictionary</u></i>")
        # answer_string = ''.join(answer_list)
        return answer_list, "Hindi Dictionary"


meaning = Meaning()


def on_start(update: Update, context: CallbackContext) -> None:
    help_message = f"""
<i>नमस्कार {update.effective_user.username}!</i>
संस्कृत शब्द का मतलब जानने के लिए आप केवल अपना शब्द लिखकर मुझे भेज सकते हैं।

शब्दकोष को उपलब्धि और उपयोगिता के आधार पर चुना जाता है। अगर आपको अपने पसंदीदा शब्दकोष से अर्थ जानना है तो आप <code>\"/&lt;lang_id&gt;&lt;शब्द&gt;\"</code> का इस्तेमाल कर सकते हैं।
तत्काल में आप निम्नलिखित शब्दकोशों में से चुन सकते हैं:
1. sh - Shabda Sagara
2. sp - Spoken Sanskrit
3. hi - hindi
उदाहरण : \"<code>/sh कृति</code>\"

आप इसे सीधे किसी भी समूह या निजी संदेश में भी इस्तेमाल कर सकते हैं। इसके लिए आपको टाइपिंग बॉक्स में मेरा हैंडल लिखकर अपना शब्द लिखना होगा।
जैसे \"<code>@sanskritkoshbot कृति</code>\"
इतना लिखने मात्र पर आपके शब्द का अर्थ कुछ क्षणों के अंदर सन्देश के ऊपर दिखा दिया जायेगा।

इस संदेश को दोबारा पढ़ने के लिए आप /start या /help का इस्तेमाल कर सकते हैं।
"""
    update.message.reply_html(help_message)


def get_meaning(update: Update, context: CallbackContext) -> None:

    search_term = update.message.text
    preference = None

    print(context)
    if context.args == []:
        update.message.reply_text("कृपया, मुझे कोई शब्द प्रदान करें।")
        return

    if update.message.entities and update.message.entities[0].type == MessageEntity.BOT_COMMAND:
        command = update.message.text[1: update.message.entities[0].length].split('@')[0]
        search_term = " ".join(context.args)
        if command.startswith("sh"):
            preference = "Shabda Sagara"
        elif command.startswith("sp"):
            preference = "Spoken Sanskrit"
        elif command.startswith("hi"):
            preference = "Hindi"

    answer, source = meaning.fetch(search_term, preference)
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
    _answer = meaning.fetch(query, preference="All")

    if str(type(_answer)) == "<class 'dict'>":  # meaning.fetch() returns dict if preference set to "All" and atleast one meaning found
        for service in _answer.keys():
            id = service
            title = service
            # BUG: For spoken sanskrit, searching english word shows same word as meaning, but actual meaning is at another line
            description = _answer[service][0][-1]  # for particular dict, first part is anwer_list, and last line of that is description
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
    dispatcher.add_handler(CommandHandler(['arth', 'sh', 'sp', 'hi'], get_meaning))
    dispatcher.add_handler(MessageHandler(Filters.text & ~(Filters.via_bot(allow_empty=True) | Filters.command), get_meaning))
    dispatcher.add_handler(MessageHandler(Filters.command & ~Filters.chat_type.groups, unknown))
    dispatcher.add_handler(InlineQueryHandler(get_meaning_inline))
