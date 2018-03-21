import json
import logging
import urllib


# KARP_BACKEND = 'https://ws.spraakbanken.gu.se/ws/karp/v4/'
KARP_BACKEND = 'http://localhost:8081/app/'



def get_lexiconconf(lexicon):
    # TODO
    return json.load(open('config/saldomp.json'))


def karp_query(action, query, mode='external', resource='saldomp'):
    query['mode'] = mode
    query['resource'] = resource
    query['size'] = 1000
    logging.debug('query %s %s' % (query, type(query)))
    params = urllib.parse.urlencode(query)
    logging.debug('ask karp %s %s' % (action, params))
    return karp_request("%s?%s" % (action, params))


def karp_request(action):
    q = "%s/%s" % (KARP_BACKEND, action)
    logging.debug('send %s' % q)
    response = urllib.request.urlopen(q).read().decode('utf8')
    logging.debug('response %s' % response)
    data = json.loads(response)
    return data


def format_simple_inflection(ans):
    " format an inflection and report whether anything has been printed "
    out = []
    for lemgram, words, analyses in ans:
        for aindex, (score, p, v) in enumerate(analyses):
            try:
                print('v %s %s' % (v, type(v)))
                infl = {'paradigm': p.name, 'WordForms': [],
                        'variables': dict(zip(range(1, len(v)+1), v)),
                        'score': score}
                print(lemgram + ':')
                print('hej %s %s' % (aindex, v))
                table = p(*v)  # Instantiate table with vars from analysis
                for form, msd in table:
                    for tag in msd:
                        infl['WordForms'].append({'writtenForm': form,
                                                  'msd': tag[1]})
                out.append((score, infl))
            except Exception as e:
                # fails if the inflection does not work (instantiation fails)
                print(e)
    out.sort(reverse=True, key=lambda x: x[0])
    return [o[1] for o in out]


def format_inflection(ans, kbest, debug=False):
    " format an inflection and report whether anything has been printed "
    out = []
    for words, analyses in ans:
        for aindex, (score, p, v) in enumerate(analyses):
            infl = {'paradigm': p.name, 'WordForms': [],
                    'variables': dict(zip(range(1, len(v)+1), v)),
                    'score': score}
            if aindex >= kbest:
                break
            table = p(*v)          # Instantiate table with vars from analysis
            for form, msd in table:
                for tag in msd:
                    infl['WordForms'].append({'writtenForm': form,
                                              'msd': tag[1]})
            out.append(infl)

            if debug:
                print("Members:", ", ".join([p(*[var[1] for var in vs])[0][0] for vs in p.var_insts]))
    return out


def lmf_tableize(table, paradigm=None, score=0):
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
    return []


def tableize(table, add_tags=True):
    thistable, thesetags = [], []
    table = table.split(',')
    if len(table[0].split('|')) > 2 or table[0].split('|') != "identifier":
        thistable.append(table[0].split('|')[0])
        thistag = "msd=identifier" if add_tags else ''
        thesetags.append(thistag)

    for l in table:
        if '|' in l:
            form, tag = l.split('|')
        else:
            form = l
            tag = 'tag' if add_tags else ''
        thistable.append(form)
        thesetags.append("msd=%s" % tag if tag else '')
    return (thistable, thesetags)

def relevant_paradigms(paradigmdict, lexicon, pos):
    try:
        return paradigmdict[lexicon][pos]
    except:
        e = Exception()
        e.message = "No word class %s for lexicon %s" % (pos, lexicon)
        raise e
