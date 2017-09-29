from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen

from mtgworkshop.cards import CardScreen
from mtgworkshop.configuration import DefaultConfiguration
from mtgworkshop.utils import Gradient


class CardResult(BoxLayout, RecycleDataViewBehavior):
    name = StringProperty()
    image_url = StringProperty()
    power = ObjectProperty(allownone=True)
    toughness = ObjectProperty(allownone=True)
    mana_cost = StringProperty(allownone=True)
    set_name = StringProperty()
    type_line = StringProperty()
    rarity = StringProperty()
    life = NumericProperty(None, allownone=True)
    hand = NumericProperty(None, allownone=True)

    card = ObjectProperty()
    mana_render = ObjectProperty()
    back_texture = ObjectProperty(Gradient.horizontal([148, 162, 173, 255]))
    color_identity = ObjectProperty(allownone=True)

    image = ObjectProperty()
    screen = ObjectProperty(None, allownone=True)

    full_type_line = StringProperty('')
    count = StringProperty()
    board = StringProperty('Main')

    def __init__(self, board='Main', **kwargs):
        self.registered_listener = False
        self.board = board
        super(CardResult, self).__init__(**kwargs)

    def refresh_view_attrs(self, rv, index, data):
        """Catch and handle the view changes"""
        self.card = data
        super(CardResult, self).refresh_view_attrs(
            rv, index, data)
        if rv is not None:
            self.screen = rv.parent.parent
        self.refresh_count(DefaultConfiguration.current_deck)
        if not self.registered_listener:
            DefaultConfiguration.register_listener('current_deck', self.refresh_count)
            DefaultConfiguration.current_deck.register_listener(self.refresh_count)
            self.registered_listener = True

    def refresh_count(self, current_deck):
        if current_deck is not None:
            self.count = current_deck.format_count(self.card['name'], self.board)

    def create_type_line(self):
        res = self.type_line
        if self.power is not None and self.toughness is not None:
            res += ' {}/{}'.format(self.power, self.toughness)
        if self.life is not None and self.hand is not None:
            res += ' {}/{}'.format(int(self.life), int(self.hand))
        self.full_type_line = res

    def on_type_line(self, instance, value):
        self.create_type_line()

    def on_power(self, instance, value):
        self.create_type_line()

    def on_toughness(self, instance, value):
        self.create_type_line()

    def on_color_identity(self, instance, colors):
        colorlookup = \
            {
                'W': [211, 199, 183, 255],
                'U': [11, 136, 201, 255],
                'B': [92, 93, 96, 255],
                'R': [167, 46, 8, 255],
                'G': [66, 112, 76, 255],
                'Gold': [221, 193, 130, 255],
                'Colorless': [148, 162, 173, 255]
            }
        color_order = ['W', 'U', 'B', 'R', 'G']

        color_vals = [colorlookup['Colorless']]
        if colors is None or len(colors) == 0:
            color_vals = [colorlookup['Colorless']]
        elif len(colors) == 1:
            color, *_ = colors
            color_vals = [colorlookup[color]]
        elif len(colors) > 1:
            color_vals = [colorlookup[x] for x in sorted(colors, key=color_order.index)]

        self.back_texture = Gradient.horizontal(*color_vals)

    def on_life(self, instance, value):
        self.create_type_line()

    def on_hand(self, instance, value):
        self.create_type_line()

    def on_touch_down(self, touch):
        if self.image.collide_point(*touch.pos) and self.screen is not None:
            manager = self.screen.parent
            manager.add_widget(CardScreen(self.card, self.screen.name, name=self.card['name']))
            manager.current = self.card['name']


class ResultsScreen(Screen):
    b_layout = ObjectProperty()
    results = ObjectProperty()
    back_button = ObjectProperty()

    def __init__(self, cards, **kwargs):
        super(ResultsScreen, self).__init__(**kwargs)
        self.b_layout = BoxLayout(orientation='vertical')
        self.back_button = Button(text='Search Again', on_release=self.new_search,
                                  size_hint=(1, 0.1))
        self.results = ResultPage(cards, size_hint=(1, 0.9))
        self.b_layout.add_widget(self.back_button)
        self.b_layout.add_widget(self.results)
        self.add_widget(self.b_layout)
        DefaultConfiguration.last_screen = "Results"

    def new_search(self, *args):
        manager = self.parent
        manager.current = "Search"
        manager.remove_widget(self)


class ResultPage(RecycleView):
    def __init__(self, data=[], **kwargs):
        super(ResultPage, self).__init__(**kwargs)
        self.data = list(data)
