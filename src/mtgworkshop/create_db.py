import contextlib
import os
import sqlite3

import mtgsdk

from collections import Counter

from magic_db import DB, cards_var


DEBUG = False


def create_db(dest=DB):
    cards = set(mtgsdk.Card.where(language="English").all())
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


if __name__ == '__main__':
    create_db()
