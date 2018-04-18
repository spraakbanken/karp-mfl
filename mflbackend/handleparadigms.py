import helpers
import logging
import uuid

import morphparser as mp
import pextract as pex


def reload_paradigms(paradigms):
    pass


def load_paradigms(paradigms):
    pass


def add_paradigm(presource, lresource, pid, paradigm, paradigms, identifier,
                 pos, classes, table):
    logging.debug('id %s, para %s.\n classes %s, identifier %s' % (pid, paradigm, classes, identifier))
    paradigm.set_id(pid)
    puuid = str(uuid.uuid1())
    paradigm.set_uuid(puuid)
    paradigm.set_lexicon(presource)
    paradigm.set_pos(pos)
    paradigm._entries = 1
    for key, val in classes.items():
        paradigm.add_class(key, [val])
    logging.debug('uuid', puuid)
    # print(paradigm.members)
    # print(paradigm.var_insts)
    # Add to our in memory paradigms
    paradigms[puuid] = paradigm
    helpers.karp_add(paradigm.jsonify(), resource=presource, _id=puuid)
    helpers.karp_add(table, resource=lresource)


def add_word_to_paradigm(presource, lresource, lemgram, inst, classes,
                         paradigm, table):
    logging.debug('old count %s' % paradigm.count)
    var_inst = list(enumerate([lemgram]+list(inst)))
    logging.debug('old var inst %s' % paradigm.var_insts[-1])
    paradigm.var_insts.append(var_inst)
    paradigm.members.append(lemgram)
    for key, val in classes.items():
        paradigm.add_class(key, [val])
    paradigm.count += 1
    paradigm.set_lexicon(presource)
    logging.debug('new var inst %s' % paradigm.var_insts[-1])
    logging.debug('new count %s' % paradigm.count)
    helpers.karp_update(paradigm.uuid, paradigm.jsonify(), resource=presource)
    helpers.karp_add(table, resource=lresource)


def update_paradigm(pid, paradigm, paradigms):
    # TODO send_to_karp()
    paradigms[pid] = paradigm


def remove_paradigm(pid, paradigms):
    # TODO send_to_karp()
    del paradigms[pid]


def inflect_table(table, settings, lexconf, pos='', lemgram='', kbest=10):
    baseform = helpers.read_restriction(lexconf)
    fill_tags = '|' in table
    pex_table = helpers.tableize(table, add_tags=False, fill_tags=fill_tags)
    logging.debug('inflect forms %s msd %s. Restricted %s' % (pex_table[0], pex_table[1], baseform))
    res = []
    if settings[0]:
        print('got some paradigms', len(settings[0]))
        res = mp.test_paradigms(pex_table, *settings, returnempty=False, baseform=baseform)
    #logging.debug('res %s' % res)
    if res:
        print('got some results', len(res))
        ans = {"Results": helpers.format_inflection(lexconf, res, kbest=kbest,
                                                    pos=pos, lemgram=lemgram)}
               #'analyzes': res[1][0]}
    else:
        print('invent!', len(res))
        pex_table = helpers.tableize(table, add_tags=True, identifier=lemgram)
        #print('pex',pex, dir(pex))
        paradigm = pex.learnparadigms([pex_table])[0]
        logging.debug('learned %s' % paradigm)
        ans = {'Results': [helpers.lmf_tableize(table, paradigm=paradigm,
                                                pos=pos, lemgram=lemgram)]}
               #'analyzes': res}
    return ans
