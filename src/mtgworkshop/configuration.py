import os

from collections import defaultdict
from weakref import WeakMethod

from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.garden.filebrowser import FileBrowser
from kivy.metrics import dp
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
# from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.screenmanager import Screen


CACHE_DIR = 'cache'
DEFAULT_CACHE_FILE = CACHE_DIR + '/worshop.config'


class ConfigurationManager:
    default_values = \
        {
            'window_width': 540,
            'window_height': 960
        }

    def __init__(self, config_file):
        uncacheable = \
            {
                'uncacheable',
                'config_file',
                'cached_keys',
                'listeners'
            }
        object.__setattr__(self, 'uncacheable', uncacheable)
        object.__setattr__(self, 'config_file', config_file)
        object.__setattr__(self, 'cached_keys', set())
        object.__setattr__(self, 'listeners', defaultdict(set))
        if os.path.exists(config_file):
            with open(config_file) as conf:
                for line in conf:
                    key, val = line.strip().split('=')
                    self.cached_keys.add(key)
                    object.__setattr__(self, key, val)

    def __getattr__(self, key):
        if key in self.default_values:
            val = self.default_values[key]
            object.__setattr__(self, key, val)
            if key not in self.uncacheable:
                self.cached_keys.add(key)
                if key in self.cached_keys:
                    with open(self.config_file, 'w') as conf:
                        conf.write('\n'.join('{}={}'.format(_key, getattr(self, _key)) for _key in self.cached_keys))
            return val
        else:
            return None

    def __setattr__(self, key, val):
        if getattr(self, key) is None and \
                key not in self.uncacheable:
            self.cached_keys.add(key)

        object.__setattr__(self, key, val)

        if key in self.cached_keys:
            with open(self.config_file, 'w') as conf:
                conf.write('\n'.join('{}={}'.format(key, getattr(self, key)) for key in self.cached_keys))

        dead_listeners = set()
        for listener in self.listeners[key]:
            f = listener()
            if f is None:
                dead_listeners.add(f)
            else:
                f(val)
        self.listeners[key] -= dead_listeners

    def __getitem__(self, key):
        return getattr(self, key)

    def add_uncacheable_key(self, key):
        self.uncacheable.add(key)

    def register_listener(self, key, callback):
        self.listeners[key].add(WeakMethod(callback))


DefaultConfiguration = ConfigurationManager(DEFAULT_CACHE_FILE)
DefaultConfiguration.add_uncacheable_key('current_deck')
DefaultConfiguration.add_uncacheable_key('last_screen')


class ConfigurationOption(BoxLayout):
    key = StringProperty()
    default_value = StringProperty('')

    text_sel = ObjectProperty()

    def __init__(self, key, default_value, **kwargs):
        self.original_key = key
        self.key = self.format_key(key)
        if default_value is None:
            default_value = ''
        self.default_value = str(default_value)
        super(ConfigurationOption, self).__init__(**kwargs)

    def format_key(self, key):
        return ' '.join(x[0].upper() + x[1:] for x in key.split('_'))


class ConfigurationScreen(Screen):
    inner_layout = ObjectProperty()

    def __init__(self, configuration=DefaultConfiguration, **kwargs):
        self.configuration = configuration
        super(ConfigurationScreen, self).__init__(**kwargs)

    def on_inner_layout(self, instance, value):
        inner_layout = self.inner_layout
        if len(inner_layout.children) > 0:
            return
        inner_layout.bind(minimum_height=inner_layout.setter('height'))

        configuration = self.configuration
        self.lookup_table = []
        for key in configuration.cached_keys:
            if os.path.exists(configuration[key]):
                print(key, 'path')
                current_value = os.path.dirname(os.path.realpath(configuration[key]))
                inner_layout.add_widget(FileBrowser(size_hint=(1, None),
                                                    height=dp(400),
                                                    filters=['*.dec'],
                                                    path=current_value))
            else:
                print(key, 'nonpath')
                inner_layout.add_widget(ConfigurationOption(key, getattr(configuration, key)))
            self.lookup_table.append(key)

        inner_layout.add_widget(Button(text='Save', size_hint=(1, None), height=dp(40),
                                       on_release=lambda btn: self.save_settings()))

    def save_settings(self):
        inner_layout = self.inner_layout

        for option, key in zip(inner_layout.children, self.lookup_table):
            if isinstance(option, ConfigurationOption):
                setattr(self.configuration, key, option.text_sel.text)
            elif isinstance(option, FileBrowser):
                if len(option.paths) == 1:
                    path = option.paths[0]
                    setattr(self.configuration, key, path)

        inner_layout.clear_widgets()
        self.on_inner_layout(None, inner_layout)
