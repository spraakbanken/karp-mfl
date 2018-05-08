import configmanager as C
from flask import request
import errors as e
import helpers
import logging
import uuid

import morphparser as mp
import pextract as pex

#########
# Remove these?
def update_paradigm(pid, paradigm, paradigms):
    # TODO send_to_karp()
    # update language model
    paradigms[pid] = paradigm


def reload_paradigms(paradigms):
    pass


def load_paradigms(paradigms):
    pass
#########


def add_paradigm(presource, lresource, pid, paradigm, paradigms, identifier,
                 pos, classes, table, lexconf):
    logging.debug('id %s, para %s.\n classes %s, identifier %s' %
                  (pid, paradigm, classes, identifier))
    paradigm.set_id(pid)
    puuid = str(uuid.uuid1())
    paradigm.set_uuid(puuid)
    paradigm.set_lexicon(presource)
    paradigm.set_pos(pos)
    paradigm._entries = 1
    for key, val in classes.items():
        paradigm.add_class(key, [val])
    logging.debug('uuid %s' % puuid)
    # Add to our in memory paradigms
    if lresource not in paradigms:
        paradigms[lresource] = {}
    if pos not in paradigms[lresource]:
        paradigms[lresource][pos] = {}
    all_paras, numex, lms, alpha = paradigms[lresource].get(pos, ({}, 0, None))
    alpha = mp.extend_alphabet(paradigm, alpha)
    mp.lms_paradigm(paradigm, lms, alpha, lexconf["ngramorder"], lexconf["ngramprior"])
    all_paras[puuid] = paradigm
    paradigms[lresource][pos] = (all_paras, numex+1, lms, alpha)
    helpers.karp_add(paradigm.jsonify(), resource=presource, _id=puuid)


def add_word_to_paradigm(presource, lemgram, inst, classes,
                         paradigm, table, paradigms, lresource, pos):
    logging.debug('old count %s' % paradigm.count)
    var_inst = [('first-attest', lemgram)]+list(enumerate(inst, 1))
    paradigm.add_var_insts(var_inst)
    paradigm.members.append(lemgram)
    for key, val in classes.items():
        paradigm.add_class(key, [val])
    paradigm.count += 1
    paradigm.set_lexicon(presource)
    all_paras, numex, lms, alpha = paradigms[lresource].get(pos, ({}, 0, None))
    alpha = mp.extend_alphabet(paradigm, alpha)
    paradigms[lresource][pos] = (all_paras, numex, lms, alpha)
    logging.debug('new count %s' % paradigm.count)
    helpers.karp_update(paradigm.uuid, paradigm.jsonify(), resource=presource)


def remove_word_from_paradigm(identifier, pos, paradigm, lexconf, paradigms):
    logging.debug('old count %s' % paradigm.count)
    # remove variable_instances
    for ix, var_inst in enumerate(paradigm.var_insts):
        if dict(var_inst).get('first-attest', '') == identifier:
            paradigm.var_insts.pop(ix)
            break

    # remove from members
    try:
        paradigm.members.remove(identifier)
    except:
        logging.warning('identifier %s cannot not be removed, since it was not present in %s'
                        % (identifier, paradigm.p_id))

    # remove from relevant classes
    paradigm.empty_classes()
    # get all classes from all other words, add to paradigm:
    q = 'extended||and|paradigm|equals|%s||not|%s|equals|%s'\
        % (paradigm.p_id, lexconf['identifier'], identifier)
    for iclass in lexconf['inflectionalclass'].keys():
        res = helpers.karp_query('statlist',
                                 {'q': q, 'size': 1000,
                                  'buckets': '%s.bucket' % iclass},
                                 resource=lexconf['lexiconName'],
                                 mode=lexconf['lexiconMode'])
        paradigm.add_class(iclass, [cl[0] for cl in res.get('stattable', [])])

    # decrease count
    paradigm.count -= 1
    logging.debug('new count %s' % paradigm.count)
    if paradigm.count > 0:
        # TODO remove from alphabet
        helpers.karp_update(paradigm.uuid, paradigm.jsonify(), resource=lexconf['paradigmlexiconName'])
    else:
        remove_paradigm(paradigm, lexconf['paradigmlexiconName'], paradigms,
                        pos, lexconf['lexiconName'])


def remove_paradigm(paradigm, resource, paradigmdict, pos, lresource):
    helpers.karp_delete(paradigm.uuid, resource)
    all_paras, numex, lms, alpha = paradigmdict[lresource].get(pos, ({}, 0, None))
    del all_paras[paradigm.uuid]
    del lms[paradigm.uuid]
    alpha = mp.paradigms_to_alphabet(all_paras.values())
    paradigmdict[lresource][pos] = all_paras, numex-1, lms, alpha


