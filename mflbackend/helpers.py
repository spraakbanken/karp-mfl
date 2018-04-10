import errors as e
from flask import request
import json
import logging
import paradigm as P
import re
import urllib.parse
import urllib.request


# KARP_BACKEND = 'https://ws.spraakbanken.gu.se/ws/karp/v4/'
KARP_BACKEND = 'http://localhost:8081/app/'


def get_lexiconconf(lexicon):
    try:
        return json.load(open('config/%s.json' % lexicon))
    except Exception as err:
        logging.exception(err)
        raise e.MflException("Could not open lexicon %s" % lexicon)


def karp_add(data, resource='saldomp', _id=None):
    # TODO must use password!
    data = {'doc': data, 'message': 'Mfl generated paradigm'}
    if _id:
        return karp_request("readd/%s/%s" % (resource, _id),
                            data=json.dumps(data).encode('utf8'))
    else:
        return karp_request("add/%s" % resource,
                            data=json.dumps(data).encode('utf8'))


def karp_bulkadd(data, resource='saldomp'):
    # TODO must use password!
    data = {'doc': data, 'message': 'Mfl candidate list'}
    return karp_request("addbulk/%s" % resource,
                        data=json.dumps(data).encode('utf8'))


def karp_delete(_id, resource='saldomp'):
    # TODO must use password!
    return karp_request("delete/%s/%s" % (resource, _id))


def karp_update(uuid, data, resource='saldomp'):
    # TODO must use password!
    data = {'doc': data, 'message': 'Mfl generated paradigm'}
    # print('data', data)
    # print('uuid', uuid)
    return karp_request("mkupdate/%s/%s" % (resource, uuid),
                        data=json.dumps(data).encode('utf8'))


def karp_query(action, query, mode='external', resource='saldomp'):
    # TODO must use password!
    if 'mode' not in query:
        query['mode'] = mode
    if 'resource' not in query and 'lexiconName' not in query:
        query['resource'] = resource
    if 'size' not in query:
        query['size'] = 1000
    logging.debug('query %s %s' % (query, type(query)))
    logging.debug('query %s %s' % (query, type(query)))
    params = urllib.parse.urlencode(query)
    logging.debug('ask karp %s %s' % (action, params))
    return karp_request("%s?%s" % (action, params))


def karp_request(action, data=None):
    # TODO must use password!
    q = "%s/%s" % (KARP_BACKEND, action)
    logging.debug('send %s' % q)
    logging.debug('send %s' % q)
    response = urllib.request.urlopen(q, data=data).read().decode('utf8')
    logging.debug('response %s' % response)
    data = json.loads(response)
    return data


def format_inflection(lexconf, ans, kbest=0, pos='', debug=False):
    " format an inflection and report whether anything has been printed "
    out = []
    #for words, analyses in ans:
    for aindex, (score, p, v) in enumerate(ans):
        if kbest and aindex >= kbest:
            break
        res = make_table(lexconf, p, v, score, pos)
        if res is not None:
            out.append(res)
        # infl = {'paradigm': p.name, 'WordForms': [],
        #         'variables': dict(zip(range(1, len(v)+1), v)), 'score':
        #         score, 'count': p.count, 'new': False, 'lemgram': '',
        #         'partOfSpeech': pos}
        # table = p(*v)          # Instantiate table with vars from analysis
        # for form, msd in table:
        #     for tag in msd:
        #         infl['WordForms'].append({'writtenForm': form,
        #                                   'msd': tag[1]})
        # out.append(infl)
        # if debug:
        #     logging.debug("Members: %s" %
        #                   ", ".join([p(*[var[1] for var in vs])[0][0]
        #                              for vs in p.var_insts]))
    return out


#def format_simple_inflection(lexconf, ans, pos=''):
#    " format an inflection and report whether anything has been printed "
#    out = []
#    for paradigm, words, analyses in ans:
#        for aindex, (score, p, v) in enumerate(analyses):
#            logging.debug('hej %s %s' % (aindex, v))
#            res = make_table(lexconf, p, v, score, pos)
#            if res is not None:
#                out.append((score, res))
#    out.sort(reverse=True, key=lambda x: x[0])
#    return [o[1] for o in out]


