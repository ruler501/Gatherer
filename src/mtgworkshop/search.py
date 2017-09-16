from kivy.properties import BooleanProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.screenmanager import Screen
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


class SearchPage(ScrollView):
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
        from results import ResultsScreen
        query = Cards.CardsQuery()
        for i, child in enumerate(self.inner_layout.children):
            query = child.update_query(i, query)

        cards = query.find_all()
        next_page = ResultsScreen(cards, name="Results")
        self.parent.parent.manager.add_widget(next_page)
        self.parent.parent.manager.current = 'Results'
        self.parent.parent.manager.remove_widget(self.parent.parent)
