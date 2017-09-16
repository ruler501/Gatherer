from kivy.app import App
from kivy.core.window import Window
from kivy.lang.builder import Builder
from kivy.uix.screenmanager import ScreenManager

from cards import CardScreen, RulingsBox  # noqa
from results import CardResult, ResultPage, ResultsScreen  # noqa
from search import ConnectorSelector, FieldInput, FieldSelector, NegateSelector, OperationSelector, SearchPage, SearchScreen  # noqa
from utils import ManaCost, MultiLineLabel, MyTab  # noqa


class WorkshopApp(App):
    def build(self):
        Builder.load_file('src/res/workshop.kv')
        sm = ScreenManager()
        sm.add_widget(SearchScreen(name="Search"))
        return sm


if __name__ == '__main__':
    Window.clearcolor = [0.6, 0.6, 0.6, 1]
    WorkshopApp().run()
