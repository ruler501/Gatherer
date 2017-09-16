import ast
import functools
import inspect
import re
import sqlite3

from utils import disk_cache


def regexp(expr, item):
    return re.search(item.lower(), expr.lower()) is not None


DB = "res/cards.sqlite3"
origins = r'(ORI)|(BFZ)|(OGW)|(SOI)|(EMN)|(KLD)|(AER)|(AKH)|(HOU)|(DDP)|(DDQ)|(DDR)|(DDS)|(E01)|(C15)|(C16)|(C17)|(CN2)'
origins_list = origins.replace('(', '').replace(')', '').split('|')
DEBUG = True
# DEBUG = False
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
        'rulings': 'list',  # Of dicts(date, text)
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
        'power': 'string',
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
        'toughness': 'string',
        'type_line': 'string'
    }


def get_conn():
    if get_conn.conn is None:
        get_conn.conn = sqlite3.connect(DB)
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


def row_to_dict(row):
    res = {}

    for var, val in zip(cards_var, row):
        if var == 'type':
            var = 'type_line'
        if val is None or val == 'None':
            res[var] = None
        elif var_type[var] == 'int':
            try:
                res[var] = int(val)
                print("made {} an int with val {}".format(var, val))
            except ValueError:
                res[var] = str(val)
        elif var_type[var] == 'list':
            res[var] = ast.literal_eval(val)
        else:
            res[var] = str(val)

    return res


# Need to get tcgplayer partnership first so should probably make an app first
def get_price(card):
    pass


# Note: Blocks don't work with predicates, but negated does
class Cards:
    class CardsQuery:
        ops = \
            {
                "equals": "{}='{}'",
                "matches": "REGEXP({}, '{}')",
                "contains": "{} LIKE '%{}%'",
                "at_least": "{}>={}",
                "at_most": "{}<={}"
            }
        calculated_ops = \
            {
                "equals": lambda x, y: x == y,
                "matches": regexp,
                "contains": lambda x, y: x in y,
                "at_least": lambda x, y: x >= y,
                "at_most": lambda x, y: x <= y
            }
        calculated_vars = \
            {
                "price": get_price,
                # "legal_in_*"
            }

        def __init__(self):
            self.query = 'SELECT * FROM cards WHERE '
            self.connector = ''
            self.back_conn = ' AND '
            self.preds = []
            self.use_not = False

        def _where(self, _lookup, **kwargs):
            for key, value in kwargs.items():
                if key == 'type_line':
                    key = 'type'
                if key in cards_var:
                    if value is None:
                        value = "None"
                    self.query += self.connector
                    if self.use_not:
                        self.query += ' NOT '
                        self.use_not = False
                    self.query += self.ops[_lookup].format(key, value)
                elif key in self.calculated_vars:
                    # Add a predicate that calculates the value from card
                    # Then checks if calculated_ops[_lookup] returns true
                    pass
                if self.connector == '':
                    self.connector = self.back_conn
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

        def with_pred(self, pred):
            if self.use_not:
                pred = functools.partial(pred, lambda p, x: not p(x))
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

        def negated(self):
            self.use_not = not self.use_not
            return self

        def find_all(self):
            cursor = get_cursor()
            if DEBUG:
                print(self.query)
            cursor.execute(self.query)
            cards = [row_to_dict(x) for x in cursor.fetchall()]
            return (card for card in cards if all(pred(card) for pred in self.preds))

        def find_one(self):
            return next(self.find_all())

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


for member in inspect.getmembers(Cards.CardsQuery, predicate=inspect.isfunction):
    member_name = member[0]
    if member_name.startswith('_'):
        continue

    def func(member_name, *args, **kwargs):
        query = Cards.CardsQuery()
        f = getattr(query, member_name)
        return f(*args, **kwargs)

    setattr(Cards, member_name, staticmethod(functools.partial(func, member_name)))


def is_origin_legal(mvid):
    card = Cards.find_by_mvid(mvid)
    printings = card['printings']
    for printing in printings:
        if printing in origins_list:
            if DEBUG:
                print(printing, card['name'])
            return True
    return False
