import ast
import contextlib
import os
import pickle
import re
import sqlite3

import mtgsdk


def regexp(expr, item):
    return re.search(item, expr) is not None


def contains(item, expr):
    try:
        res = ast.literal_eval(item)
        return res is not None and expr in res
    except:
        return False


DB = "cards.sqlite3"
origins = r'(ORI)|(BFZ)|(OGW)|(SOI)|(EMN)|(KLD)|(AER)|(AKH)|(HOU)|(DDP)|(DDQ)|(DDR)|(DDS)|(E01)|(C15)|(C16)|(C17)|(CN2)'
origins_list = origins.replace('(', '').replace(')', '').split('|')
# DEBUG = True
DEBUG = False
cards_var = ("printings", "rarity", "border", "watermark",
             "loyalty", "set", "multiverse_id", "text", "type",
             "life", "subtypes", "flavor", "rulings", "mana_cost",
             "starter", "names", "timeshifted", "foreign_names",
             "artist", "supertypes", "types", "colors", "source",
             "id", "layout", "set_name", "power", "cmc", "name",
             "legalities", "image_url", "color_identity",
             "original_text", "number", "variations",
             "release_date", "original_type", "hand", "toughness")
# CREATE TABLE cards (
# "printings" list<string(enum 3 letter set symbols)>,
# "rarity" string(enum rarities),
# "border" text,\\
# "watermark" text,\\
# "loyalty" text,\\
# "set" string(enum 3letter set symbols),
# "multiverse_id" int,
# "text" string,
# "type" string,
# "life" text,\\
# "subtypes" list<string>,\\
# "flavor" string?,\\
# "rulings" list<dict<(date,text)>>,
# "mana_cost" string(valid mana cost ({.(/.)?})+,
# "starter" text, \\
# "names" text, \\
# "timeshifted" text, \\
# "foreign_names" text, \\
# "artist" string,
# "supertypes" list<string(enum supertypes)>, \\
# "types" list<string(enum types)>,
# "colors" list<string(enum colors)>, \\
# "source" text, \\
# "id" string(hex),
# "layout" text, \\
# "set_name" string,
# "power" int, \\
# "cmc" uint,
# "name" string,
# "legalities" list<dict<(legality, format)>>,
# "image_url" url,
# "color_identity" list<char(WUBRG)>?, \\
# "original_text" string,
# "number" int?, \\
# "variations" text, \\
# "release_date" text, \\
# "original_type" string,
# "hand" text, \\
# "toughness" int
# );


def disk_cache(cache_file):
    def dec(fun):
        cache = {}
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as inp:
                cache = pickle.load(inp)

        def f(*args, **kwargs):
            args_tuple = tuple(*args, frozenset(kwargs.items()))
            res = cache.get(args_tuple, None)
            if res is not None:
                if DEBUG:
                    print(args_tuple)
                return res
            res = fun(*args, **kwargs)
            cache[args_tuple] = res
            with open(cache_file, 'wb') as inp:
                pickle.dump(cache, inp)
            return res
        return f
    return dec


def make_unique(lst, func=lambda x: x):
    res = []
    used = set()
    for x in lst:
        val = func(x)
        if val not in used:
            res.append(x)
            used.add(val)
    return res


def get_conn():
    if get_conn.conn is None:
        get_conn.conn = sqlite3.connect('cards.sqlite3')
        get_conn.conn.create_function("CONTAINS", 2, contains)
        get_conn.conn.create_function("REGEXP", 2, regexp)
    return get_conn.conn


def get_cursor(conn=None):
    if conn is None:
        conn = get_conn()
    if get_cursor.cursor is None:
        get_cursor.cursor = conn.cursor()
    return get_cursor.cursor


get_conn.conn = None
get_cursor.cursor = None


def create_db(dest=DB):
    cards = []
    cards = mtgsdk.Card.where(language="English").all()
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


def row_to_dict(row):
    return {cards_var[i]: row[i] for i in range(len(cards_var))}


def get_cards(**kwargs):
    sql = 'SELECT * FROM cards WHERE '
    params = []
    preds = []
    connect = ' '
    for key, value in kwargs.items():
        if key == 'mvid':
            key = 'multiverse_id'
        if key in cards_var:
            sql += connect + key + '=?'
            params.append(value)
        elif key.startswith('reg_'):
            sql += connect + 'REGEXP(' + key[4:] + ',?)'
            params.append(value)
        else:
            preds.append(value)
        connect = ' AND '
    cursor = get_cursor()
    if DEBUG:
        print(sql, params)
    cursor.execute(sql, params)
    cards = [row_to_dict(x) for x in cursor.fetchall()]
    return (card for card in cards if all(pred(card) for pred in preds))


@disk_cache('card.cache')
def get_card(**kwargs):
    if DEBUG:
        print("GETTING CARD")
    return next(get_cards(**kwargs))


def get_all_printings(mvid):
    cards = get_cards(name=get_card(multiverse_id=mvid)['name'])
    return (x['multiverse_id'] for x in cards)


def is_origin_legal(mvid):
    card = get_card(multiverse_id=mvid)
    printings = ast.literal_eval(card['printings'])
    for printing in printings:
        if printing in origins_list:
            if DEBUG:
                print(printing, card['name'])
            return True
    return False


def filter_to_origin_legal(mvids):
    return (mvid for mvid in mvids if is_origin_legal(mvid))
