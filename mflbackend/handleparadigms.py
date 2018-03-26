import helpers
import logging

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
    logging.debug('old count %s' % paradigm.count)
    var_inst = list(enumerate([lemgram]+list(inst)))
    logging.debug('old var inst %s' % paradigm.var_insts[-1])
    paradigm.var_insts.append(var_inst)
    paradigm.count += 1
    logging.debug('new var inst %s' % paradigm.var_insts[-1])
    logging.debug('new count %s' % paradigm.count)
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


def inflect_table(table, settings, pos='', kbest=10):
    pex_table = helpers.tableize(table, add_tags=False)
    logging.debug('inflect forms %s msd %s' % pex_table)
    res = mp.test_paradigms([pex_table], *settings, returnempty=False)
    logging.debug('inflect table %s, tags %s' % (pex_table[0], pex_table[1]))
    logging.debug('res %s' % res)
    if res:
        ans = {"Results": helpers.format_inflection(res, kbest=kbest, pos=pos),
               'new': False, 'analyzes': res[0][1][0]}
    else:
        # TODO  will this be the correct output?
        pex_table = helpers.tableize(table, add_tags=True)
        paradigm = pex.learnparadigms([pex_table])[0]
        logging.debug('learned %s' % paradigm)
        ans = {'Results': helpers.lmf_tableize(table, paradigm=paradigm, pos=pos),
               'new': True, 'analyses': res}
    return ans
