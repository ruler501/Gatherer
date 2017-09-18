from kivy.app import App
from kivy.core.window import Window
from kivy.garden.androidtabs import AndroidTabs
from kivy.lang.builder import Builder
from kivy.uix.screenmanager import ScreenManager

from configuration import ConfigurationScreen
from decks import DeckScreen
from search import SearchScreen
from utils import MyTab


class WorkshopApp(App):
    def build(self):
        Builder.load_file('src/res/workshop.kv')
        android_tabs = AndroidTabs()

        tab1 = MyTab(text="Search")
        sm = ScreenManager()
        sm.add_widget(SearchScreen(name="Search"))
        tab1.add_widget(sm)
        android_tabs.add_widget(tab1)

        tab2 = MyTab(text="Decks")
        sm = ScreenManager()
        sm.add_widget(DeckScreen(name="Deck"))
        tab2.add_widget(sm)
        android_tabs.add_widget(tab2)

        tab3 = MyTab(text="Settings")
        sm = ScreenManager()
        sm.add_widget(ConfigurationScreen())
        tab3.add_widget(sm)
        android_tabs.add_widget(tab3)

        return android_tabs

    def on_start(self):
        import builtins
        prof = self.prof = builtins.__dict__.get('profile', None)
        if prof is not None:
            print("Profiling")
            prof.enable_profile_all()
            prof.enable()

    def on_stop(self):
        prof = self.prof
        if prof is not None:
            prof.disable()


if __name__ == '__main__':
    Window.clearcolor = [0.6, 0.6, 0.6, 1]
    WorkshopApp().run()
