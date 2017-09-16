import os


CACHE_DIR = 'cache'
DEFAULT_CACHE_FILE = CACHE_DIR + '/worshop.config'


class ConfigurationManager:
    default_values = \
        {
        }

    def __init__(self, config_file):
        uncacheable = \
            {
                'uncacheable',
                'config_file',
                'cached_values'
            }
        object.__setattr__(self, 'uncacheable', uncacheable)
        object.__setattr__(self, 'config_file', config_file)
        object.__setattr__(self, 'cached_values', set())
        if os.path.exists(config_file):
            with open(config_file) as conf:
                for line in conf:
                    key, val = line.strip().split('=')
                    self.cached_values.add(key)
                    object.__setattr__(self, key, val)

    def __getattr__(self, key):
        if key in self.default_values:
            val = self.default_values[key]
            setattr(self, key, val)
            return val
        else:
            return None

    def __setattr__(self, key, val):
        if getattr(self, key) is None and \
                key not in self.uncacheable:
            self.cached_values.add(key)
        object.__setattr__(self, key, val)
        if key in self.cached_values:
            with open(self.config_file, 'w') as conf:
                conf.write('\n'.join('{}={}'.format(key, getattr(self, key)) for key in self.cached_values))

    def add_uncacheable_key(self, key):
        self.uncacheable.add(key)


DefaultConfiguration = ConfigurationManager(DEFAULT_CACHE_FILE)
DefaultConfiguration.add_uncacheable_key('current_deck')
