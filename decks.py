from collections import Counter

import magic_db


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
        res.append("///mvid:{0:} qty:{1:} name:{2:} loc:Deck\n{1:} {2:}"
                   .format(mvid, qty, magic_db.Cards.find_by_mvid(mvid)['name']))
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


if __name__ == "__main__":
    mvids = import_coll2("CommanderAllSets.coll2")
    unique = magic_db.make_unique((x for x in mvids if magic_db.is_origin_legal(x)),
                                  lambda x: magic_db.Cards.find_by_mvid(x)['name'])
    print(len(unique))
    export_coll2(unique, "Result.coll2")
