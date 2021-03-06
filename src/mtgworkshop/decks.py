import os

from collections import Counter, defaultdict
from weakref import WeakMethod

from kivy.clock import mainthread
from kivy.metrics import dp, sp
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.screenmanager import Screen

from mtgworkshop.configuration import DefaultConfiguration
from mtgworkshop.magic_db import Cards
from mtgworkshop.results import CardResult
from mtgworkshop.utils import split_and_cut


class Deck:
    def __init__(self, name='Untitled', file_location=None):
        self.boards = defaultdict(Counter)
        self.add_board('Main')
        self.add_board('Sideboard')
        self.name = name
        self.file_location = file_location
        self.listeners = set()

    def __getitem__(self, key):
        return self.get_board(key)

    def __len__(self):
        return len(self.boards)

    def add_board(self, board_name):
        self.boards[board_name] = Counter()

    def add_cards(self, board, *cards):
        for card in cards:
            r_card, count = card, 1
            if isinstance(card, (tuple, list)):
                r_card, count = card
            self.boards[board][r_card] += count
        self.call_listeners()

    def add_cards_by_mvid(self, board, *mvids):
        cards = []
        for mvid in mvids:
            if isinstance(mvid, (tuple, list)):
                r_mvid, count = mvid
                cards.append((Cards.find_by_mvid(r_mvid), count))
        self.add_cards(board, *cards)

    def remove_cards(self, board, *cards):
        for card in cards:
            r_card, count = card, 1
            if isinstance(card, (tuple, list)):
                r_card, count = card
            self.boards[board][r_card] += count

            if self.boards[board][r_card] <= 0:
                del self.boards[board][r_card]
        self.call_listeners()

    def remove_cards_by_mvid(self, board, *mvids):
        cards = []
        for mvid in mvids:
            if isinstance(mvid, (tuple, list)):
                r_mvid, count = mvid
                cards.append((Cards.find_by_mvid(r_mvid), count))
        self.remove_cards(board, *cards)

    def get_board(self, board):
        return self.boards[board]

    def get_board_counts(self):
        return ((board, sum(cards.values())) for board, cards in self.boards.items())

    def get_sorted(self, key=Cards.default_sort_key):
        res = {}
        for board, cards in self.boards.items():
            res[board] = sorted(cards.items(), key=lambda x: key(x[0]))
        return res

    def format_count(self, name, board='Main'):
        return str(sum(count for _, count in self.get_matching_cards(name, board)))

    def get_matching_cards(self, name, board):
        return ((card, count)
                for card, count
                in self.boards[board].items()
                if card.name == name)

    def get_all_counts(self, name):
        return {board: self.format_count(name, board) for board in self.boards}

    def register_listener(self, callback):
        self.listeners.add(WeakMethod(callback))

    def call_listeners(self):
        dead_listeners = set()
        for listener in self.listeners:
            call = listener()
            if call is None:
                dead_listeners.add(listener)
            else:
                call(self)
        self.listeners -= dead_listeners

    @staticmethod
    def import_dec(fname):
        """
        Returns a Deck
        """
        boards = defaultdict(list)
        with open(fname, encoding='utf-8') as dec_file:
            comment = True
            for line in dec_file:
                try:
                    if comment:
                        line = line.strip()
                        mvid = int(split_and_cut(line, 'mvid:', 1, ' ', 0))
                        qty = int(split_and_cut(line, 'qty:', 1, ' ', 0))
                        loc = split_and_cut(line, 'loc:', 1, ' ', 0)
                        if loc == 'Deck':
                            loc = 'Main'
                        elif loc == 'SB':
                            loc = 'Sideboard'
                        boards[loc].append((mvid, qty))
                except Exception as e:
                    print("Failed to parse line")
                    print(line)
                    print(e)
                comment = not comment
        trimmed_fname = split_and_cut(fname, '/', -1, '.dec', 0)
        deck = Deck(name=trimmed_fname, file_location=fname)
        for board, cards in boards.items():
            deck.add_cards_by_mvid(board, *cards)
        return deck

    def export_dec(self, fname=None, decked_compatible=False):
        """
        Saves a dec file at fname with all the ids translated into cards
        """
        if fname is None:
            fname = self.file_location

        boards = self.get_sorted(lambda x: x['name'])
        res = []
        for board, cards in sorted(boards.items()):
            if decked_compatible:
                if board == 'Main':
                    board = 'Deck'
                if board == 'Sideboard':
                    board = 'SB'

            for card, qty in cards:
                res.append("///mvid:{0:} qty:{1:} name:{2:} loc:{3:}\n{4:}{1:} {2:}"
                           .format(card['multiverse_id'], qty, card['name'], board,
                                   'SB:' if board == 'SB' or board == 'Sideboard' else ''))
        with open(fname, 'w', encoding='utf-8') as out_file:
            out_file.write('\n'.join(res))


def rough_type(card):
    if 'Land' in card['types']:
        return 2
    elif 'Creature' in card['types']:
        return 0
    else:
        return 1


def full_type(card):
    if 'Land' in card['types']:
        return 6
    elif 'Creature' in card['types']:
        return 0
    elif 'Artifact' in card['types']:
        return 1
    elif 'Enchantment' in card['types']:
        return 2
    elif 'Sorcery' in card['types']:
        return 3
    elif 'Instant' in card['types']:
        return 4
    elif 'Planeswalker' in card['types']:
        return 5
    else:
        return 7


