from kivy.app import App
from kivy.core.window import Window
from kivy.garden.androidtabs import AndroidTabsBase
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView

from magic_db import Cards


class SearchScreen(Screen):
    pass


class NegateSelector(BoxLayout):
    use_not = BooleanProperty(False)

    def set_use_not(self, value):
        self.use_not = value


class OperationSelector(Button):
    operations = \
        {
            'Equals': 'where',
            'Contains': 'where_contains',
            'Regex Match': 'where_matches'
        }

    def __init__(self, **kwargs):
        super(OperationSelector, self).__init__(**kwargs)
        self.text = 'Contains'
        self.font_size = 16

        self.drop_list = DropDown()
        for op in self.operations:
            btn = Button(text=op, size_hint_y=None, height=32)
            btn.bind(on_release=lambda btn: self.drop_list.select(btn.text))
            btn.font_size = 16
            self.drop_list.add_widget(btn)

        self.bind(on_release=self.drop_list.open)

        self.drop_list.bind(on_select=lambda instance, x: setattr(self, 'text', x))

    def get_operation(self):
        return self.operations[self.text]


class ConnectorSelector(Button):
    connectors = \
        {
            'And': 'use_and',
            'Or': 'use_or'
        }

    def __init__(self, **kwargs):
        super(ConnectorSelector, self).__init__(**kwargs)
        self.text = 'And'

        self.drop_list = DropDown()
        for conn in self.connectors:
            btn = Button(text=conn, size_hint_y=None, height=30)
            btn.bind(on_release=lambda btn: self.drop_list.select(btn.text))
            btn.font_size = 16
            self.drop_list.add_widget(btn)

        self.bind(on_release=self.drop_list.open)

        self.drop_list.bind(on_select=lambda instance, x: setattr(self, 'text', x))

    def get_connector(self):
        return self.connectors[self.text]


class FieldSelector(Button):
    fields = ['Text', 'Type Line', 'Name', 'Toughness', 'Flavor', 'Loyalty', 'Artist', 'Rarity',
              'Set Name', 'CMC', 'Color Identity', 'Original Text', 'Original Type']

    def __init__(self, **kwargs):
        super(FieldSelector, self).__init__(**kwargs)
        self.text = 'Text'

        self.drop_list = DropDown()
        for field in self.fields:
            btn = Button(text=field, size_hint_y=None, height=30)
            btn.bind(on_release=lambda btn: self.drop_list.select(btn.text))
            btn.font_size = 16
            self.drop_list.add_widget(btn)

        self.bind(on_release=self.drop_list.open)

        self.drop_list.bind(on_select=lambda instance, x: setattr(self, 'text', x))
        # setattr(getattr(self, 'parent'), 'field', self.get_field())

    def get_field(self):
        return self.text.lower().replace(' ', '_')


class FieldInput(BoxLayout):
    op_sel = ObjectProperty()
    conn_sel = ObjectProperty()
    field_sel = ObjectProperty()
    text_sel = ObjectProperty()
    neg_sel = ObjectProperty()

    def remove_row(self):
        self.parent.parent.remove_row(self)

    def update_query(self, i, query):
        if len(self.text_sel.text) == 0:
            return query
        if i > 0:
            query = getattr(query, self.conn_sel.get_connector())()
        if self.neg_sel.use_not:
            query = query.negated()
        kwargs = {self.field_sel.get_field(): self.text_sel.text}
        query = getattr(query, self.op_sel.get_operation())(**kwargs)
        return query


class SearchFields(ScrollView):
    inner_layout = ObjectProperty()

    def on_inner_layout(self, instance, value):
        self.inner_layout.bind(minimum_height=self.inner_layout.setter('height'))
        self.add_row()

    def add_row(self):
        row = FieldInput()
        self.inner_layout.add_widget(row)

    def remove_row(self, view):
        self.inner_layout.remove_widget(view)

    def perform_search(self):
        query = Cards.CardsQuery()
        for i, child in enumerate(self.inner_layout.children):
            query = child.update_query(i, query)

        cards = query.find_all()
        next_page = ResultScreen(cards, name="Results")
        self.parent.parent.manager.add_widget(next_page)
        self.parent.parent.manager.current = 'Results'
        self.parent.parent.manager.remove_widget(self.parent.parent)


