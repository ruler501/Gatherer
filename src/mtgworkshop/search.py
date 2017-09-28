from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from mtgworkshop.magic_db import Cards


class SearchScreen(Screen):
    pass


class NegateSelector(BoxLayout):
    use_not = BooleanProperty(False)

    def set_use_not(self, value):
        self.use_not = value


class OperationSelector(Button):
    field = StringProperty('Text')

    def __init__(self, **kwargs):
        super(OperationSelector, self).__init__(**kwargs)
        self.text = 'Contains'
        self.font_size = sp(16)

        self.drop_list = DropDown()
        self.bind(on_release=self.drop_list.open)
        self.drop_list.bind(on_select=lambda instance, x: setattr(self, 'text', x))

        self.on_field(None, self.field)

    def create_dropdown(self):
        self.drop_list.clear_widgets()
        if self.text not in self.operations:
            if 'Contains' in self.operations:
                self.text = 'Contains'
            elif 'Equals' in self.operations:
                self.text = 'Equals'
            else:
                self.text = self.operations[0]
        for op in self.operations:
            btn = Button(text=op, size_hint_y=None, height=dp(32))
            btn.bind(on_release=lambda btn: self.drop_list.select(btn.text))
            btn.font_size = sp(16)
            self.drop_list.add_widget(btn)

    def on_field(self, instance, value):
        field = self.field.lower().replace(' ', '_')
        self.operations = []
        for op, values in Cards.CardsQuery.var_ops.items():
            if field in values:
                self.operations.append(op.replace('_', ' ').title())
        self.operations = sorted(self.operations)
        self.create_dropdown()

    def get_operation(self):
        return self.text.replace(' ', '_').lower()


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
            btn = Button(text=conn, size_hint_y=None, height=dp(30))
            btn.bind(on_release=lambda btn: self.drop_list.select(btn.text))
            btn.font_size = sp(16)
            self.drop_list.add_widget(btn)

        self.bind(on_release=self.drop_list.open)

        self.drop_list.bind(on_select=lambda instance, x: setattr(self, 'text', x))

    def get_connector(self):
        return self.connectors[self.text]


class FieldSelector(Button):
    fields = sorted(x.replace('_', ' ').title() for x in Cards.card_vars.keys())

    def __init__(self, **kwargs):
        super(FieldSelector, self).__init__(**kwargs)
        self.text = 'Text'

        self.drop_list = DropDown()
        for field in self.fields:
            btn = Button(text=field, size_hint_y=None, height=dp(30))
            btn.bind(on_release=lambda btn: self.drop_list.select(btn.text))
            btn.font_size = sp(16)
            self.drop_list.add_widget(btn)

        self.bind(on_release=self.drop_list.open)

        self.drop_list.bind(on_select=lambda instance, x: setattr(self, 'text', x))

    def get_field(self):
        return self.text.lower().replace(' ', '_')


class FieldInput(BoxLayout):
    op_sel = ObjectProperty()
    # conn_sel = ObjectProperty()
    field_sel = ObjectProperty()
    text_sel = ObjectProperty()
    neg_sel = ObjectProperty()

    def remove_row(self):
        self.parent.parent.remove_row(self)

    def update_query(self, i, query):
        if len(self.text_sel.text) == 0:
            return query
        # if i > 0:
        #     query = getattr(query, self.conn_sel.get_connector())()
        if self.neg_sel.use_not:
            query = query.negated()
        kwargs = {self.field_sel.get_field(): self.text_sel.text}
        query = query._where(self.op_sel.get_operation(), **kwargs)
        return query


class SearchPage(ScrollView):
    inner_layout = ObjectProperty()
    sort_sel = ObjectProperty()
    screen = ObjectProperty()

    def on_inner_layout(self, instance, value):
        self.inner_layout.bind(minimum_height=self.inner_layout.setter('height'))
        self.add_row()

    def on_screen(self, instance, value):
        print(self.screen, 'screen value set')

    def add_row(self):
        row = FieldInput()
        self.inner_layout.add_widget(row)

    def remove_row(self, view):
        self.inner_layout.remove_widget(view)

    def perform_search(self):
        from mtgworkshop.results import ResultsScreen
        query = Cards.CardsQuery()
        for i, child in enumerate(child
                                  for child
                                  in self.inner_layout.children
                                  if isinstance(child, FieldInput)):
            query = child.update_query(i, query)

        cards = sorted(query.find_all(), key=self.sort_sel.get_sort())
        next_page = ResultsScreen(cards, name="Results")
        manager = self.screen.parent
        manager.add_widget(next_page)
        manager.current = 'Results'
        manager.remove_widget(self.screen)
