import errors as e
import json
import logging
import paradigm as P
import urllib.parse
import urllib.request


# KARP_BACKEND = 'https://ws.spraakbanken.gu.se/ws/karp/v4/'
KARP_BACKEND = 'http://localhost:8081/app/'


def get_lexiconconf(lexicon):
    return json.load(open('config/%s.json' % lexicon))


def karp_add(data, resource='saldomp', _id=None):
    data = {'doc': data, 'message': 'Mfl generated paradigm'}
    if _id:
        return karp_request("readd/%s/%s" % (resource, _id),
                            data=json.dumps(data).encode('utf8'))
    else:
        return karp_request("add/%s" % resource,
                            data=json.dumps(data).encode('utf8'))


def karp_update(uuid, data, resource='saldomp'):
    data = {'doc': data, 'message': 'Mfl generated paradigm'}
    # print('data', data)
    # print('uuid', uuid)
    return karp_request("mkupdate/%s/%s" % (resource, uuid),
                        data=json.dumps(data).encode('utf8'))


def karp_query(action, query, mode='external', resource='saldomp'):
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
    q = "%s/%s" % (KARP_BACKEND, action)
    logging.debug('send %s' % q)
    logging.debug('send %s' % q)
    response = urllib.request.urlopen(q, data=data).read().decode('utf8')
    logging.debug('response %s' % response)
    data = json.loads(response)
    return data


def format_simple_inflection(ans, pos=''):
    " format an inflection and report whether anything has been printed "
    out = []
    for lemgram, words, analyses in ans:
        for aindex, (score, p, v) in enumerate(analyses):
            try:
                logging.debug('v %s %s' % (v, type(v)))
                infl = {'paradigm': p.name, 'WordForms': [],
                        'variables': dict(zip(range(1, len(v)+1), v)),
                        'score': score,
                        'lemgram': '', 'partOfSpeech': pos}
                logging.debug(lemgram + ':')
                logging.debug('hej %s %s' % (aindex, v))
                table = p(*v)  # Instantiate table with vars from analysis
                for form, msd in table:
                    for tag in msd:
                        infl['WordForms'].append({'writtenForm': form,
                                                  'msd': tag[1]})
                # TODO is the baseform always the first form?
                # infl['baseform'] = infl['Wordforms'][0]['writtenForm']
                logging.debug('could use paradigm %s' % lemgram)
                out.append((score, infl))
            except Exception as e:
                # fails if the inflection does not work (instantiation fails)
                logging.debug('could not use paradigm %s' % lemgram)
                logging.exception(e)
    out.sort(reverse=True, key=lambda x: x[0])
#   X lemgram
#   X grundform
#   X paradigmnamn
#   X ordklass
#   annan klass
    return [o[1] for o in out]


# TODO who uses this? add pos to that
def format_inflection(ans, kbest, pos='', debug=False):
    " format an inflection and report whether anything has been printed "
    out = []
    for words, analyses in ans:
        for aindex, (score, p, v) in enumerate(analyses):
            infl = {'paradigm': p.name, 'WordForms': [],
                    'variables': dict(zip(range(1, len(v)+1), v)),
                    'score': score,
                    'lemgram': '', 'partOfSpeech': pos}
            if aindex >= kbest:
                break
            table = p(*v)          # Instantiate table with vars from analysis
            for form, msd in table:
                for tag in msd:
                    infl['WordForms'].append({'writtenForm': form,
                                              'msd': tag[1]})
            out.append(infl)

            if debug:
                logging.debug("Members: %s" %
                              ", ".join([p(*[var[1] for var in vs])[0][0]
                                         for vs in p.var_insts]))
    return out


# TODO lexicon specific
def lmf_wftableize(paradigm, table, classes={}, baseform='', identifier='',
                   pos='', resource=''):
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
    form['lemgram'] = identifier
    form['partOfSpeech'] = pos
    form['baseform'] = baseform
    form['paradigm'] = paradigm
    for key, val in classes.items():
        form[key] = val
    obj['FormRepresentations'] = [form]

    return obj


def lmf_tableize(table, paradigm=None, pos='', score=0):
    table = table.split(',')
    obj = {'score': score, 'paradigm': '', 'new': True}
    if paradigm is not None:
        obj['variables'] = paradigm.var_insts[0]
        obj['paradigm'] = paradigm.name
        obj['new'] = False
    wfs = []
    for l in table:
        if '|' in l:
            form, tag = l.split('|')
        else:
            form = l
            tag = 'X'
        wfs.append({'writtenForm': form, 'msd': tag})

    obj['WordForms'] = wfs
    obj['lemgram'] = ''
    obj['partOfSpeech'] = pos
    return obj


def tableize(table, add_tags=True):
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
        if add_tags:
            thesetags.append([("msd", tag)])
    return (thistable, thesetags)


def relevant_paradigms(paradigmdict, lexicon, pos, possible_p=[]):
    all_paras, numex, lms = paradigmdict[lexicon][pos]
    # print('all_paras', all_paras.keys())
    if possible_p:
        all_paras = [all_paras[p] for p in possible_p if p in all_paras]
    else:
        all_paras = list(all_paras.values())

    return all_paras, numex, lms


def load_paradigms(es_result, lexconf):
    paras = [hit['_source'] for hit in es_result['hits']['hits']]
    paradigms = P.load_json(paras)
    return paradigms


def compile_list(query, searchfield, q, lexicon, show, size, start, mode):
    query = search_q(query, searchfield, q, lexicon)
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
