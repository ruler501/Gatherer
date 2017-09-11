import ast
import contextlib
import functools
import inspect
import os
import pickle
import re
import sqlite3

from collections import Counter

import mtgsdk


def regexp(expr, item):
    return re.search(item, expr) is not None


def contains(item, expr):
    try:
        res = ast.literal_eval(item)
        return res is not None and expr in res
    except:
        return expr in item


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
var_type = \
    {
        'printings': 'list',
        'rarity': 'string',
        'border': 'string',  # Effectively unused, should phase out
        'watermark': 'string',
        'loyalty': 'int',
        'set': 'string',
        'multiverse_id': 'int',
        'text': 'string',
        'type': 'string',  # Full type line
        'life': 'int',  # Vanguard only
        'subtypes': 'list',
        'flavor': 'string',
        'rulings': 'list',  # Of dicts(date, string)
        'mana_cost': 'string',  # In the form of ({.(/.)?})+
        'starter': 'text',  # What does this do?
        'names': 'list',  # Names for double faced cards
        'timeshifted': 'text',  # What does this do?
        'foreign_names': 'list',  # Of dicts(language, imageUrl, multiverseid, name)
        'artist': 'string',
        'supertypes': 'list',
        'types': 'list',
        'colors': 'list',
        'source': 'string',  # Effectively unused should phase out
        'id': 'bytes',  # Can probably be hidden
        'layout': 'string',
        'set_name': 'string',
        'power': 'int',
        'cmc': 'int',
        'name': 'string',
        'legalities': 'list',  # Of dicts(legality, format)
        'image_url': 'string',
        'color_identity': 'list',
        'original_text': 'string',
        'number': 'int',  # Collectors Number
        'variations': 'list',  # mvids for things with multiple arts in same set
        'release_date': 'string',  # Effectively unused
        'original_type': 'string',
        'hand': 'int',  # Vanguard only
        'toughness': 'int'
    }


def disk_cache(cache_file):
    def dec(fun):
        cache = {}
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as inp:
                cache = pickle.load(inp)

        def f(*args, **kwargs):
            args_tuple = frozenset(kwargs.items()), *args
            res = cache.get(args_tuple, None)
            if res is not None:
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


def row_to_dict(row):
    res = {}

    for var, val in zip(cards_var, row):
        if val is None or val == 'None':
            res[var] = None
        elif var_type[var] == 'int':
            try:
                res[var] = int(val)
            except ValueError:
                res[var] = str(val)
        elif var_type[var] == 'list':
            res[var] = ast.literal_eval(val)
        else:
            res[var] = str(val)

    return res


class Cards:
    class CardsQuery:
        def __init__(self):
            self.query = 'SELECT * FROM cards WHERE '
            self.params = []
            self.connector = ''
            self.back_conn = ' AND '
            self.preds = []

        def where(self, **kwargs):
            for key, value in kwargs.items():
                if key in cards_var:
                    self.query += self.connector + key + '=?'
                    if value is None:
                        value = "None"
                    self.params.append(value)
                if self.connector == '':
                    self.connector = self.back_conn
            return self

        def where_matches(self, **kwargs):
            for key, value in kwargs.items():
                if key in cards_var:
                    self.query += self.connector + 'REGEXP(' + key + ',?)'
                    self.params.append(value)
                if self.connector == '':
                    self.connector = self.back_conn
            return self

        def where_contains(self, **kwargs):
            for key, value in kwargs.items():
                if key in cards_var:
                    self.query += self.connector + 'CONTAINS(' + key + ',?)'
                    self.params.append(value)
                if self.connector == '':
                    self.connector = self.back_conn
            return self

        def where_contains_all(self, **kwargs):
            for key, value in kwargs.items():
                if key in cards_var:
                    self.query += self.connector + '('
                    conn = ''
                    for v in value:
                        self.query += conn + 'CONTAINS(' + key + ',?)'
                        self.params.append(v)
                        conn = ' AND '
                    self.query += ')'
                if self.connector == '':
                    self.connector = self.back_conn
            return self

        def where_at_least(self, **kwargs):
            for key, value in kwargs.items():
                if key in cards_var:
                    self.query += self.connector + key + '>=?'
                    self.params.append(value)
                if self.connector == '':
                    self.connector = self.back_conn
            return self

        def where_at_most(self, **kwargs):
            for key, value in kwargs.items():
                if key in cards_var:
                    self.query += self.connector + 'CONTAINS(' + key + ',?)'
                    self.params.append(value)
                if self.connector == '':
                    self.connector = self.back_conn
            return self

        def with_pred(self, pred):
            self.preds.append(pred)
            return self

        def start_block(self):
            self.query += self.connector + '('
            self.connector = ''
            self.back_conn = self.connector
            return self

        def end_block(self):
            self.query += ')'
            self.connector = self.back_conn
            return self

        def use_and(self):
            self.connector = ' AND '
            return self

        def use_or(self):
            self.connector = ' OR '
            return self

        def use_not(self):
            self.query += self.connector + ' NOT '
            self.back_conn = self.connector
            self.connector = ''
            return self

        def find_all(self):
            cursor = get_cursor()
            if DEBUG:
                print(self.query, self.params)
            cursor.execute(self.query, self.params)
            cards = [row_to_dict(x) for x in cursor.fetchall()]
            return (card for card in cards if all(pred(card) for pred in self.preds))

        def find_one(self):
            cursor = get_cursor()
            if DEBUG:
                print(self.query, self.params)
            cursor.execute(self.query, self.params)
            cards = [row_to_dict(x) for x in cursor.fetchall()]
            return next((card for card in cards if all(pred(card) for pred in self.preds)))


for member in inspect.getmembers(Cards.CardsQuery, predicate=inspect.isfunction):
    member_name = member[0]
    if member_name.startswith('_'):
        continue

    def func(member_name, *args, **kwargs):
        query = Cards.CardsQuery()
        f = getattr(query, member_name)
        return f(*args, **kwargs)

    setattr(Cards, member_name, staticmethod(functools.partial(func, member_name)))


@disk_cache('cards.mvid.cache')
def get_card_by_mvid(mvid):
    return Cards.where(multiverse_id=mvid).find_one()


@disk_cache('cards.name.cache')
def get_card_by_name(name):
    return Cards.where(name=name).find_one()


def get_all_printings(mvid):
    card_name = get_card_by_mvid(mvid)['name']
    cards = Cards.where(name=card_name).find_all()
    return (x['multiverse_id'] for x in cards)


def is_origin_legal(mvid):
    card = get_card_by_mvid(mvid)
    printings = card['printings']
    for printing in printings:
        if printing in origins_list:
            if DEBUG:
                print(printing, card['name'])
            return True
    return False


def filter_to_origin_legal(mvids):
    return (mvid for mvid in mvids if is_origin_legal(mvid))


# cards = Cards.where_contains(name='Lightning')\
#     .where(toughness=1)\
#     .use_not().where_contains(name='Ball')\
#     .use_not().where(rulings=None)\
#     .find_all()
# cards = make_unique(cards, lambda x: x['name'])
# for x in sorted(cards, key=lambda x: x['name']):
#     print(x['name'], x['rulings'][0]['text'])