def make_table(lexconf, paradigm, v, score, pos):
    try:
        #logging.debug('v %s %s' % (v, type(v)))
        infl = {'paradigm': paradigm.name, 'WordForms': [],
                'variables': dict(zip(range(1, len(v)+1), v)),
                'score': score, 'count': paradigm.count,
                'new': False, 'partOfSpeech': pos}
        logging.debug('%s:, %s' % (paradigm.name, v))
        table = paradigm(*v)  # Instantiate table with vars from analysis
        for form, msd in table:
            for tag in msd:
                infl['WordForms'].append({'writtenForm': form,
                                          'msd': tag[1]})

        infl['baseform'] = get_baseform_infl(lexconf, infl)
        #logging.debug('could use paradigm %s' % paradigm)
        return infl
    except Exception as e:
        # fails if the inflection does not work (instantiation fails)
        logging.debug('could not use paradigm %s' % paradigm.name)
        logging.exception(e)
        return None


# TODO lexicon specific
def lmf_wftableize(lexconf, paradigm, table, classes={}, baseform='',
                   identifier='', pos='', resource=''):
    def default(paradigm, table, classes, baseform, identifier, pos, reosource):
        # TODO implement something more generic?
        table = table.split(',')
        obj = {'lexiconName': resource}
        wfs = []
        for l in table:
            if '|' in l:
                form, tag = l.split('|')
            else:
                form = l
                tag = ''
            wfs.append({'writtenForm': form, 'msd': tag})
            if not baseform:
                baseform = form

        obj['WordForms'] = wfs
        form = {}
        form['identifier'] = identifier
        form['partOfSpeech'] = pos
        form['baseform'] = baseform
        form['paradigm'] = paradigm
        for key, val in classes.items():
            form[key] = val
        obj['FormRepresentations'] = [form]
        obj['used_default'] = 'true'
        return obj

    func = extra_src(lexconf, 'lmf_wftabelize', default)

    return func(paradigm, table, classes, baseform, identifier, pos, resource)


def identifier2pos(lexconf, lemgram):
    func = extra_src(lexconf, 'get_pos',
                     lambda x: re.search('.*\.\.(.*?)\..*', x))
    return func(lemgram)


def get_baseform_infl(lexconf, infl):
    func = extra_src(lexconf, 'get_baseform',
                     lambda infl: infl['WordForms'][0]['writtenForm'])
    return func(entry=infl)


def get_baseform(lexconf, lemgram):
    func = extra_src(lexconf, 'get_baseform',
                     lambda x: x.split('\.')[0])
    return func(lemgram=lemgram)


def extra_src(lexconf, funcname, default):
    import importlib
    # If importing fails, try with a different path.
    logging.debug('look for %s' % (funcname))
    logging.debug('file: %s' % lexconf['src'])
    try:
        classmodule = importlib.import_module(lexconf['src'])
        logging.debug('\n\ngo look in %s\n\n' % classmodule)
        func = getattr(classmodule, funcname)
        return func
    except:
        return default


def lmf_tableize(table, paradigm=None, pos='', score=0):
    table = table.split(',')
    obj = {'score': score, 'paradigm': '', 'new': True}
    if paradigm is not None:
        obj['variables'] = paradigm.var_insts[0]
        obj['paradigm'] = paradigm.name
    wfs = []
    for l in table:
        if '|' in l:
            form, tag = l.split('|')
        else:
            form = l
            tag = 'X'
        wfs.append({'writtenForm': form, 'msd': tag})

    obj['WordForms'] = wfs
    obj['identifier'] = ''
    obj['partOfSpeech'] = pos
    obj['count'] = 0
    return obj


def tableize(table, add_tags=True, fill_tags=True):
    thistable, thesetags = [], []
    table = table.split(',')
    # if len(table[0].split('|')) < 2 or table[0].split('|') != "identifier":
    #     thistable.append(table[0].split('|')[0])
    #     thistag = [("msd", "identifier")] # if add_tags else ''
    #     thesetags.append(thistag)

    for l in table:
        if '|' in l:
            form, tag = l.split('|')
        else:
            form = l
            tag = 'tag' if add_tags else ''
        thistable.append(form)
        if add_tags or tag:
            thesetags.append([("msd", tag)])
        elif fill_tags:
            thesetags.append('')
    return (thistable, thesetags)


