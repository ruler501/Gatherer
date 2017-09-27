import functools
import inspect
import re
import sqlite3

from utils import disk_cache, split_and_cut


def regexp(expr, item):
    return re.search(item.lower(), expr.lower()) is not None


DB = "res/cards.sqlite3"
origins = r'(ORI)|(BFZ)|(OGW)|(SOI)|(EMN)|(KLD)|(AER)|(AKH)|(HOU)|(DDP)|(DDQ)|(DDR)|(DDS)|(E01)|(C15)|(C16)|(C17)|(CN2)'
origins_list = origins.replace('(', '').replace(')', '').split('|')
DEBUG = True
# DEBUG = False


def get_conn():
    if get_conn.conn is None:
        get_conn.conn = sqlite3.connect(DB)
        get_conn.conn.create_function("REGEXP", 2, regexp)
        get_conn.conn.row_factory = sqlite3.Row
    return get_conn.conn


def get_cursor(conn=None):
    if conn is None:
        conn = get_conn()
    if get_cursor.cursor is None:
        get_cursor.cursor = conn.cursor()
    return get_cursor.cursor


get_conn.conn = None
get_cursor.cursor = None


class Ruling:
    def __init__(self, date, text):
        self.date = date
        self.text = text

    @staticmethod
    def from_dict(dic):
        if dic is None:
            return None
        return Ruling(dic['date'], dic['text'])


class Card:
    def __init__(self, row):
        for var in row.keys():
            setattr(self, var, row[var])

        mvid = self.mvid = getattr(self, 'multiverse_id')
        name = getattr(self, 'name')
        if mvid is None or name is None:
            raise ValueError('Did not set multiverse_id or name in row')

        set_types = [
            ('supertypes', lambda x: x['supertype']),
            ('types', lambda x: x['type']),
            ('subtypes', lambda x: x['subtype']),
            ('colors', lambda x: x['color']),
            ('color_identity', lambda x: x['color']),
            ('rulings', lambda x: Ruling(x['date'], x['text']))
        ]

        conn = get_conn()
        for set_type, cons in set_types:
            vals = conn.execute('select * from {} where card_name = ?'.format(set_type),
                                (name,))
            setattr(self, set_type, frozenset(cons(x) for x in vals))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.multiverse_id == other.multiverse_id
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return self.multiverse_id != other.multiverse_id
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self.multiverse_id)

    def __getitem__(self, index):
        return getattr(self, index)

    def items(self):
        return {(key, getattr(self, key)) for key in Cards.card_vars}

    def get(self, key, default_val=None):
        return getattr(self, key, default_val)


