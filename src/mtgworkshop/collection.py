from mtgworkshop.utils import split_and_cut


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
