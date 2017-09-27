import contextlib
import itertools
import math
import os
import pickle
import sqlite3
import sys

import mtgsdk

from collections import Counter

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/src')
from mtgworkshop.magic_db import DB, Cards, Ruling
from mtgworkshop.utils import make_unique


DEBUG = False

LOCAL_CACHE = 'cards.tmp.cache'


def create_db(dest=DB):
    cards = set()
    if os.path.exists(LOCAL_CACHE) and len(sys.argv) == 1:
        with open(LOCAL_CACHE, 'rb') as inp:
            cards = pickle.load(inp)
    else:
        cards = set(mtgsdk.Card.where(language="English").all())
        with open(LOCAL_CACHE, 'wb') as inp:
            pickle.dump(cards, inp)

    to_remove = set()
    for card in cards:
        if card.multiverse_id is None or card.image_url is None:
            to_remove.add(card)
    cards -= to_remove

    bfms = [card for card in cards if 'B.F.M.' in card.name]
    for card in bfms:
        card.multiverse_id = 9844

    mvid_count = Counter()
    for card in cards:
        mvid_count[card.multiverse_id] += 1
    for mvid, count in mvid_count.items():
        if mvid is None:
            continue
        if count > 1:
            dup = {card for card in cards if card.multiverse_id == mvid}
            names = set()
            to_remove = []
            for d in dup:
                if d.name in names and 'B.F.M.' not in d.name:
                    to_remove.append(d)
                else:
                    names.add(d.name)
            for d in to_remove:
                dup.remove(d)
                cards.remove(d)
            if len(dup) > 1:
                dup_list = list(dup)
                first = dup_list[0]
                dup_list = sorted(dup_list, key=lambda x: first.names.index(x.name))

                combined = mtgsdk.Card()
                copied = ('power', 'toughness', 'loyalty', 'life', 'hand', 'layout',
                          'set', 'set_name', 'multiverse_id', 'rarity', 'watermark',
                          'artist', 'image_url', 'number', 'legalities', 'rulings')
                slashed = ('name', 'mana_cost', 'type', 'text', 'flavor',
                           'original_text', 'original_type')
                appended = ('supertypes', 'types', 'subtypes', 'colors', 'color_identity')
                added = ('cmc',)
                for var in copied:
                    setattr(combined, var, getattr(first, var))
                for var in slashed:
                    setattr(combined, var, ' // '.join([getattr(x, var) or '' for x in dup_list]))
                for var in added:
                    setattr(combined, var, sum(getattr(x, var) or 0 for x in dup_list))
                for var in appended:
                    setattr(combined, var, sum((getattr(x, var) or [] for x in dup_list), []))

                for d in dup_list:
                    cards.remove(d)
                cards.add(combined)

    def get_alt_name(card):
        alt_names = getattr(card, 'names')
        name = getattr(card, 'name')
        if alt_names is None or len(alt_names) <= 1 or '//' in name:
            return None
        else:
            if name in alt_names:
                alt_names = alt_names[:]
                alt_names.remove(name)
            return ' // '.join(alt_names)

    databases = [
        ('cards',
         [
             lambda x: getattr(x, 'name'),
             lambda x: getattr(x, 'mana_cost'),
             lambda x: getattr(x, 'cmc') or 0,
             lambda x: getattr(x, 'type'),
             lambda x: getattr(x, 'text'),
             lambda x: getattr(x, 'power'),
             lambda x: getattr(x, 'toughness'),
             lambda x: getattr(x, 'loyalty'),
             lambda x: getattr(x, 'life'),
             lambda x: getattr(x, 'hand'),
             lambda x: getattr(x, 'layout'),
             get_alt_name
         ]),
        ('sets',
            [
                lambda x: getattr(x, 'set'),
                lambda x: getattr(x, 'set_name')
            ]),
        ('printings',
            [
                lambda x: getattr(x, 'multiverse_id'),
                lambda x: getattr(x, 'name'),
                lambda x: getattr(x, 'rarity'),
                lambda x: getattr(x, 'watermark'),
                lambda x: getattr(x, 'set'),
                lambda x: getattr(x, 'flavor'),
                lambda x: getattr(x, 'artist'),
                lambda x: getattr(x, 'image_url'),
                lambda x: getattr(x, 'original_text'),
                lambda x: getattr(x, 'original_type'),
                lambda x: getattr(x, 'number')
            ])
    ]

    m2m_databases = [
        ('supertypes', lambda x: getattr(x, 'supertypes'),
            [
                lambda x: x
        ]),
        ('types', lambda x: getattr(x, 'types'),
            [
                lambda x: x
        ]),
        ('subtypes', lambda x: getattr(x, 'subtypes'),
            [
                lambda x: x
        ]),
        ('colors', lambda x: getattr(x, 'colors'),
            [
                lambda x: x
        ]),
        ('color_identity', lambda x: getattr(x, 'color_identity'),
            [
                lambda x: x
        ]),
        ('rulings', lambda x: [Ruling.from_dict(y) for y in (getattr(x, 'rulings') or [])],
            [
                lambda x: x.date,
                lambda x: x.text,
        ])
    ]

    with contextlib.suppress(FileNotFoundError):
        os.remove(dest)
    conn = sqlite3.connect(dest)
    conn.row_factory = sqlite3.Row

    with conn:
        cur = conn.cursor()
        with open('src/res/database.schema') as schema:
            cur.executescript(schema.read())

    for database, fields in databases:
        populate_database(conn, database, fields, cards)

    cards = make_unique(cards, lambda x: x.name)
    for database, list_field, fields in m2m_databases:
        populate_m2m_database(conn, database, list_field, fields, cards)

    with conn:
        cur = conn.cursor()
        cur.execute('VACUUM;')
        cur.execute('ANALYZE;')

    conn.close()