def relevant_paradigms(paradigmdict, lexicon, pos, possible_p=[]):
    all_paras, numex, lms = paradigmdict[lexicon][pos]
    if possible_p:
        all_paras = [all_paras[p] for p in possible_p if p in all_paras]
    else:
        all_paras = list(all_paras.values())

    return all_paras, numex, lms


def load_paradigms(es_result, lexconf):
    paras = [hit['_source'] for hit in es_result['hits']['hits']]
    paradigms = P.load_json(paras)
    return paradigms


def compile_list(query, searchfield, querystr, lexicon, show,
                 size, start, mode):
    query = search_q(query, searchfield, querystr, lexicon)
    res = karp_query('minientry',
                     {'q': query, 'show': show, 'size': size,
                      'start': start, 'mode': mode,
                      'resource': lexicon})
    ans = []
    for hit in res["hits"]["hits"]:
        ans.append(hit["_source"])
    return ans


def check_identifier(_id, field, resource, mode):
    q = {'size': 0, 'q': 'extended||and|%s.search|equals|%s' % (field, _id)}
    res = karp_query('query', q, mode=mode, resource=resource)
    if res['hits']['total'] > 0:
        raise e.MflException("Identifier %s already in use" % _id)


def search_q(query, searchfield, q, lexicon):
    if q:
        logging.debug('q is %s' % q)
        query.append('and|%s.search|equals|%s' % (searchfield, q))
    if query:
        query = 'extended||' + '||'.join(query)
    else:
        query = 'extended||and|lexiconName|equals|%s' % lexicon
    return query


def multi_query(lexconf, fields, query, fullquery):
    for ix, field in enumerate(fields):
        q = query[ix]
        fullquery.append('and|%s.search|equals|%s' % (lexconf.get(field, field), q))


def make_candidate(lexicon, lemgram, table, paradigms, pos, kbest=5):
    obj = {}
    form = {'identifier': lemgram, 'partOfSpeech': pos, 'baseform': table[0]}
    obj['FormRepresentations'] = [form]
    obj['lexiconName'] = lexicon
    obj['CandidateParadigms'] = []
    obj['WordForms'] = []
    # attested forms
    for form in table[1:]:
        if '|' in form:
            form, tag = form.split('|')
            wf = {'writtenForm': form, 'msd': tag}
        else:
            wf = {'writtenForm': form}
        obj['WordForms'].append(wf)
    cands = []
    for score, p, v in paradigms:
         cand = {}
         cand['name'] = p.name
         cand['uuid'] = p.uuid
         cand['VariableInstances'] = dict(enumerate(v, 1))
         cand['score'] = score
         cands.append((score, cand))

    cands.sort(reverse=True, key=lambda x: x[0])
    if cands:
        obj['maxScore'] = cands[0][0]

    obj['CandidateParadigms'] = [c for score, c in cands[:kbest]]
    return obj


def read_one_pos(lexconf):
    return read_pos(lexconf)[0]


def read_pos(lexconf):
    pos = request.args.get('pos', '')
    partofspeech = request.args.get('partOfSpeech', lexconf['defaultpos'])
    pos = pos or partofspeech
    return pos.split(',')


def read_restriction(lexconf):
    restrict = request.args.get('restrict_to_baseform')
    print('restrict???', restrict)
    if restrict is None:
        return lexconf['restrict_to_baseform']
    return restrict in ['True', 'true', True]


def get_bucket(bucket, res, lexconf):
    return res['aggregations']['q_statistics'][bucket]['buckets']


def get_classbucket(iclass, res, lexconf):
    return get_bucket(lexconf['inflectionalclass'][iclass], res, lexconf)
    # return res['aggregations']['q_statistics'][lexconf['inflectionalclass'][iclass]]['buckets']
