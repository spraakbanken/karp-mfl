import json
import logging
import urllib


# KARP_BACKEND = 'https://ws.spraakbanken.gu.se/ws/karp/v4/'
KARP_BACKEND = 'http://localhost:8081/app/'


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
        for aindex, (p, v) in enumerate(analyses):
            try:
                infl = {'paradigm': lemgram, 'WordForms': []}
                print(lemgram + ':')
                print('hej %s %s' % (aindex, v))
                table = p(*v)  # Instantiate table with vars from analysis
                for form, msd in table:
                    for tag in msd:
                        infl['WordForms'].append({'writtenForm': form,
                                                  'msd': tag[1]})
                    infl['writtenForm'] = form
                    infl['msd'] = msd
                out.append(infl)
            except Exception as e:
                # fails if the inflection does not work (instantiation fails)
                print(e)
    return out


def format_inflection(ans, kbest, debug=False):
    " format an inflection and report whether anything has been printed "
    out = []
    for words, analyses in ans:
        for aindex, (score, p, v) in enumerate(analyses):
            infl = {'paradigm': p.name, 'WordForms': []}
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


def lmf_tableize(table):
    table = table.split(',')
    wfs = []
    for l in table:
        if '|' in l:
            form, tag = l.split('|')
        else:
            form = l
            tag = 'X'
        wfs.append({'writtenForm': form, 'msd': tag})
    return wfs


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
