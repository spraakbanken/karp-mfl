import helpers

import pextract.generate as generate
import pextract.morphparser as mp
import pextract.pextract as pex


def reload_paradigms(paradigms):
    pass


def load_paradigms(paradigms):
    pass


def add_paradigm(pid, paradigm, paradigms):
    paradigm.set_id(pid)
    paradigms.append(paradigm)
    # send_to_karp()


def add_word_to_paradigm(lemgram, inst, paradigm):
    print('old count', paradigm.count)
    var_inst = list(enumerate([lemgram]+list(inst)))
    print('old var inst', paradigm.var_insts[-1])
    paradigm.var_insts.append(var_inst)
    paradigm.count += 1
    print('new var inst', paradigm.var_insts[-1])
    print('new count', paradigm.count)
    # send_to_karp()


def update_paradigm(pid, paradigm, paradigms):
    for ix, p in enumerate(paradigms):
        if p == pid:
            paradigms[ix] = paradigm
            break
    # send_to_karp()


def remove_paradigm(pid, paradigms):
    for ix, p in enumerate(paradigms):
        if p == pid:
            del paradigms[ix]
    # send_to_karp()


def inflect_table(table, settings):
     # TODO also send thesetags (table[1]) to test_paradigms
    pex_table = helpers.tableize(table, add_tags=False)
    res = mp.test_paradigms([pex_table], *settings, returnempty=False)
    print('inflect table %s, tags %s' % (pex_table[0], pex_table[1]))
    print('res', res)
    if res:
        ans = {"Results": helpers.format_inflection(res, 1), 'new': False,
               'analyzes': res[0][1][0]}
    else:
        pex_table = helpers.tableize(table, add_tags=True)
        paradigm = pex.learnparadigms([pex_table])[0]
        ans = {'new': True,
               'paradigm': paradigm,
               'Results': helpers.lmf_tableize(table)}
    return ans
