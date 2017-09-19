import os

from collections import Counter, defaultdict
from weakref import WeakMethod

from kivy.clock import mainthread
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from configuration import DefaultConfiguration
from magic_db import Cards
from utils import split_and_cut


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
        self.add_cards_by_mvid(board, *(card['multiverse_id'] for card in cards))

    def add_cards_by_mvid(self, board, *mvids):
        for mvid in mvids:
            r_mvid, count = mvid, 1
            if isinstance(mvid, (tuple, list)):
                r_mvid, count = mvid
            self.boards[board][r_mvid] += count
        self.call_listeners()

    def remove_cards(self, board, *cards):
        self.remove_cards_by_mvid(board, *(card['multiverse_id'] for card in cards))

    def remove_cards_by_mvid(self, board, *mvids):
        for mvid in mvids:
            r_mvid, count = mvid, 1
            if isinstance(mvid, (tuple, list)):
                r_mvid, count = mvid
            self.boards[board][r_mvid] -= count

            if self.boards[board][r_mvid] <= 0:
                del self.boards[board][r_mvid]

        self.call_listeners()

    def get_board(self, board):
        return self.boards[board]

    def get_board_counts(self):
        return ((board, sum(cards.values())) for board, cards in self.boards.items())

    def get_sorted(self, key=Cards.default_sort_key):
        res = {}
        for board, cards in self.boards.items():
            card_objects = ((Cards.find_by_mvid(card), count) for card, count in cards.items())
            res[board] = sorted(card_objects, key=lambda x: key(x[0]))
        return res

    def format_count(self, name, board='Main'):
        return str(sum(count for _, count in self.get_matching_cards(name, board)))

    def get_matching_cards(self, name, board):
        return ((card, count)
                for card, count
                in self.boards[board].items()
                if Cards.find_by_mvid(card)['name'] == name)

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
        trimmed_fname = split_and_cut(fname, '/', -1, '.dec', 0)
        deck = Deck(name=trimmed_fname, file_location=fname)
        with open(fname) as dec_file:
            comment = True
            for line in dec_file:
                if comment:
                    line = line.strip()
                    mvid = int(split_and_cut(line, 'mvid:', 1, ' ', 0))
                    qty = int(split_and_cut(line, 'qty:', 1, ' ', 0))
                    loc = split_and_cut(line, 'loc:', 1, ' ', 0)
                    if loc == 'Deck':
                        loc = 'Main'
                    elif loc == 'SB':
                        loc = 'Sideboard'
                    deck.add_cards_by_mvid(loc, (mvid, qty))
                comment = not comment
        return deck

    def export_dec(self, fname=None, decked_compatible=False):
        """
        Saves a dec file at fname with all the ids translated into cards
        """
        if fname is None:
            fname = self.file_location

        boards = self.get_sorted(lambda x: x[0]['name'])
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
                                   '' if not decked_compatible else 'SB:' if board == 'SB' else ''))
        with open(fname, 'w') as out_file:
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


class SortSelector(Button):
    sort_methods = \
        {
            'Creature/Spell/Land': lambda x: (rough_type(x), Cards.default_sort_key(x)),
            'CMC': Cards.default_sort_key,
            'Name': lambda x: x['name'],
            'Type': lambda x: (full_type(x), Cards.default_sort_key(x)),
            'Color Identity': lambda x: ([] if x['color_identity'] is None else
                                         sorted(x['color_identity'],
                                                key=lambda x: ['W', 'U', 'B', 'R', 'G'].index(x)),
                                         Cards.default_sort_key(x)),
            'Rarity': lambda x: (x['rarity'], Cards.default_sort_key(x)),
            'Set Name': lambda x: (x['set_name'], Cards.default_sort_key(x))
        }
    screen = ObjectProperty()

    def __init__(self, **kwargs):
        super(SortSelector, self).__init__(**kwargs)
        self.text = 'CMC'

        self.drop_list = DropDown()
        for conn in self.sort_methods:
            btn = Button(text=conn, size_hint_y=None, height=30)
            btn.bind(on_release=lambda btn: self.drop_list.select(btn.text))
            btn.font_size = 16
            self.drop_list.add_widget(btn)

        self.bind(on_release=self.drop_list.open)

        self.drop_list.bind(on_select=self.drop_select)

    def drop_select(self, instance, text):
        setattr(self, 'text', text)
        self.screen.update_deck(self.screen.deck, save=False)

    def get_sort(self):
        return self.sort_methods[self.text]


class DeckScreen(Screen):
    deck = ObjectProperty()

    counts = StringProperty()
    deck_name = StringProperty()

    inner_layout = ObjectProperty()
    sort_sel = ObjectProperty()

    def __init__(self, deck_name=None, **kwargs):
        self.created_widgets = []
        cached_deck_name = DefaultConfiguration.last_deck
        if deck_name is not None:
            self.load_deck(deck_name)
        elif cached_deck_name is not None and os.path.exists(cached_deck_name):
            self.load_deck(cached_deck_name)
        else:
            self.load_deck(None)
        DefaultConfiguration.register_listener('last_deck', self.load_deck)
        super(DeckScreen, self).__init__(**kwargs)

    def load_deck(self, deck_name):
        if deck_name is None:
            self.deck = Deck()
        else:
            self.deck = Deck.import_dec(deck_name)
        DefaultConfiguration.current_deck = self.deck
        self.deck.register_listener(self.update_deck)
        self.update_deck(self.deck, save=False)

    def update_deck(self, deck, save=True):
        self.deck = deck
        self.counts = ' '.join('{} {}'.format(board, count) for board, count in sorted(deck.get_board_counts()))
        self.deck_name = deck.name
        if save:
            deck.export_dec()
        if self.inner_layout is not None:
            self.on_inner_layout(None, self.inner_layout)

    def on_enter(self, *args):
        DefaultConfiguration.last_screen = "Deck"
        DefaultConfiguration.last_deck = self.deck.file_location
        super(DeckScreen, self).on_enter(*args)

    @mainthread
    def on_inner_layout(self, instance, value):
        self.inner_layout.bind(minimum_height=self.inner_layout.setter('height'))
        from results import CardResult
        if value is None:
            return

        for widget in self.created_widgets:
            self.inner_layout.remove_widget(widget)
        self.created_widgets = []

        for board, cards in sorted(self.deck.get_sorted(key=self.sort_sel.get_sort()).items()):
            label = BoardLabel(text=board)
            self.inner_layout.add_widget(label)
            self.created_widgets.append(label)

            for card, qty in cards:
                card_widget = CardResult(board=board, size_hint=(1, None))
                card_widget.refresh_view_attrs(None, None, card)
                self.inner_layout.add_widget(card_widget)
                self.created_widgets.append(card_widget)


class BoardLabel(Label):
    pass
