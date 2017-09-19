import itertools
import math
import os
import pickle
import urllib.request

from threading import Thread

from kivy.clock import mainthread
from kivy.garden.androidtabs import AndroidTabsBase
from kivy.graphics.texture import Texture
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
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
                self.add_widget(Image(source='res/{}.png'.format(m),
                                      width=self.MANA_SIZE,
                                      allow_stretch=True,
                                      keep_ratio=True,
                                      mipmap=True,
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
    class Decorator:
        def __init__(self, func):
            self.f = func
            self.cache = {}
            self.to_disk = True
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as inp:
                    self.cache = pickle.load(inp)

        def save_to_disk(self):
            with open(self.cache_file, 'wb') as inp:
                pickle.dump(self.cache, inp)

        def __call__(self, *args, **kwargs):
            args_tuple = frozenset(kwargs.items()), *args
            res = self.cache.get(args_tuple, None)
            if res is not None:
                return res
            res = self.f(*args, **kwargs)
            self.cache[args_tuple] = res
            if self.to_disk:
                self.save_to_disk()
            return res
    Decorator.cache_file = cache_file
    return Decorator


def make_unique(lst, func=lambda x: x):
    res = []
    used = set()
    for x in lst:
        val = func(x)
        if val not in used:
            res.append(x)
            used.add(val)
    return res


class Gradient(object):
    @staticmethod
    def horizontal(*points):
        texture = Texture.create(size=(len(points), 1), colorfmt="rgba")
        buf = bytes(itertools.chain(*points))
        texture.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
        return texture

    @staticmethod
    def vertical(*points):
        texture = Texture.create(size=(1, len(points)), colorfmt="rgba")
        buf = bytes(itertools.chain(*points))
        texture.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')
        return texture


class CroppedImage(Image):
    skip = BooleanProperty(False)
    crop_to = ListProperty(None, allownone=True)
    original_size = ListProperty(None, allownone=True)

    def __init__(self, **kwargs):
        self.old_texture_update = self.texture_update
        super(CroppedImage, self).__init__(**kwargs)
        self.texture_update = self.on_image_loaded
        self.real_texture = None

    def on_image_loaded(self, *args):
        if self.crop_to is None or self.original_size is None \
                or len(self.crop_to) != 4 or len(self.original_size) != 2:
            return
        old_ratio = self.get_image_ratio()
        correct_ratio = self.original_size[0] / float(self.original_size[1])
        if math.isclose(old_ratio, correct_ratio, abs_tol=0.1):
            ratio = self.texture.height / self.original_size[1]
            x, y, width, height = (a * ratio for a in self.crop_to)
            self.texture = self.real_texture = \
                self.texture.get_region(x, self.texture.height - y - height, width, height)
            self._coreimage.unbind(on_texture=self.on_image_loaded)

    def on_texture(self, instance, value):
        real_texture = getattr(self, 'real_texture')
        if real_texture is not None and self.texture != real_texture:
            self.texture = real_texture
        if self.skip:
            return
        self._coreimage.bind(on_texture=self.on_image_loaded)
        self.skip = True
        self.on_image_loaded()

    def on_source(self, instance, value):
        self.skip = False
        self.real_texture = None
        self.old_texture_update()


class CachedImage(BoxLayout):
    image_location = StringProperty('res/loading.jpeg')

    allow_stretch = BooleanProperty(True)
    keep_ratio = BooleanProperty(True)
    source = StringProperty()
    original_size = ListProperty(None, allownone=True)
    crop_to = ListProperty(None, allownone=True)

    cache_path = 'cache/images/{}'

    def __init__(self, image_format='.jpeg', **kwargs):
        self.image_format = image_format
        if 'source' in kwargs:
            self.source = kwargs['source']
        super(CachedImage, self).__init__(**kwargs)

    def on_source(self, instance, value):
        if self.source.startswith('http'):
            cache_path = self.get_cached_path(value)
            if os.path.exists(cache_path):
                self.image_location = cache_path
            else:
                get_thread = Thread(target=self.download_image, args=(value,))
                get_thread.start()
        else:
            self.image_location = value

    def get_cached_path(self, original_value):
        res = original_value[1:][-20:]
        if 'multiverseid' in original_value:
            res = split_and_cut(original_value, 'multiverseid=', 1, '&', 0)
            if '.' in original_value[-5:]:
                res += split_and_cut(original_value, '.', -1)
        if '.' not in res[-5:]:
            res += self.image_format
        return self.cache_path.format(res)

    @mainthread
    def set_image_location(self, value):
        self.image_location = value

    def download_image(self, value):
        cache_path = self.get_cached_path(value)
        urllib.request.urlretrieve(value, cache_path)
        self.set_image_location(cache_path)