def color_identity_key(x):
    color_list = ['W', 'U', 'B', 'R', 'G']
    if x['color_identity'] is None:
        return (0, [], Cards.default_sort_key(x))
    int_colors = sorted(color_list.index(c) for c in x['color_identity'])
    return (len(int_colors), int_colors, Cards.default_sort_key(x))


class SortSelector(Button):
    sort_methods = \
        {
            'Creature/Spell/Land': lambda x: (rough_type(x), Cards.default_sort_key(x)),
            'CMC': Cards.default_sort_key,
            'Name': lambda x: x['name'],
            'Type': lambda x: (full_type(x), Cards.default_sort_key(x)),
            'Color Identity': lambda x: (color_identity_key(x), Cards.default_sort_key(x)),
            'Rarity': lambda x: (x['rarity'], Cards.default_sort_key(x)),
            'Set Name': lambda x: (x['set_name'], Cards.default_sort_key(x))
        }
    screen = ObjectProperty(None, allownone=True)
    prefix = 'Sort By: '

    def __init__(self, **kwargs):
        super(SortSelector, self).__init__(**kwargs)
        self.text = self.prefix + 'CMC'

        self.drop_list = DropDown()
        for conn in sorted(self.sort_methods):
            btn = Button(text=conn, size_hint_y=None, height=dp(30))
            btn.bind(on_release=lambda btn: self.drop_list.select(btn.text))
            btn.font_size = sp(16)
            self.drop_list.add_widget(btn)

        self.bind(on_release=self.drop_list.open)

        self.drop_list.bind(on_select=self.drop_select)

    def drop_select(self, instance, text):
        setattr(self, 'text', self.prefix + text)
        if self.screen is not None:
            self.screen.update_deck(self.screen.deck, save=False)

    def get_sort(self):
        return self.sort_methods[self.text[len(self.prefix):]]


class Board(BoxLayout):
    title = StringProperty()

    screen = ObjectProperty()

    def __init__(self, cards, board='Main', **kwargs):
        self.board = board
        self.cache = []
        super(Board, self).__init__(**kwargs)
        self.bind(minimum_height=self.setter('height'))

    @mainthread
    def update_cards(self, cards):
        for card, _ in cards[len(self.cache):]:
            card_widget = CardResult(board=self.board, size_hint=(1, None))
            card_widget.screen = self.screen
            self.add_widget(card_widget)
            self.cache.append(card_widget)

        for cached in self.cache[len(cards):][::-1]:
            self.remove_widget(cached)
        self.cache = self.cache[:len(cards)]

        for cached, (card, _) in zip(self.cache, cards):
            cached.refresh_view_attrs(None, None, card)

        self.update_title(cards)

    @mainthread
    def update_title(self, cards):
        self.title = '{}: {}'.format(self.board, sum(qty for c, qty in cards))


class DeckScreen(Screen):
    deck = ObjectProperty()

    counts = StringProperty()
    deck_name = StringProperty()
    deck_location = StringProperty(allownone=True)

    inner_layout = ObjectProperty()
    sort_sel = ObjectProperty()

    def __init__(self, deck_name=None, **kwargs):
        self.created_widgets = []
        cached_deck_name = DefaultConfiguration.last_deck
        self.bind_inner = True
        self.register_listener = True
        self.boards = {}
        if deck_name is not None:
            self.load_deck(deck_name)
        elif cached_deck_name is not None and os.path.exists(cached_deck_name):
            self.load_deck(cached_deck_name)
        else:
            self.load_deck(None)
        super(DeckScreen, self).__init__(**kwargs)

    def load_deck(self, deck_location):
        if deck_location == self.deck_location:
            return

        if deck_location is None:
            self.deck = Deck()
        elif not os.path.exists(deck_location):
            display_name = split_and_cut(deck_location, '/', -1, '\\', -1, '.dec', 0)
            self.deck = Deck(display_name, deck_location)
        else:
            self.deck = Deck.import_dec(deck_location)
        self.deck_name = self.deck.name
        self.deck_location = self.deck.file_location
        DefaultConfiguration.current_deck = self.deck
        DefaultConfiguration.last_deck = self.deck.file_location
        self.deck.register_listener(self.update_deck)
        if self.register_listener:
            DefaultConfiguration.register_listener('last_deck', self.load_deck)
            self.register_listener = False
        self.update_deck(self.deck, save=False)

    def update_deck(self, deck, save=True, *args):
        self.deck = deck
        self.counts = ' '.join('{} {}'.format(board, count) for board, count in sorted(deck.get_board_counts()))
        self.deck_name = deck.name
        if save:
            deck.export_dec()
        self.update_boards()

    def on_enter(self, *args):
        DefaultConfiguration.last_screen = "Deck"
        super(DeckScreen, self).on_enter(*args)

    @mainthread
    def update_boards(self, *args):
        boards = sorted(self.deck.get_sorted(key=self.sort_sel.get_sort()).items())
        for name, cards in boards:
            board = self.boards.get(name, None)
            if board is None:
                board = self.boards[name] = Board(cards, name)
                board.screen = self
                self.inner_layout.add_widget(board)
            board.update_cards(cards)

    @mainthread
    def on_inner_layout(self, instance, value):
        if self.bind_inner:
            self.inner_layout.bind(minimum_height=self.inner_layout.setter('height'))
            self.bind_inner = False
