#!/usr/bin/env python3
import logging
import pickle
import os
import urllib.request

from collections import Counter

from bs4 import BeautifulSoup
# Future Work. Support looking up without mvid number, Fix split cards, CMC extraction, Type Extraction


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


colors = ['White', 'Blue', 'Black', 'Red', 'Green', 'Colorless']


def disk_cache(cache_file):
    def dec(fun):
        cache = {}
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as inp:
                cache = pickle.load(inp)

        def f(*args):
            res = cache.get(tuple(args), None)
            if res is not None:
                return res
            res = fun(*args)
            cache[tuple(args)] = res
            with open(cache_file, 'wb') as inp:
                pickle.dump(cache, inp)
            return res
        return f
    return dec


class CardInfo:
    def __init__(self, name='Unknown', cost='Unknown', text='', flavor_text='',
                 supertypes=[], types=[], subtypes=[], image_link='',
                 power='', toughness='', printing='UNK', rarity='Unknown',
                 artist='Unknown', color_identity='', other_printings=[],
                 number=-1):
        self.name = name
        self.cost = cost
        self.text = text
        self.flavor_text = flavor_text
        self.supertypes = supertypes
        self.types = types
        self.subtypes = subtypes
        self.image_link = image_link
        self.power = power
        self.toughness = toughness
        self.printing = printing
        self.rarity = rarity
        self.artist = artist
        self.color_identity = color_identity
        self.other_printings = other_printings
        self.number = number

    def __str__(self):
        image_link = '<img src="{}">'.format(self.image_link)
        fields = [self.name, self.cost, self.text, self.flavor_text,
                  self.types, image_link, self.power,
                  self.printing, self.rarity, self.artist, self.color_identity]
        return ';'.join(['{}'.format(n.replace('\n', '<br>')) for n in fields])


def get_value_text(key, box='value'):
    def fun(doc):
        search_items = doc.find_all(**{"id": key})[0]
        search_item = search_items.find_all(**{'class': box})[0]
        return search_item.text.strip()
    return fun


def get_color_id_str(doc):
    res = set()
    search_items = doc.find_all(**{'class': 'manaRow'})
    search_items += doc.find_all(**{'class': 'cardtextbox'})
    for item in search_items:
        image_items = item.find_all('img')
        for img in image_items:
            possibles = img.get('alt')
            if possibles is None:
                continue
            possibles = possibles.replace('Variable Colorless', '')
            for color in colors:
                if color in possibles:
                    res.add(color)
        return ' '.join(res)


def get_other_printing_list(doc):
    res = []
    search_items = doc.find_all(**{"id": "ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_otherSetsValue"})[0]
    search_items = search_items.find_all('a')
    for link in search_items:
        try:
            res.append(split_and_cut(link.get('href'), '=', -1))
        except Exception as e:
            logging.exception("Error parsing link")
    return res


def get_image_link(doc):
    search_item = doc.find_all(**{'id': 'ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_cardImage'})[0]
    return 'https://gatherer.wizards.com' + search_item['src'][5:]


@disk_cache('card.cache')
def get_card(mvid):
    r_url = 'http://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid={}'.format(mvid)
    doc = None
    req = urllib.request.urlopen(r_url)
    doc = BeautifulSoup(req.read(), "lxml")
    req.close()

    # def CardInfo(self, name='Unknown', cost='Unknown', text='', flavor_text='',
    #              supertypes=[], types=[], subtypes=[], image_link='',
    #              power='', toughness='', printing='UNK', rarity='Unknown',
    #              artist='Unknown', color_idenity='', other_printings=[]):
    fields = {
        'name': get_value_text('ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_nameRow'),
        # Eventually replace with a function to correctly read
        'cost': 'ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_manaRow',
        'text': get_value_text('ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_textRow'),
        'flavor_text': get_value_text('ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_FlavorText',
                                      box='flavortextbox'),
        # Eventually split into sub, super, regular
        'types': get_value_text('ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_typeRow'),
        'image_link': get_image_link,
        'power': get_value_text('ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_ptRow'),
        # Need to correctly parse out set name and maybe 3 letter code
        'printing': get_value_text('ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_setRow'),
        'rarity': get_value_text('ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_rarityRow'),
        'artist': get_value_text('ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_artistRow'),
        'color_identity': get_color_id_str,
        'other_printings': get_other_printing_list
    }

    kwargs = {}
    for field, f in fields.items():
        try:
            kwargs[field] = f(doc)
        except:
            pass

    return CardInfo(**kwargs)


