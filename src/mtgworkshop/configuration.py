import os

from collections import defaultdict
from weakref import WeakMethod

from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
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
            setattr(self, key, val)
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
        self.default_value = default_value
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
        for key in configuration.cached_keys:
            inner_layout.add_widget(ConfigurationOption(key, getattr(configuration, key)))

        inner_layout.add_widget(Button(text='Save', size_hint=(1, None), height=40,
                                       on_release=lambda btn: self.save_settings()))

    def save_settings(self):
        inner_layout = self.inner_layout

        for option in inner_layout.children:
            if isinstance(option, ConfigurationOption):
                setattr(self.configuration, option.original_key, option.text_sel.text)

        inner_layout.clear_widgets()
        self.on_inner_layout(None, inner_layout)
