from kivy.app import App
from kivy.core.window import Window
from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.recycleview import RecycleView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from magic_db import Cards


class SearchScreen(Screen):
    pass


class ResultScreen(Screen):
    pass


class TextSelector(TextInput):
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
        self.text = 'Equals'
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
    fields = ['Text', 'Type Line', 'Name', 'Toughness']

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
        print("Removing row", view)
        self.inner_layout.remove_widget(view)
        if len(self.inner_layout.children) > 0:
            self.inner_layout.children[0].delete_conn

    def perform_search(self):
        query = Cards.CardsQuery()
        for i, child in enumerate(self.inner_layout.children):
            query = child.update_query(i, query)

        cards = query.find_all()
        next_page = ResultPage(cards)
        next_screen = Screen(name="Results")
        next_screen.add_widget(next_page)
        app = App.get_running_app()
        app.root.add_widget(next_screen)
        app.root.current = 'Results'
        for card in cards:
            print(card)
            print()


class SearchPage(BoxLayout):
    pass


class CardResult(BoxLayout):
    name = StringProperty('')
    image_url = StringProperty('')
    power = StringProperty('')
    toughness = StringProperty('')
    mana_cost = StringProperty('')
    set_name = StringProperty('')
    type_line = StringProperty('')
    full_type_line = StringProperty('')
    index = None

    def refresh_view_attrs(self, rv, index, data):
        """Catch and handle the view changes"""
        self.index = index
        print(data)
        return super(CardResult, self).refresh_view_attrs(
            rv, index, data)

    def create_type_line(self):
        print('type', self.type_line, self.power, self.toughness)
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


class ResultPage(RecycleView):
    def __init__(self, data, **kwargs):
        super(ResultPage, self).__init__(**kwargs)
        self.data = list(data)


class SearchApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(SearchScreen(name="Search"))
        return sm


if __name__ == '__main__':
    Window.clearcolor = (1, 1, 1, 1)
    SearchApp().run()
# Label:
#     font_size: 32
#     center_x: root.width / 4
#     top: root.top
#     text: "Deck Builder"

# Button:
#     font_size: 18
#     center_x: 2 * root.width / 3
#     top: root.top / 12
#     text: "Search"