class ManaCost(RelativeLayout):
    symbols = ['W', 'U', 'B', 'R', 'G', 'C', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
    mana_cost = StringProperty('', allownone=True)
    MANA_SIZE = 18

    def on_mana_cost(self, instance, value):
        self.clear_widgets()
        if value is None:
            return
        mana_cost = value.replace('{', '').split('}')
        count = 0
        for m in mana_cost:
            m = str(m)
            if len(m) == 0:
                continue
            if m in self.symbols:
                self.add_widget(AsyncImage(source=m + '.png',
                                           width=self.MANA_SIZE,
                                           allow_stretch=True,
                                           keep_ratio=True,
                                           size_hint=(None, None),
                                           pos=(self.MANA_SIZE * 1.1 * count, -self.MANA_SIZE / 2 - 5)))
                count += 1
            else:
                self.add_widget(Label(text=m, color=[0, 0, 0, 1], size=(32, 32), pos=(36 * count, 0)))
                count += 1


class CardResult(BoxLayout, RecycleDataViewBehavior):
    name = StringProperty('')
    image_url = StringProperty('')
    power = StringProperty('', allownone=True)
    toughness = StringProperty('', allownone=True)
    mana_cost = StringProperty('', allownone=True)
    set_name = StringProperty('')
    type_line = StringProperty('')
    full_type_line = StringProperty('')
    index = None
    card = ObjectProperty()
    mana_render = ObjectProperty()
    back_col = ListProperty([171 / 255.0, 196 / 255.0, 210 / 255.0, 0.6])
    color_identity = ObjectProperty(allownone=True)
    image = ObjectProperty()

    def refresh_view_attrs(self, rv, index, data):
        """Catch and handle the view changes"""
        self.index = index
        self.card = data
        return super(CardResult, self).refresh_view_attrs(
            rv, index, data)
        self.mana_cost = data['mana_cost']

    def set_back_col(self, colors):
        colorlookup = \
            {
                'W': [211 / 255.0, 199 / 255.0, 183 / 255.0, 0.6],
                'U': [11 / 255.0, 136 / 255.0, 201 / 255.0, 0.6],
                'B': [92 / 255.0, 93 / 255.0, 96 / 255.0, 0.6],
                'R': [138 / 255.0, 38 / 255.0, 6 / 255.0, 0.6],
                'G': [66 / 255.0, 112 / 255.0, 76 / 255.0, 0.6],
                'Gold': [221 / 255.0, 193 / 255.0, 130 / 255.0, 0.6],
                'Colorless': [171 / 255.0, 196 / 255.0, 210 / 255.0, 0.6]
            }
        if colors is None:
            self.back_col = colorlookup['Colorless']
            return None

        if len(colors) == 1:
            self.back_col = colorlookup[colors[0]]
        elif len(colors) > 1:
            self.back_col = colorlookup['Gold']
        else:
            self.back_col = colorlookup['Colorless']

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

    def on_mana_cost(self, instance, value):
        self.mana_render.mana_cost = value

    def on_color_identity(self, instance, value):
        self.set_back_col(value)

    def on_touch_down(self, touch):
        if self.image.collide_point(*touch.pos):
            rv = self.parent.parent
            sc = rv.parent.parent
            sc.manager.add_widget(CardScreen(self.card, name=self.card['name']))
            sc.manager.current = self.card['name']


class ResultScreen(Screen):
    b_layout = ObjectProperty()
    results = ObjectProperty()
    back_button = ObjectProperty()

    def __init__(self, cards, **kwargs):
        super(ResultScreen, self).__init__(**kwargs)
        self.b_layout = BoxLayout(orientation='vertical')
        self.back_button = Button(text='Search Again', on_release=self.new_search,
                                  size_hint=(1, 0.1))
        self.results = ResultPage(cards, size_hint=(1, 0.9))
        self.b_layout.add_widget(self.back_button)
        self.b_layout.add_widget(self.results)
        self.add_widget(self.b_layout)

    def new_search(self, *args):
        self.manager.add_widget(SearchScreen(name="Search"))
        self.manager.current = "Search"
        self.manager.remove_widget(self)


class ResultPage(RecycleView):
    def __init__(self, data, **kwargs):
        super(ResultPage, self).__init__(**kwargs)
        self.data = list(data)


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
    text = StringProperty()
    rulings = ObjectProperty(allownone=True)

    power_tough = StringProperty()

    def __init__(self, card, **kwargs):
        super(CardScreen, self).__init__(**kwargs)
        self.size = Window.size
        self.card = card
        for key, val in card.items():
            setattr(self, key, val)
        print('screen', self.size)

    def on_inner_layout(self, instance, value):
        self.inner_layout.bind(minimum_height=self.inner_layout.setter('height'))
        print('inner_layout.parent', self.inner_layout.parent.size)

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
        print("Going to results")
        self.manager.current = 'Results'
        self.manager.remove_widget(self)


class RulingsBox(BoxLayout):
    date = StringProperty()
    text = StringProperty()

    date_label = ObjectProperty()
    text_label = ObjectProperty()

    def __init__(self, date, text, **kwargs):
        super(RulingsBox, self).__init__(**kwargs)
        self.date = date
        self.text = text


class MultiLineLabel(Label):
    def __init__(self, **kwargs):
        super(MultiLineLabel, self).__init__(**kwargs)
        self.text_size = self.size
        self.bind(size=self.on_size)
        self.bind(text=self.on_text_changed)
        self.size_hint_y = None  # Not needed here

    def on_size(self, widget, size):
        self.text_size = size[0], None
        self.texture_update()
        if self.size_hint_y is None and self.size_hint_x is not None:
            self.height = max(self.texture_size[1], self.line_height)
        elif self.size_hint_x is None and self.size_hint_y is not None:
            self.width = self.texture_size[0]

    def on_text_changed(self, widget, text):
        self.on_size(self, self.size)


class MyTab(BoxLayout, AndroidTabsBase):
    pass


class SearchApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(SearchScreen(name="Search"))
        return sm


if __name__ == '__main__':
    Window.clearcolor = [0.6, 0.6, 0.6, 1]
    SearchApp().run()
