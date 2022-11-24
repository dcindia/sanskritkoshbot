import re
from io import StringIO
from html.parser import HTMLParser
from lxml import etree, html


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
    sub_tree = html.fromstring(part)
    siblings = sub_tree.find('.//tr').findall("td")
    answer_row = [s.text_content() for s in siblings]
    answer_list = ["* " + HTMLStripper().strip(k) for k in answer_row if (k != '') and (not k.isspace())]
    # answer_list.append("\n<i><u>From Spoken Sanskrit</u></i>")
    # answer_string = ''.join(answer_list)
    return answer_list


def shabda_sagara(word, part):

    # sibling = etree.tostring(part.find('../*[@class="card-body"]//p[@class="card-text"]'), encoding='unicode')
    # answer_inside = re.search(r'<p class="card-text">(.*?)</p>', str(sibling), re.DOTALL)
    answer_list = ["* " + HTMLStripper().strip(k) for k in part.split('<BR>')]
    if len(answer_list) > 5:
        answer_list = answer_list[:6]
    # answer_list.append("\n<i><u>From Shabda Sagara</u></i>")
    # answer_string = ''.join(answer_list)
    return answer_list


def hindi_dict(word, part):
    answer_list = [f'* {word}\n', f'* {part}']
    # answer_table.append("\n<i><u>From Hindi Dictionary</u></i>")
    # answer_string = ''.join(answer_list)
    return answer_list


def apte(word, part):
    # BUG: answer are divided in many sections, however only 1 section in shown, which is incomplete.
    # TODO: Order sections by their id and join them to show complete meaning
    answer_list = [HTMLStripper().strip(k) for k in part.split('<BR>')]

    return answer_list


def yates(word, part):
    answer_list = ["* " + HTMLStripper().strip(k) for k in part.split('<BR>')]
    if len(answer_list) > 5:
        answer_list = answer_list[:6]

    return answer_list


def wilson(word, part):
    answer_list = ["* " + HTMLStripper().strip(k) for k in part.split('<BR>')]
    if len(answer_list) > 5:
        answer_list = answer_list[:6]

    return answer_list


def monier_wiliams(word, part):
    answer_list = [HTMLStripper().strip(k) for k in part.split('<BR>')]

    return answer_list


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


def universal(word, part):
    answer = part.find(".//p[@class='card-text']")
    answer_list = answer.text_content().split("\n")

    answer_length = 0
    for count, line in enumerate(answer_list):
        answer_length += len(line)
        if answer_length > 4000:
            return answer_list[0: count]

    print(answer_list)
    return answer_list
