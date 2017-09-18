import os

from collections import Counter, defaultdict

from kivy.properties import ObjectProperty, StringProperty
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
        self.add_cards_by_mvid(self, board, *(card['multiverse_id'] for card in cards))

    def add_cards_by_mvid(self, board, *mvids):
        for mvid in mvids:
            if isinstance(mvids, (tuple, list)):
                self.boards[board][mvid[0]] += mvid[1]
            else:
                self.boards[board][mvid] += 1

    def get_board(self, board):
        return self.boards[board]

    def get_board_counts(self):
        return ((board, sum(cards.values())) for board, cards in self.boards.items())

    def get_sorted(self,
                   search_key=lambda x: Cards.default_sort_key(x[0])):
        res = {}
        for key, value in self.boards.items():
            res[key] = sorted(((Cards.find_by_mvid(x), y) for x, y in value.items()),
                              key=search_key)
        return res

    def format_count(self, name):
        return str(sum(count
                       for card, count
                       in self.boards['Main'].items()
                       if Cards.find_by_mvid(card)['name'] == name))

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
                    mvid = split_and_cut(line, 'mvid:', 1, ' ', 0)
                    qty = int(split_and_cut(line, 'qty:', 1, ' ', 0))
                    loc = split_and_cut(line, 'loc:', 1, ' ', 0)
                    if loc == 'Deck':
                        loc = 'Main'
                    elif loc == 'SB':
                        loc = 'Sideboard'
                    deck.add_cards_by_mvid(loc, (mvid, qty))
                comment = not comment
        return deck

    @staticmethod
    def export_dec(deck, fname, decked_compatible=False):
        """
        Saves a dec file at fname with all the ids translated into cards
        """
        boards = deck.get_sorted(lambda x: Cards.find_by_mvid(x[0])['name'])
        res = []
        for board, cards in sorted(boards.items()):
            if decked_compatible:
                if board == 'Main':
                    board = 'Deck'
                if board == 'Sideboard':
                    board = 'SB'

            for mvid, qty in cards:
                res.append("///mvid:{0:} qty:{1:} name:{2:} loc:{3:}\n{4:}{1:} {2:}"
                           .format(mvid, qty, Cards.find_by_mvid(mvid)['name']), board,
                           '' if not decked_compatible else 'SB:' if board == 'SB' else '')
        with open(fname, 'w') as out_file:
            out_file.write('\n'.join(res))
        return res


class DeckScreen(Screen):
    deck = ObjectProperty()

    counts = StringProperty()
    deck_name = StringProperty()

    inner_layout = ObjectProperty()

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

        self.counts = ' '.join('{} {}'.format(deck, count) for deck, count in sorted(self.deck.get_board_counts()))
        self.deck_name = self.deck.name
        if self.inner_layout is not None:
            self.on_inner_layout(None, self.inner_layout)

    def on_enter(self, *args):
        DefaultConfiguration.last_screen = "Deck"
        DefaultConfiguration.current_deck = self.deck
        DefaultConfiguration.last_deck = self.deck.file_location
        super(DeckScreen, self).on_enter(*args)

    def on_inner_layout(self, instance, value):
        self.inner_layout.bind(minimum_height=self.inner_layout.setter('height'))
        from results import CardResult
        if value is None:
            return

        for widget in self.created_widgets:
            self.inner_layout.remove_widget(widget)
        self.created_widgets = []

        for board, cards in sorted(self.deck.get_sorted().items()):
            label = BoardLabel(text=board)
            self.inner_layout.add_widget(label)
            self.created_widgets.append(label)

            for card, qty in cards:
                card_widget = CardResult(size_hint=(1, None))
                card_widget.refresh_view_attrs(None, None, card)
                self.inner_layout.add_widget(card_widget)
                self.created_widgets.append(card_widget)


class BoardLabel(Label):
    pass