def inflect_table(table, settings, lexconf, pos='', lemgram='', kbest=10, match_all=False):
    baseform = helpers.read_restriction(lexconf)
    fill_tags = '|' in table
    pex_table = helpers.tableize(table, add_tags=False, fill_tags=fill_tags)
    logging.debug('inflect forms %s msd %s. Restricted %s' %
                  (pex_table[0], pex_table[1], baseform))
    res = []
    if settings[0]:
        # print('got some paradigms', len(settings[0]))
        res = mp.test_paradigms(pex_table, *settings, returnempty=False,
                                baseform=baseform, match_all=match_all)
    # logging.debug('res %s' % res)
    if res:
        # print('got some results', len(res))
        ans = {"Results": helpers.format_inflection(lexconf, res, kbest=kbest,
                                                    pos=pos, lemgram=lemgram)}
    else:
        logging.debug('invent!', len(res))
        pex_table = helpers.tableize(table, add_tags=True, identifier=lemgram)
        paradigm = pex.learnparadigms([pex_table])[0]
        logging.debug('learned %s' % paradigm)
        ans = {'Results': [helpers.lmf_tableize(lexconf, table,
                                                paradigm=paradigm,
                                                pos=pos,
                                                lemgram=lemgram)]}
    return ans


def make_new_table(lexconf, paradigmdict, newword=False):
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = helpers.read_one_pos(lexconf)
    paradigm = request.args.get('paradigm', '')
    identifier = request.args.get('identifier', '')
    baseform = request.args.get('baseform', '')
    # check that the table's identier is unique
    # if it is new: make sure that it doesn't already exists.
    #    otherwise: construct a new one
    # if it is not new: make sure that it does exists.
    #    otherwise: fail
    ok = helpers.check_identifier(identifier, lexconf['identifier'],
                                  lexconf['lexiconName'], lexconf['lexiconMode'],
                                  unique=newword, fail=not newword)
    if not ok:
        logging.debug('identifier %s not ok' % (identifier))
        word = baseform or helpers.get_baseform(lexconf, identifier)
        identifier = helpers.make_identifier(lexconf, word, pos)
        logging.debug('\t...use %s' % (identifier))

    for name, field in [('identifier', identifier), ('paradigm', paradigm), ('partOfSpeech', pos)]:
        if not field:
            raise e.MflException("Both identifier, partOfSpeech and paradigm must be given!",
                                 code="unknown_%s" % name)
    classes = request.args.get('class', '') or request.args.get('classes', '')
    is_new = request.args.get('new')
    is_new = is_new in ['True', 'true', True]
    try:
        logging.debug('make classes: %s' % classes)
        if classes:
            classes = dict([c.split(':') for c in classes.split(',')])
        else:
            classes = {}
    except Exception as e1:
        logging.warning('Could not parse classes')
        logging.error(e1)
        raise e.MflException("Could not parse classes. Format should be 'classname:apa,classname2:bepa'" % (classes),
                             code="unparsable_class")
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    if is_new and paradigm in [p.name for p in paras]:
        raise e.MflException("Paradigm name %s is already used" % (paradigm),
                             code="unique_paradigm")

    pex_table = helpers.tableize(table, add_tags=False)
    wf_table = helpers.lmf_wftableize(lexconf, paradigm, table, classes,
                                      baseform=baseform, identifier=identifier,
                                      pos=pos, resource=lexconf['lexiconName'])
    if not is_new:
        logging.debug('not new, look for %s' % paradigm)
        fittingparadigms = [p for p in paras if p.p_id == paradigm]
        if not fittingparadigms:
            raise e.MflException("Could not find paradigm %s" % paradigm,
                                 code="unknown_paradigm")

    else:
        # TODO If an paradigm is already fitting, refuse to add as new?
        fittingparadigms = paras
        # check that this is a new name
        helpers.check_identifier(paradigm, 'MorphologicalPatternID',
                                 lexconf['paradigmlexiconName'],
                                 lexconf['paradigmMode'])

    logging.debug('fitting %s' % fittingparadigms)
    logging.debug('pex_table %s %s' % pex_table)
    ans = mp.test_paradigms(pex_table, fittingparadigms, numex, lms,
                            C.config["print_tables"], C.config["debug"],
                            lexconf["pprior"], returnempty=False,
                            match_all=True)
    if not is_new and len(ans) < 1:
        # print('ans', ans)
        logging.warning("Could not inflect %s as %s" % (table, paradigm))
        raise e.MflException("Table can not belong to paradigm %s" % (paradigm),
                             code="inflect_problem")
    if is_new and len(ans) > 0:
        # print('ans', ans)
        logging.warning("Could inflect %s as %s" % (table, ans[0][1].p_id))
        raise e.MflException("Table should belong to paradigm %s" % (ans[0][1].p_id),
                             code="inflect_problem")

    if not ans:
        # print(ans)
        pex_table = helpers.tableize(table, add_tags=False, identifier=identifier)
        para = pex.learnparadigms([pex_table])[0]
        # print('para is', para)
        # TODO bug? should be 1:
        v = [var for ix, var in para.var_insts[0][:1]]
        add_paradigm(lexconf['paradigmlexiconName'],
                     lexconf['lexiconName'], paradigm, para,
                     paradigmdict, identifier, pos, classes, wf_table,
                     lexconf)

    else:
        # TODO used to be ans[0][0], see slack 13:26 12/4
        score, para, v = ans[0]
        add_word_to_paradigm(lexconf['paradigmlexiconName'],
                             identifier, v, classes, para, wf_table,
                             paradigmdict, lexconf['lexiconName'], pos)

    return identifier, wf_table, para, v, classes