def populate_database(conn, database, fields, cards):
    query = 'INSERT INTO {} VALUES ({})'.format(database, ','.join(['?' for f in fields]))
    for card in cards:
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(query, [field(card) for field in fields])
        except sqlite3.IntegrityError as e:
            e_desc = str(e)
            if e_desc == 'UNIQUE constraint failed: cards.name' or \
               e_desc == 'UNIQUE constraint failed: sets.set_name':
                continue
            else:
                print(e)
                print(card.name, card.names, card.set, card.number, card.multiverse_id)
    print('populated', database)


def populate_m2m_database(conn, database, list_field, fields, cards):
    query = 'INSERT INTO {} VALUES ({})'.format(database,
                                                ','.join(['?' for f in range(len(fields) + 1)]))
    for card in cards:
        vals = list_field(card)
        name = getattr(card, 'name')
        if vals is None:
            continue
        vals = set(vals)
        for val in vals:
            try:
                with conn:
                    cur = conn.cursor()
                    cur.execute(query, [name] + [field(val) for field in fields])
            except sqlite3.IntegrityError as e:
                print(e)
                print(card.name, card.types, card.supertypes)
    print('populated', database)


def populate_cache():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT multiverse_id FROM cards;')
    res = list(itertools.chain(*list(c.fetchall())))
    total_len = len(res)
    percent_point = math.ceil(total_len / 1000)
    Cards.find_by_mvid.to_disk = False
    try:
        for i, mvid in enumerate(res):
            if i % percent_point == 0:
                print(i / percent_point / 10)
            Cards.find_by_mvid(mvid)
    finally:
        print(total_len)
        Cards.find_by_mvid.save_to_disk()


def get_value_text(key, box='value'):
    def fun(doc):
        search_items = doc.find_all(**{"id": key})[0]
        search_item = search_items.find_all(**{'class': box})[0]
        return search_item.text.strip()
    return fun


def find_price(card):
    from bs4 import BeautifulSoup
    from fake_useragent import UserAgent
    from incapsula import IncapSession
    r_url = 'http://shop.tcgplayer.com/magic/{}/{}'.format(card['set_name'].replace(' ', '-').lower(),
                                                           card['name'].replace(' ', '-').lower())
    r_url = 'http://shop.tcgplayer.com/magic/hour-of-devastation/hour-of-devastation'
    session = IncapSession(user_agent=UserAgent().random, cookie_domain='.tcgplayer.com', max_retries=None)
    page = session.get(r_url)
    doc = BeautifulSoup(page.text, "lxml")
    search_items = doc.find_all(**{'class': 'price-point price-point--market'})
    search_items = search_items[0].find_all('tr')
    regular = None
    foil = None
    for item in search_items:
        if item.th.string == 'Normal':
            try:
                regular = float(item.td.string.replace('$', ''))
            except:
                regular = None
        elif item.th.string == 'Foil':
            try:
                foil = float(item.td.string.replace('$', ''))
            except:
                foil = None
        else:
            print(card['name'], item)
    return regular, foil


if __name__ == '__main__':
    create_db(DB + '.new')
    # populate_cache()
