from kivy.garden.androidtabs import AndroidTabsBase
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout


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


class ManaCost(RelativeLayout):
    symbols = ['W', 'U', 'B', 'R', 'G', 'C', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'X']
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
                self.add_widget(AsyncImage(source='res/{}.png'.format(m),
                                           width=self.MANA_SIZE,
                                           allow_stretch=True,
                                           keep_ratio=True,
                                           size_hint=(None, None),
                                           pos=(self.MANA_SIZE * 1.1 * count, -self.MANA_SIZE * 2)))
                count += 1
            else:
                self.add_widget(Label(text=m, color=[0, 0, 0, 1], size=(32, 32), pos=(36 * count, 0)))
                count += 1


class MyTab(BoxLayout, AndroidTabsBase):
    pass
