import contextlib
import itertools
import math
import os
import pickle
import sqlite3
import sys

import mtgsdk

from collections import Counter

from magic_db import DB, cards_var, Cards


DEBUG = False

LOCAL_CACHE = 'cards.tmp.cache'


def create_db(dest=DB):
    cards = set()
    if os.path.exists(LOCAL_CACHE) and len(sys.argv) == 1:
        with open(LOCAL_CACHE, 'rb') as inp:
            cards = pickle.load(inp)
    else:
        cards = frozenset(mtgsdk.Card.where(language="English").all())
        with open(LOCAL_CACHE, 'rb') as inp:
            pickle.dump(cards, inp)
    mvid_count = Counter()
    for card in cards:
        mvid_count[card.multiverse_id] += 1
    for mvid, count in mvid_count.items():
        if count == 2:
            dup = [card for card in cards if cards.multiverse_id == mvid]
            if dup[0].name == dup[1].name:
                pass
            else:
                cards.remove(dup[1])
        elif count > 2:
            dup = [card for card in cards if cards.multiverse_id == mvid]
            next(dup)
            for i in dup:
                cards.remove(dup[i])

    with contextlib.suppress(FileNotFoundError):
        os.remove(dest)
    conn = sqlite3.connect(dest)
    c = conn.cursor()
    create_command = "CREATE TABLE cards ("
    vars_dict = vars(cards[0])
    sql = 'INSERT INTO cards('
    for var in cards_var:
        create_command += '\n"' + var + '"'
        try:
            int(vars_dict[var])
            create_command += ' int'
        except:
            create_command += ' text'
        create_command += ','
        sql += '"' + var + '",'
    sql = sql[:-1]
    sql += ')\nVALUES(' + '?,' * (len(cards_var) - 1) + '?)'
    create_command = create_command[:-1]
    create_command += '\n);'
    if DEBUG:
        print(create_command)
    c.execute(create_command)
    conn.commit()
    cards = list(card for card in cards if card.multiverse_id is not None)
    if DEBUG:
        print(sql)
        print(len(cards))
    card_lists = [list(str(vars(card)[var]) for var in cards_var) for card in cards]
    c.executemany(sql, card_lists)
    conn.commit()
    conn.close()


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
            # if i & 32 == 32:
            #     print(i, 100 * i / f_total_len)
            Cards.find_by_mvid(mvid)
    finally:
        print(total_len)
        Cards.find_by_mvid.save_to_disk()


if __name__ == '__main__':
    # create_db(DB + '.new')
    populate_cache()
