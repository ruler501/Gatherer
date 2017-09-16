import os
import pickle

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


def split_and_cut(s, txt, ind, *args):
    """
    Split a string on a sequence of txt arguments and pull out specific indexes.

    Assumes at least one of find, sind is not None
    """
    ret_list = s.split(txt)
    if isinstance(ind, tuple):
        find, sind = ind
        if find is None:
            ret_list = ret_list[:sind]
        elif sind is None:
            ret_list = ret_list[find:]
        else:
            ret_list = ret_list[find:sind]
        ret = txt.join(ret_list)
    else:
        ret = ret_list[ind]
    if len(args) > 0:
        return split_and_cut(ret, *args)
    else:
        return ret


def disk_cache(cache_file):
    def dec(fun):
        cache = {}
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as inp:
                cache = pickle.load(inp)

        def f(*args, **kwargs):
            args_tuple = frozenset(kwargs.items()), *args
            res = cache.get(args_tuple, None)
            if res is not None:
                return res
            res = fun(*args, **kwargs)
            cache[args_tuple] = res
            with open(cache_file, 'wb') as inp:
                pickle.dump(cache, inp)
            return res
        return f
    return dec


def make_unique(lst, func=lambda x: x):
    res = []
    used = set()
    for x in lst:
        val = func(x)
        if val not in used:
            res.append(x)
            used.add(val)
    return res