class Cards:
    class CardsQuery:
        self_var_ops = \
            {
                "equals": {},
                "matches": {},
                "contains": {},
                "at_least": {},
                "at_most": {},
                "greater": {},
                "lesser": {},
            }
        var_tables = \
            {
                # "printings": None,
                "rarity": 'printings',
                "watermark": 'printings',
                "alt_name": 'cards',
                "loyalty": 'cards',
                "set": 'printings',
                "multiverse_id": 'printings',
                "text": 'cards',
                "type_line": 'cards',
                "life": 'cards',
                "flavor": 'printings',
                "rulings": None,
                "mana_cost": 'card',
                "artist": 'printings',
                "supertypes": None,
                "types": None,
                "subtypes": None,
                "colors": None,
                "layout": 'cards',
                "set_name": 'sets',
                "power": 'cards',
                "cmc": 'cards',
                "name": 'cards',
                # "legalities": 'None',
                "image_url": 'printings',
                "color_identity": None,
                "original_text": 'printings',
                "number": 'printings',
                "original_type": 'printings',
                "hand": 'cards',
                "toughness": 'cards'
            }
        basic_statement = '''SELECT printings.rarity, printings.watermark, cards.alt_name, cards.loyalty,
            printings.set_code, printings.multiverse_id, cards.text, cards.type_line, cards.life,
            printings.flavor, cards.mana_cost, printings.artist, cards.layout, sets.set_name,
            cards.power, cards.cmc, cards.name, printings.image_url, printings.original_text,
            printings.number, printings.original_type, cards.hand, cards.toughness
            FROM cards
            INNER JOIN printings on printings.name = cards.name
            INNER JOIN sets on sets.set_code = printings.set_code'''
        normal_connectors = {' AND '}

        def __init__(self):
            self.query = self.basic_statement[:]
            self.params = []
            self.connector = ' WHERE '
            self.use_not = False

        def _where(self, _lookup, **kwargs):
            if len(kwargs) > 1:
                raise ValueError('Too many args at once, only accepts one per call')

            key, value = list(kwargs.items())[0]
            if key not in self.self_var_ops[_lookup]:
                raise ValueError('Cannot test key by value')
            if _lookup == 'contains' and not Cards.card_vars[key].startswith('list'):
                value = '%{}%'.format(value)

            table = self.var_tables[key]
            table_key = key
            if table is not None:
                table_key = '{}.{}'.format(table, key)

            self.query += self.connector
            self.params.append(value)
            if self.use_not:
                self.query += ' NOT '
                self.use_not = False
            self.query += self.self_var_ops[_lookup][key].format(table_key)

            if self.connector not in self.normal_connectors:
                self.connector = ' AND '
            return self

        def where(self, **kwargs):
            return self._where("equals", **kwargs)

        def where_matches(self, **kwargs):
            return self._where("matches", **kwargs)

        def where_contains(self, **kwargs):
            return self._where("contains", **kwargs)

        def where_contains_all(self, **kwargs):
            for key, value in kwargs.items():
                for v in value:
                    self.where_contains(**{key: v})
            return self

        def where_at_least(self, **kwargs):
            return self._where("at_least", **kwargs)

        def where_at_most(self, **kwargs):
            return self._where("at_most", **kwargs)

        def where_greater(self, **kwargs):
            return self._where("greater", **kwargs)

        def where_lesser(self, **kwargs):
            return self._where("lesser", **kwargs)

        def negated(self):
            self.use_not = not self.use_not
            return self

        def find_all(self):
            conn = get_conn()
            if DEBUG:
                print(self.query, self.params)
            cards = [Card(x) for x in conn.execute(self.query, self.params)]
            return cards

        def find_one(self):
            cursor = get_cursor()
            if DEBUG:
                print(self.query, self.params)
            cursor.execute(self.query, self.params)
            row = cursor.fetchone()
            if row is None:
                return None
            else:
                return Card(row)

    @staticmethod
    @disk_cache('res/cards.mvid.cache')
    def find_by_mvid(mvid):
        return Cards.where(multiverse_id=mvid).find_one()

    @staticmethod
    @disk_cache('res/printings.mvid.cache')
    def find_all_printings(mvid):
        card_name = Cards.find_by_mvid(mvid)['name']
        cards = Cards.where(name=card_name).find_all()
        return (x['multiverse_id'] for x in cards)

    @staticmethod
    def default_sort_key(card):
        return (card['cmc'], card['name'])

    card_vars = \
        {
            # "printings": 'list<string>',
            "rarity": 'string',
            "watermark": 'string',
            "alt_name": 'string',
            "loyalty": 'int',
            "set_code": 'string',
            "multiverse_id": 'int',
            "text": 'string',
            "type_line": 'string',
            "life": 'int',
            "flavor": 'string',
            "rulings": 'list<Ruling>',
            "mana_cost": 'string',
            "artist": 'string',
            "supertypes": 'list<string>',
            "types": 'list<string>',
            "subtypes": 'list<string>',
            "colors": 'list<string>',
            "layout": 'string',
            "set_name": 'string',
            "power": 'int',
            "cmc": 'int',
            "name": 'string',
            # "legalities": 'list<Legality>',
            "image_url": 'string',
            "color_identity": 'list<string>',
            "original_text": 'string',
            "number": 'string',
            "original_type": 'string',
            "hand": 'int',
            "toughness": 'int'
        }


for member in inspect.getmembers(Cards.CardsQuery, predicate=inspect.isfunction):
    member_name = member[0]
    if member_name.startswith('_'):
        continue

    def func(member_name, *args, **kwargs):
        query = Cards.CardsQuery()
        f = getattr(query, member_name)
        return f(*args, **kwargs)

    setattr(Cards, member_name, staticmethod(functools.partial(func, member_name)))

for var, var_type in Cards.card_vars.items():
    if var_type.startswith('string'):
        Cards.CardsQuery.self_var_ops['equals'][var] = '{} = ?'
        Cards.CardsQuery.self_var_ops['matches'][var] = 'REGEXP({}, ?)'
        Cards.CardsQuery.self_var_ops['contains'][var] = '{} LIKE ?'
    if var_type.startswith('int'):
        Cards.CardsQuery.self_var_ops['equals'][var] = '{} = ?'
        Cards.CardsQuery.self_var_ops['at_least'][var] = '{} >= ?'
        Cards.CardsQuery.self_var_ops['at_most'][var] = '{} <= ?'
        Cards.CardsQuery.self_var_ops['greater'][var] = '{} > ?'
        Cards.CardsQuery.self_var_ops['lesser'][var] = '{} < ?'
    if var_type.startswith('list') and \
       split_and_cut(var_type, '<', 1, '>', 0).startswith('string'):
        inner_var = \
            {
                'supertypes': 'supertype',
                'types': 'type',
                'subtypes': 'subtype',
                'colors': 'color',
                'color_identity': 'color'
            }
        subquery = 'select * from {} where card_name = cards.name'
        grouping = 'group by card_name having count(*)'
        Cards.CardsQuery.self_var_ops['contains'][var] = 'exists({} and {} = ?)'.format(subquery,
                                                                                        inner_var[var])
        Cards.CardsQuery.self_var_ops['at_least'][var] = 'exists({} {} >= ?)'.format(subquery, grouping)
        Cards.CardsQuery.self_var_ops['at_most'][var] = 'exists({} {} <= ?)'.format(subquery, grouping)
        Cards.CardsQuery.self_var_ops['greater'][var] = 'exists({} {} > ?)'.format(subquery, grouping)
        Cards.CardsQuery.self_var_ops['lesser'][var] = 'exists({} {} < ?)'.format(subquery, grouping)


def is_origin_legal(mvid):
    card = Cards.find_by_mvid(mvid)
    printings = card['printings']
    for printing in printings:
        if printing in origins_list:
            if DEBUG:
                print(printing, card['name'])
            return True
    return False