@disk_cache('color.cache')
def get_color_identity(mvid):
    """
    Get a set of colors in the cards color identity. Card passed as two lines from a dec file.
    """
    res = set()
    r_url = 'http://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid={}'.format(mvid)
    doc = None
    req = urllib.request.urlopen(r_url)
    doc = BeautifulSoup(req.read(), "lxml")
    req.close()

    search_items = doc.find_all(**{'class': 'manaRow'})
    search_items += doc.find_all(**{'class': 'cardtextbox'})
    for item in search_items:
        image_items = item.find_all('img')
        for img in image_items:
            possibles = img.get('alt')
            if possibles is None:
                continue
            possibles = possibles.replace('Variable Colorless', '')
            for color in colors:
                if color in possibles:
                    res.add(color)
    return res


@disk_cache('sets.cache')
def get_all_printings(mvid):
    """
    Return a list of ids for each printing of the card. Only returns the original mvid for split cards.
    """
    res = []

    r_url = 'http://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid={}'.format(mvid)
    doc = None
    req = urllib.request.urlopen(r_url)
    doc = BeautifulSoup(req.read(), "lxml")
    req.close()
    try:
        search_items = doc.find_all(**{"id": "ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_otherSetsValue"})[0]
        search_items = search_items.find_all('a')
        for link in search_items:
            try:
                res.append(split_and_cut(link.get('href'), '=', -1))
            except Exception as e:
                logging.exception("Error parsing link")
    except:
        logging.debug("{}: Probably a split card which aren't supported yet or is only in 1 expansion".format(mvid))
        return [mvid]
    return res


@disk_cache('names.cache')
def get_name(mvid):
    """
    Return the name of a card by id
    """
    print(mvid)
    r_url = 'http://gatherer.wizards.com/Pages/Card/Details.aspx?multiverseid={}'.format(mvid)
    doc = None
    req = urllib.request.urlopen(r_url)
    doc = BeautifulSoup(req.read(), "lxml")
    req.close()

    try:
        search_item = doc.find_all(**{"id": "ctl00_ctl00_ctl00_MainContent_SubContent_SubContent_nameRow"})[0]
        search_item = search_item.find_all(**{"class": "value"})[0]
        return search_item.text.strip()
    except:
        logging.exception("Probably a split card which aren't supported yet")
        return "Unknown"


def import_dec(fname):
    """
    Return a list of mvids of cards in the dec file with repetition
    """
    mvids = []
    with open(fname) as rare_file:
        comment = True
        for line in rare_file:
            if comment:
                mvid = split_and_cut(line, 'mvid:', 1, ' ', 0)
                qty = split_and_cut(line, 'qty:', 1, ' ', 0)
                mvids += [mvid] * int(qty)
            comment = not comment
    return mvids


def export_dec(ids, fname):
    """
    Saves a dec file at fname with all the ids translated into cards in the
    main deck. Does not support sideboard
    """
    oc = Counter(ids)
    res = []
    for mvid, qty in oc.items():
        res.append("///mvid:{0:} qty:{1:} name:{2:} loc:Deck\n{1:} {2:}".format(mvid, qty, get_name(mvid)))
    with open(fname, 'w') as of:
        of.write('\n'.join(res))
    return res


def import_coll2(fname):
    """
    Return a list of mvids of cards in the coll2 file without repetition
    """
    mvids = []
    with open(fname) as rare_file:
        r = False
        i = 0
        for line in rare_file:
            if i < 3:
                i += 1
                continue
            if not r:
                mvids.append(split_and_cut(line, 'id: ', 1).strip())
            r = not r
        return mvids


def export_coll2(mvids, fname):
    res = ['doc:', '- version: 1', '- items:']
    mvids = sorted(mvids, key=lambda x: int(x))
    for mvid in mvids:
        res.append('  - - id: {}\n    - r: 1'.format(mvid))
    with open(fname, 'w') as of:
        of.write('\n'.join(res))
    return res
