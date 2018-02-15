#!/usr/bin/env python3
import os
import sys

from kivy.app import App
from kivy.core.window import Window
from kivy.garden.androidtabs import AndroidTabs
from kivy.lang.builder import Builder
from kivy.uix.screenmanager import ScreenManager

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/src')
from mtgworkshop.configuration import ConfigurationScreen, DefaultConfiguration
from mtgworkshop.decks import DeckScreen
from mtgworkshop.search import SearchScreen
from mtgworkshop.utils import MyTab

__version__ = '0.0.1-MVP'

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
        sm.add_widget(ConfigurationScreen(name='Config'))
        tab3.add_widget(sm)
        android_tabs.add_widget(tab3)

        Window.bind(on_keyboard=self.onBackBtn)

        return android_tabs

    def onBackBtn(self, window, key, *args):
        """ To be called whenever user presses Back/Esc Key """
        # If user presses Back/Esc Key
        if key == 27:
            # Do whatever you need to do, like check if there are any
            # screens that you can go back to.
            # return True if you don't want to close app
            # return False if you do
            return True
        return False

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

    def on_pause(self):
        return True


if __name__ == '__main__':
    # Config.set('graphics', 'width', DefaultConfiguration.window_width)
    # Config.set('graphics', 'height', DefaultConfiguration.window_height)
    if not os.path.exists('cache/images'):
        os.makedirs('cache/images')
    # files = os.listdir('cache/images')
    # print(files)
    # import io
    # from kivy.core.image import Image as CoreImage
    # file_data = open('cache/images/93.jpeg', 'rb').read()
    # print(len(file_data), file_data)
    # data = io.BytesIO(file_data)
    # img = CoreImage(data, ext='jpeg')
    # sys.exit()
    if not os.path.dirname(os.path.realpath(__file__)).startswith('/data/data/com.'):
        Window.size = (int(DefaultConfiguration.window_width), int(DefaultConfiguration.window_height))
    Window.clearcolor = [0.6, 0.6, 0.6, 1]
    WorkshopApp().run()
