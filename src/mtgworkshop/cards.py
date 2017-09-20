from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

from configuration import DefaultConfiguration


class CardScreen(Screen):
    card = ObjectProperty()
    rulings_box = ObjectProperty()
    inner_layout = ObjectProperty()

    name = StringProperty()
    image_url = StringProperty()
    power = StringProperty(allownone=True)
    toughness = StringProperty(allownone=True)
    mana_cost = StringProperty(allownone=True)
    set_name = StringProperty()
    type_line = StringProperty()
    rarity = StringProperty()
    text = StringProperty(allownone=True)
    flavor = StringProperty(allownone=True)
    rulings = ObjectProperty(allownone=True)
    main_count = StringProperty('-')
    side_count = StringProperty('-')

    power_tough = StringProperty()

    def __init__(self, card, **kwargs):
        super(CardScreen, self).__init__(**kwargs)
        self.card = card
        self.update_deck(DefaultConfiguration.current_deck)

        for key, val in card.items():
            setattr(self, key, val)

    def update_deck(self, deck):
        if deck is None:
            self.main_count = '-'
            self.side_count = '-'
            return

        self.update_counts(deck)
        deck.register_listener(self.update_counts)

    def update_counts(self, deck):
        if deck is None:
            return

        board_counts = deck.get_all_counts(self.name)

        self.main_count = '{} Main'.format(board_counts['Main'])
        self.side_count = '{} Side'.format(board_counts['Sideboard'])

    def on_inner_layout(self, instance, value):
        self.inner_layout.bind(minimum_height=self.inner_layout.setter('height'))

    def create_power_tough(self):
        if 'Creature' in self.type_line or 'Vehicle' in self.type_line:
            self.power_tough = '{}/{}'.format(self.power, self.toughness)

    def on_power(self, instance, value):
        self.create_power_tough()

    def on_toughness(self, instance, value):
        self.create_power_tough()

    def on_rulings(self, instance, value):
        if value is None:
            return

        self.rulings_box.clear_widgets()
        for rule in value:
            t_label = RulingsBox(rule['date'], rule['text'])
            self.rulings_box.add_widget(t_label)
        self.rulings_box.height = 60 * len(value)

    def to_results(self):
        self.manager.current = DefaultConfiguration.last_screen
        self.manager.remove_widget(self)

    def add_card(self, board):
        current_deck = DefaultConfiguration.current_deck
        if current_deck is None:
            return
        current_deck.add_cards(board, self.card)

    def remove_card(self, board):
        current_deck = DefaultConfiguration.current_deck
        if current_deck is None:
            return
        current_deck.remove_cards(board, self.card)


class RulingsBox(BoxLayout):
    date = StringProperty()
    text = StringProperty()

    date_label = ObjectProperty()
    text_label = ObjectProperty()

    def __init__(self, date, text, **kwargs):
        super(RulingsBox, self).__init__(**kwargs)
        self.date = date
        self.text = text
