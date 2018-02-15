import functools
import itertools
import os
import pickle
import urllib.request

from collections import defaultdict
from threading import Thread

from kivy.clock import mainthread
from kivy.garden.androidtabs import AndroidTabsBase
from kivy.graphics.texture import Texture
from kivy.metrics import sp
from kivy.properties import ListProperty, NumericProperty, \
    ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget


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


class ManaImage(Widget):
    texture = ObjectProperty()

    def __init__(self, texture, **kwargs):
        self.texture = texture
        super(ManaImage, self).__init__(**kwargs)


class ManaCost(RelativeLayout):
    symbols = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11',
               '12', '13', '14', '15', '16', '17', '18', '19', '20', 'X', 'Y',
               'Z', 'W', 'U', 'B', 'R', 'G', 'S', 'W/U', 'W/B', 'U/B', 'U/R',
               'B/R', 'B/G', 'R/W', 'R/G', 'G/W', 'G/U', 'T', 'Q', '∞', '½',
               'FET', '4ET', 'OW']
    mana_cost = StringProperty('', allownone=True)
    # full_texture = ObjectProperty(None, allownone=True)

    MANA_SIZE = sp(18)
    # full_image = CoreImage(resource_find('res/Mana.png'), mipmap=True)

    def __init__(self, **kwargs):
        self.cache_images = defaultdict(list)
        # self.full_image.bind(on_texture=self.set_full_texture)
        # self.full_texture = self.full_image.texture
        super(ManaCost, self).__init__(**kwargs)

    # def set_full_texture(self, *args):
    #     self.full_texture = self.full_image.texture

    def on_mana_cost(self, instance, value):
        if value is None:
            return

        self.clear_widgets()
        mana_cost = value.replace('{', '').split('}')
        count = 0
        pre_cache_images = defaultdict(list)
        for m in mana_cost:
            m = str(m)
            if len(m) == 0:
                continue
            if len(self.cache_images[m]) > 0:
                mana_image = self.cache_images[m].pop()
            elif m in self.symbols:
                path = 'atlas://res/mana/{}'.format(m.replace('/', '-'))
                mana_image = Image(source=path, mipmap=True, allow_stretch=True,
                                   size_hint=(None, None), size=(self.MANA_SIZE, self.MANA_SIZE))
            else:
                mana_image = Label(text=m, color=[0, 0, 0, 1],
                                   size=(self.MANA_SIZE, self.MANA_SIZE))
            mana_image.pos = (self.MANA_SIZE * 1.1 * count, 0)
            self.add_widget(mana_image)
            pre_cache_images[m].append(mana_image)
            count += 1
        for m, cache in pre_cache_images.items():
            self.cache_images[m] += cache


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


class CachedImage(Image):
    image_location = StringProperty()

    original_height = NumericProperty(None, allownone=True)
    crop_to = ListProperty(None, allownone=True)

    cache_path = 'cache/images/{}'

    def __init__(self, image_format='.jpeg', **kwargs):
        self.cropped_image = None
        self.image_format = image_format
        if 'source' in kwargs:
            self.source = kwargs['source']
        super(CachedImage, self).__init__(**kwargs)

    def on_source(self, instance, value):
        if self.source.startswith('http'):
            cache_path = self.get_cached_path(value)
            if os.path.exists(cache_path):
                self.source = cache_path
            else:
                self.saved_crop_to = self.crop_to
                self.saved_original_height = self.original_height
                self.crop_to = []
                self.original_height = None
                get_thread = Thread(target=self.download_image, args=(value,))
                get_thread.start()
                self.source = 'res/loading.jpeg'

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
        self.source = value

    def download_image(self, value):
        cache_path = self.get_cached_path(value)
        urllib.request.urlretrieve(value, cache_path)
        self.crop_to = self.saved_crop_to
        self.original_height = self.saved_original_height
        self.set_image_location(cache_path)

    def crop_image(self, *args):
        if self.image.texture is None:
            return

        theight = self.image.texture.height
        ratio = theight / self.original_height
        x, y, width, height = (a * ratio for a in self.crop_to)
        self.texture = \
            self.image.texture.get_region(x, theight - y - height,
                                          width, height)

    def render_image(self, *args):
        self.texture = self.image.texture

    def on_texture(self, instance, value):
        if self.crop_to is None or self.original_height is None or \
                self.original_height == 0 or len(self.crop_to) != 4 or \
                self.cropped_image == self.texture:
            return

        theight = self.texture.height
        ratio = theight / self.original_height
        x, y, width, height = (a * ratio for a in self.crop_to)
        temp_texture = \
            self.texture.get_region(x, theight - y - height,
                                    width, height)
        self.cropped_image = temp_texture
        self.texture = temp_texture


class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
        Thread.__init__(self, group, target, name, args, kwargs, daemon=daemon)

        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self):
        Thread.join(self)
        return self._return


def backgroundthread(func):
    @functools.wraps(func)
    def delayed_func(*args, **kwargs):
        res = ThreadWithReturnValue(target=func, args=args, kwargs=kwargs)
        res.start()
        return res
    return delayed_func
