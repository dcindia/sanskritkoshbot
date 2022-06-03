import re
from io import StringIO
from html.parser import HTMLParser
from lxml import etree


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
        self.feed(html_text)
        return self.text.getvalue().strip()


def spoken_sanskrit(word, part):
    siblings = part.find('../*[@class="card-body"]//table//tr').findall("td")
    answer_row = [s.text_content() for s in siblings]
    answer_list = ["* " + HTMLStripper().strip(k) + "\n" for k in answer_row if (k != '') and (not k.isspace())]
    # answer_list.append("\n<i><u>From Spoken Sanskrit</u></i>")
    # answer_string = ''.join(answer_list)
    return answer_list, "Spoken Sanskrit"


def shabda_sagara(word, part):

    sibling = etree.tostring(part.find('../*[@class="card-body"]//p[@class="card-text"]'), encoding='unicode')
    answer_inside = re.search(r'<p class="card-text">(.*?)</p>', str(sibling), re.DOTALL)
    answer_list = ["* " + HTMLStripper().strip(k) + '\n' for k in answer_inside.group(1).split('<br/>')]
    if len(answer_list) > 5:
        answer_list = answer_list[:6]
    # answer_list.append("\n<i><u>From Shabda Sagara</u></i>")
    # answer_string = ''.join(answer_list)
    return answer_list, "Shabda Sagara"


def hindi_dict(word, part):
    sibling = part.find('../*[@class="card-body"]//p[@class="card-text"]')
    answer_list = [f'* {word}\n', f'* {sibling.text}\n']
    # answer_table.append("\n<i><u>From Hindi Dictionary</u></i>")
    # answer_string = ''.join(answer_list)
    return answer_list, "Hindi Dictionary"


def apte(word, part):
    siblings = part.findall('../*[@class="card-body"]')
    answer_list = [f'* {line.text_content().strip()}\n\n' for line in siblings]

    return answer_list, "Apte Dictionary"


def yates(word, part):
    sibling = etree.tostring(part.find('../*[@class="card-body"]//p[@class="card-text"]'))
    answer_inside = re.search(r'<p class="card-text">(.*?)</p>', str(sibling), re.DOTALL)
    answer_list = ["* " + HTMLStripper().strip(k) + '\n' for k in answer_inside.group(1).split('<br/>')]

    return answer_list, "Yates Dictionary"


def wilson(word, part):
    sibling = etree.tostring(part.find('../*[@class="card-body"]//p[@class="card-text"]'))
    answer_inside = re.search(r'<p class="card-text">(.*?)</p>', str(sibling), re.DOTALL)
    answer_list = ["* " + HTMLStripper().strip(k) + '\n' for k in answer_inside.group(1).split('<br/>')]

    return answer_list, "Wilson Dictionary"


def monier_wiliams(word, part):
    siblings = part.findall('../*[@class="card-body"]')
    answer_list = [f'* {line.text_content().strip()}\n\n' for line in siblings]

    return answer_list, "Monier Williams Dictionary"


def monier_williams2(word, part):  # for inline mode
    sibling = etree.tostring(part.find('../*[@class="card-body"]//p[@class="card-text"]'))
    answer_inside = re.search(r'<p class="card-text">(.*?)</p>', str(sibling), re.DOTALL)
    answer_list = []
    answer_length = 0
    for k in answer_inside.group(1).split('<br/>'):
        answer_length += len(k)
        if answer_length < 4000:  # default is 4096 for telegram
            if k != '' and (not k.isspace()):
                answer_list.append(HTMLStripper().strip(k) + '\n')
        else:
            break

    return answer_list, "Monier Williams Dictionary"
