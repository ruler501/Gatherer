from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen

from cards import CardScreen
from configuration import DefaultConfiguration
from search import SearchScreen
from utils import Gradient


class CardResult(BoxLayout, RecycleDataViewBehavior):
    name = StringProperty('')
    image_url = StringProperty('')
    power = StringProperty('', allownone=True)
    toughness = StringProperty('', allownone=True)
    mana_cost = StringProperty('', allownone=True)
    set_name = StringProperty('')
    type_line = StringProperty('')
    full_type_line = StringProperty('')
    card = ObjectProperty()
    mana_render = ObjectProperty()
    back_texture = ObjectProperty(Gradient.horizontal([148, 162, 173, 255]))
    color_identity = ObjectProperty(allownone=True)

    image = ObjectProperty()

    count = StringProperty()

    def refresh_view_attrs(self, rv, index, data):
        """Catch and handle the view changes"""
        self.card = data
        self.refresh_count(DefaultConfiguration.current_deck)
        DefaultConfiguration.register_listener('current_deck', self.refresh_count)
        return super(CardResult, self).refresh_view_attrs(
            rv, index, data)

    def refresh_count(self, current_deck):
        if current_deck is not None:
            self.count = current_deck.format_count(self.card['name'])

    def set_back_texture(self, colors):
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
            color_vals = [colorlookup[colors[0]]]
        elif len(colors) > 1:
            color_vals = [colorlookup[x] for x in sorted(colors, key=color_order.index)]

        self.back_texture = Gradient.horizontal(*color_vals)

    def create_type_line(self):
        res = self.type_line
        if 'Creature' in res or 'Vehicle' in res:
            res += ' {}/{}'.format(self.power, self.toughness)
        self.full_type_line = res

    def on_type_line(self, instance, value):
        self.create_type_line()

    def on_power(self, instance, value):
        self.create_type_line()

    def on_toughness(self, instance, value):
        self.create_type_line()

    def on_color_identity(self, instance, value):
        self.set_back_texture(value)

    def on_touch_down(self, touch):
        if self.image.collide_point(*touch.pos):
            rv = self.parent.parent
            sc = rv.parent.parent
            sc.manager.add_widget(CardScreen(self.card, name=self.card['name']))
            sc.manager.current = self.card['name']


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
        self.manager.add_widget(SearchScreen(name="Search"))
        self.manager.current = "Search"
        self.manager.remove_widget(self)


class ResultPage(RecycleView):
    def __init__(self, data=[], **kwargs):
        super(ResultPage, self).__init__(**kwargs)
        self.data = list(data)
