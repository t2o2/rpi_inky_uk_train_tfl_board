from PIL import Image, ImageFont, ImageDraw
from collections import namedtuple
import datetime
import requests
from lxml import html
import re
from font_fredoka_one import FredokaOne

from inky import InkyPHAT

inky_display = InkyPHAT("red")
inky_display.set_border(inky_display.WHITE)


pixel_map = [
    [0, 0],
    [0, 21],
    [0, 42],
    [0, 63],
    [0, 84]
]


def display_txt(img, idx, message, color='BLACK'):
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("UbuntuMono-Regular.ttf", 14)
    x, y = pixel_map[idx]
    draw.text((x, y), message, getattr(inky_display, color), font=font)

def get_trains(tree):
    departs = tree.xpath('/html[1]/body[1]/div/strong[1]/text()')
    arrives = tree.xpath('/html[1]/body[1]/div/strong[2]/text()')
    Train = namedtuple('Train', 'depart dest status arrive')
    list_train = []
    for d, a in zip(departs, arrives):
        matched = re.match(r"(?P<depart>\d{2}:\d{2}) \((?P<status>.+)\) to (?P<dest>.+)", d)
        matched_a = re.match(r"(?P<arrive>\d{2}:\d{2})", a)
        if matched and matched_a:
            tr = Train(matched.group('depart'), matched.group('dest'), matched.group('status'), matched_a.group('arrive'))
            list_train.append(tr)
    return list_train

totime = lambda x: datetime.datetime.strptime(datetime.datetime.now().strftime('%Y-%m-%d') + 'T' + x, '%Y-%m-%dT%H:%M')

def get_later_trains(trains, minutes):
    out = []
    now = datetime.datetime.now()
    for tr in trains:
        if now + datetime.timedelta(minutes=minutes) < totime(tr.depart):
            out.append(tr)
    return out

def print_trains(img, all_trains, delay, offset):
    trains = get_later_trains(all_trains, delay)
    for i, tr in enumerate(trains[:2]):
        if tr.status == 'On time':
            color = 'BLACK'
            msg = f'{tr.depart} {tr.dest}'
            status = 'On time'
            msg = f'{tr.depart} {tr.dest[:14]:14} {status: >9}'
        else:
            color = 'RED'
            status = 'Exp ' + tr.status
            msg = f'{tr.depart} {tr.dest[:14]:14} {status: >9}'
        display_txt(img, offset+i, msg, color)

mapping = {'hammersmith-city': 'H&C', 'metropolitan': 'MET'}
severity_map = {0: 'Special', 1: 'Closed', 2: 'NoServ', 3: 'NoServ', 4: 'PClose', 5: 'PClose', 6: 'Severe', 7: 'Reduced', 8: 'Bus', 9: 'Minor', 10: 'Good', 11: 'PClose', 12: 'ExitOn', 13: 'Good', 14: 'ChFreq', 15: 'Divert', 16: 'NotRun', 17: 'Issue', 18: 'NoIssu', 19: 'Info'}

try:
    #rsp = requests.get("https://traintext.uk/rys/kgx")
    rsp = requests.get("https://traintext.uk/kgx/rys")
    tree = html.fromstring(rsp.content)
    rys_trains = get_trains(tree)

    rsp = requests.get("https://traintext.uk/lbg/pur")
    tree = html.fromstring(rsp.content)
    pur_trains = get_trains(tree)

    tfl = requests.get("https://api.tfl.gov.uk/line/mode/tube/status")
    service = {x['id']:x['lineStatuses'][0]['statusSeverity'] for x in tfl.json() if x['id'] in ['hammersmith-city', 'metropolitan']}

    tube_status = [[mapping[k],v] for k, v in service.items()]

    img = Image.new("P", (inky_display.WIDTH, inky_display.HEIGHT), 200)
    print_trains(img, rys_trains, 0, 0)
    #===
    msg = ''
    for line in tube_status:
        msg += f'|{line[0]} {severity_map[line[1]]: >9}  '
    display_txt(img, 2, msg[:-1], 'BLACK')
    #===
    print_trains(img, pur_trains, 20, 3)
    inky_display.set_image(img)
    inky_display.show()
except:
    img = Image.open("hello-badge.png")
    draw = ImageDraw.Draw(img)
    message = "Chuan Bai"
    w, h = font.getsize(message)
    x = (inky_display.WIDTH / 2) - (w / 2)
    y = 60
    font = ImageFont.truetype(FredokaOne, 22)
    #draw.text((x, y), message, inky_display.WHITE, font)
    draw.text((x, y), message, inky_display.RED, font)
    inky_display.set_image(img)
    inky_display.show()
