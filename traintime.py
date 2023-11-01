from collections import namedtuple
from font_fredoka_one import FredokaOne
from inky import InkyPHAT
from logging.handlers import TimedRotatingFileHandler
from loguru import logger
from lxml import html
from PIL import Image, ImageFont, ImageDraw
import datetime
import hashlib
import logging
import re
import requests
import os

# Setup hardware
inky_display = InkyPHAT("red")
inky_display.set_border(inky_display.WHITE)

# Create a timed rotating file handler
handler = TimedRotatingFileHandler("rotated_log.log", when="midnight", interval=1, backupCount=7)
logger.add(handler)
        
pixel_map = [
    [0, 0],
    [0, 21],
    [0, 42],
    [0, 63],
    [0, 84]
]

tube_mapping = {'hammersmith-city': 'H&C', 'metropolitan': 'MET', 'northern': 'NOR', 'central': 'CTR', 'dlr': 'DLR'}
severity_map = {0: 'Special', 1: 'Closed', 2: 'NoServ', 3: 'NoServ', 4: 'PClose', 5: 'PClose', 6: 'Severe', 7: 'Reduced', 8: 'Bus', 9: 'Minor', 10: 'Good', 11: 'PClose', 12: 'ExitOn', 13: 'Good', 14: 'ChFreq', 15: 'Divert', 16: 'NotRun', 17: 'Issue', 18: 'NoIssu', 19: 'Info'}

# Go to https://traintext.uk/ to search
departing_station = 'mog'
arriving_station = 'pbr'

def hash(img):
   return hashlib.md5(img.tobytes()).hexdigest()

def display_txt(img, idx, message, color='BLACK'):
    logger.info(f'display_txt msg: {idx} {message}')
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

def print_trains(img, all_trains, delay=0, idx_offset=0):
    trains = get_later_trains(all_trains, delay)
    for i, tr in enumerate(trains[:4]):
        if tr.status == 'On time':
            color = 'BLACK'
            status = 'On time'
            msg = f'{tr.depart} {tr.dest[:14]:14} {status: >9}'
        else:
            color = 'RED'
            status = 'Exp ' + tr.status
            msg = f'{tr.depart} {tr.dest[:14]:14} {status: >9}'
        display_txt(img, idx_offset+i, msg, color)

def display_if_different(ha_img):
    ha_last = ''
    if os.path.exists('img_hash.txt'):
        with open('img_hash.txt', 'r') as f:
            ha_last = f.read()
    
    if ha_last != ha_img:
        with open('img_hash.txt', 'w') as f:
            f.write(ha_img)
        logger.info('updating display')
        inky_display.show()
    else:
        logger.info('not updating - same image')

def generate_train_img():
    rsp = requests.get(f"https://traintext.uk/{departing_station}/{arriving_station}")
    tree = html.fromstring(rsp.content)
    trains = get_trains(tree)
    logger.info(f'trains: {trains}')
    
    tfl = requests.get("https://api.tfl.gov.uk/line/mode/tube/status")
    service_list = tfl.json()
    dlr = requests.get("https://api.tfl.gov.uk/line/mode/dlr/status")
    service_list += dlr.json()
    
    service = {x['id']:x['lineStatuses'][0]['statusSeverity'] for x in tfl.json() if x['id'] in ['northern', 'dlr']}
    
    tube_status = [[tube_mapping[k],v] for k, v in service.items()]
    logger.info(f'tube: {tube_status}')
    # Creation of new image
    img = Image.new("P", (inky_display.WIDTH, inky_display.HEIGHT), 200)
    print_trains(img, trains, delay=10, idx_offset=0)
    #===
    msg = ''
    for line in tube_status:
        msg += f'|{line[0]} {severity_map[line[1]]: >9}  '
    is_good = all([x[1] == 10 for x in tube_status])
    display_txt(img, 4, msg[:-1], 'BLACK' if is_good else 'RED')
    #===
    inky_display.set_image(img)
    return img

def generate_default_img():
    img = Image.open("hello-badge.png")
    draw = ImageDraw.Draw(img)
    message = "Chuan Bai"
    font = ImageFont.truetype(FredokaOne, 22)
    w, h = font.getsize(message)
    x = (inky_display.WIDTH / 2) - (w / 2)
    y = 60
    draw.text((x, y), message, inky_display.RED, font)
    inky_display.set_image(img)
    img.save('new.png')
    return img

def main():
    try:
        try:
            img = generate_train_img()
            ha_img = hash(img)
        except:
            img = generate_default_img()
            ha_img = hash(img)
        display_if_different(ha_img)
    except Exception as e:
        logger.exception(e)

if __name__ == '__main__':
    main()
