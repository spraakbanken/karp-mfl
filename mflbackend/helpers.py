import base64
import configmanager as C
import errors as e
from flask import request
import json
import logging
from hashlib import md5
import paradigm as P
import re
import urllib.parse
import urllib.request
import uuid


def es_total(res):
    return res['hits']['total']


def es_first_source(res):
    return res['hits']['hits'][0]['_source']


def es_first_id(res):
    return res['hits']['hits'][0]['_id']


def es_all_source(res):
    return [hit['_source'] for hit in res['hits']['hits']]


def es_get_hits(res):
    return res['hits']['hits']


def es_get_id(hit):
    return hit['_id']


def es_get_source(hit):
    return hit['_source']


def get_lexiconconf(lexicon):
    try:
        return json.load(open(C.config['lexiconpath'][lexicon]))
    except Exception as err:
        logging.exception(err)
        raise e.MflException("Could not open lexicon %s" % lexicon,
                             code="unknown_lexicon")


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
    return karp_request("delete/%s/%s" % (resource, _id))


def karp_update(uuid, data, resource='saldomp'):
    data = {'doc': data, 'message': 'Mfl generated paradigm'}
    # print('data', data)
    # print('uuid', uuid)
    return karp_request("mkupdate/%s/%s" % (resource, uuid),
                        data=json.dumps(data).encode('utf8'))


def karp_query(action, query, mode='external', resource='saldomp', user=''):
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
    return karp_request("%s?%s" % (action, params), user=user)


def karp_request(action, data=None, user=''):
    q = "%s/%s" % (C.config['KARP_BACKEND'], action)

    if user:
       userpw = user
    else:
        try:
            auth = request.authorization
            user, pw = auth.username, auth.password
        except:
            user, pw = 'mfl', 'mfl'
        userpw = '%s:%s' % (user, pw)
    basic = base64.b64encode(userpw.encode())
    req = urllib.request.Request(q, data=data)
    req.add_header('Authorization', 'Basic %s' % basic.decode())

    logging.debug('send %s' % q)
    response = urllib.request.urlopen(req).read().decode('utf8')
    return json.loads(response)


def format_inflection(lexconf, ans, kbest=0, pos='', lemgram='', debug=False):
    " format an inflection and report whether anything has been printed "
    out = []
    for aindex, (score, p, v) in enumerate(ans):
        if kbest and aindex >= kbest:
            break
        res = make_table(lexconf, p, v, score, pos, lemgram=lemgram)
        if res is not None:
            out.append(res)
    return out


def make_table(lexconf, paradigm, v, score, pos, lemgram=''):
    try:
        # logging.debug('v %s %s' % (v, type(v)))
        infl = {'paradigm': paradigm.name, 'WordForms': [],
                'variables': dict(zip(range(1, len(v)+1), v)),
                'score': score, 'count': paradigm.count,
                'new': False, 'partOfSpeech': pos,
                'identifier': lemgram}
        logging.debug('%s:, %s' % (paradigm.name, v))
        table = paradigm(*v)  # Instantiate table with vars from analysis
        logging.debug('table %s' % (table))
        for form, msd in table:
            for tag in msd:
                infl['WordForms'].append({'writtenForm': form,
                                          'msd': tag[1]})
            if not msd:
                infl['WordForms'].append({'writtenForm': form})

        infl['baseform'] = get_baseform_infl(lexconf, infl)
        # logging.debug('could use paradigm %s' % paradigm)
        return show_inflected(lexconf, infl)
    except Exception as e:
        # fails if the inflection does not work (instantiation fails)
        logging.debug('could not use paradigm %s' % paradigm.name)
        logging.exception(e)
        return None


def show_inflected(lexconf, entry):
    func = extra_src(lexconf, 'show_inflected', lambda x: x)
    return func(entry)


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

    func = extra_src(lexconf, 'lmf_wftableize', default)

    return func(paradigm, table, classes, baseform, identifier, pos, resource)


def identifier2pos(lexconf, lemgram):
    func = extra_src(lexconf, 'get_pos',
                     lambda x: re.search('.*\.\.(.*?)\..*', x))
    return func(lemgram)


def get_baseform_infl(lexconf, infl):
    func = extra_src(lexconf, 'get_baseform',
                     lambda entry=infl: entry['WordForms'][0]['writtenForm'])
    return func(entry=infl)


def get_baseform(lexconf, lemgram):
    func = extra_src(lexconf, 'get_baseform',
                     lambda x: x.split('\.')[0])
    return func(lemgram=lemgram)


def extra_src(lexconf, funcname, default):
    import importlib
    # If importing fails, try with a different path.
    logging.debug('look for %s' % (funcname))
    try:
        logging.debug('file: %s' % lexconf['src'])
        classmodule = importlib.import_module(lexconf['src'])
        logging.debug('\n\ngo look in %s\n\n' % classmodule)
        func = getattr(classmodule, funcname)
        return func
    except:
        return default


def lmf_tableize(lexconf, table, paradigm=None, pos='', lemgram='', score=0):
    table = table.split(',')
    obj = {'score': score, 'paradigm': '', 'new': True}
    if paradigm is not None:
        obj['variables'] = dict([var for var in paradigm.var_insts[0][1:]])
        obj['paradigm'] = paradigm.name
        obj['pattern'] = paradigm.jsonify()
    wfs = []
    for l in table:
        if '|' in l:
            form, tag = l.split('|')
        else:
            form = l
            tag = 'X'
        wfs.append({'writtenForm': form, 'msd': tag})

    obj['WordForms'] = wfs
    func = extra_src(lexconf, 'get_baseform', '')
    obj['baseform'] = func(obj)
    obj['partOfSpeech'] = pos
    obj['count'] = 0
    obj['identifier'] = lemgram
    return show_inflected(lexconf, obj)


def tableize(table, add_tags=True, fill_tags=True, identifier=''):
    thistable, thesetags = [], []
    table = table.split(',')
    # if len(table[0].split('|')) < 2 or table[0].split('|') != "identifier":
    #     thistable.append(table[0].split('|')[0])
    #     thistag = [("msd", "identifier")] # if add_tags else ''
    #     thesetags.append(thistag)

    if identifier:
        thistable.append(identifier)
        thesetags.append([("msd", "identifier")])
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
            thesetags.append([])
    return (thistable, thesetags)


def tableize_obj(obj, add_tags=True, fill_tags=True, identifier=''):
    thistable, thesetags = [obj['baseform']], ['']
    if identifier:
        thistable.append(identifier)
        thesetags.append([("msd", "identifier")])
    for wf in obj['WordForms']:
        thistable.append(wf['writtenForm'])
        tag = wf.get('msd', 'tag' if add_tags else '')
        if add_tags or tag:
            thesetags.append([("msd", tag)])
        elif fill_tags:
            thesetags.append('')
        tag = 'tag' if add_tags else ''
    return (thistable, thesetags)


def relevant_paradigms(paradigmdict, lexicon, pos, possible_p=[]):
    try:
        all_paras, numex, lms, alpha = paradigmdict[lexicon].get(pos, ({}, 0, None, ''))
        if possible_p:
            # print('search for %s (%s)' % (possible_p[0], all_paras))
            all_paras = [all_paras[p] for p in possible_p if p in all_paras]
        else:
            all_paras = list(all_paras.values())

        return all_paras, numex, lms
    except:
        raise e.MflException("Could not read lexicon %s" % lexicon,
                             code="unknown_lexicon")


def load_paradigms(es_result, lexconf):
    paras = es_all_source(es_result)
    paradigms = P.load_json(paras)
    return paradigms


def compile_list(query, searchfield, querystr, lexicon, show,
                 size, start, mode, isfilter=False):
    query = search_q(query, searchfield, querystr, lexicon, isfilter=isfilter)
    res = karp_query('minientry',
                     {'q': query, 'show': show, 'size': size,
                      'start': start, 'mode': mode,
                      'resource': lexicon})
    ans = es_all_source(res)
    return {"ans": ans, "total": es_total(res)}


def get_current_paradigm(_id, pos, lexconf, paradigmdict):
    field = lexconf['identifier']
    q = {'size': 1, 'q': 'extended||and|%s.search|equals|%s' %
         ('first-attest', _id),
         'show': '_id'}
    res = karp_query('query', q, mode=lexconf['paradigmMode'],
                     resource=lexconf['paradigmlexiconName'])
    if not es_total(res) > 0:
        raise e.MflException("Identifier %s not found" % _id,
                             code="unknown_%s" % field)

    p_id = es_first_source(res)['_uuid']
    logging.debug('p_id is %s' % p_id)
    paras, numex, lms = relevant_paradigms(paradigmdict, lexconf['lexiconName'],
                                           pos, possible_p=[p_id])
    if not paras:
        raise e.MflException("Paradigm %s not found" % p_id,
                             code="unknown_paradigm")
    return paras[0]


def get_es_identifier(_id, field, resource, mode):
    q = {'size': 1, 'q': 'extended||and|%s.search|equals|%s' % (field, _id)}
    res = karp_query('query', q, mode=mode, resource=resource)
    if not es_total(res) > 0:
        raise e.MflException("Identifier %s not found" % _id,
                             code="unknown_%s" % field)
    return es_first_id(res)


def check_identifier(_id, field, resource, mode, unique=True, fail=True):
    q = {'size': 0, 'q': 'extended||and|%s.search|equals|%s' % (field, _id)}
    res = karp_query('query', q, mode=mode, resource=resource)
    used = es_total(res) > 0
    ok = (used and not unique) or (not used and unique)
    if not ok and fail:
        text = 'already in use' if unique else 'not found'
        raise e.MflException("Identifier %s %s" % (_id, text),
                             code="unique_%s" % field)
    return not used


def make_identifier(lexconf, baseform, pos, lexicon='', field='', mode='', default=False):
    func = extra_src(lexconf, 'yield_identifier', None)

    if default or func is None:
        return str(uuid.uuid1())

    lexicon = lexicon or lexconf['lexiconName']
    field = field or lexconf['identifier']
    mode = mode or lexconf['lexiconMode']

    for _id in func(baseform, pos):
        if check_identifier(_id, field, lexicon, mode, fail=False):
            return _id

    raise e.MflException("Could not come up with an identifier for %s, %s in lexicon %s" %
                         (baseform, pos, lexicon),
                         code="id_generation")


def search_q(query, searchfield, q, lexicon, isfilter=False):
    if q:
        operator = 'equals' if not isfilter else 'regexp'
        if isfilter:
            q = '.*'+q+'.*'
        logging.debug('q is %s' % q)
        query.append('and|%s.search|%s|%s' % (searchfield, operator, q))
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
    obj = {'identifier': lemgram, 'partOfSpeech': pos, 'baseform': table[0]}
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
    # print('restrict???', restrict)
    if restrict is None:
        return lexconf['restrict_to_baseform']
    return restrict in ['True', 'true', True]


def get_bucket(bucket, res, lexconf):
    return res['aggregations']['q_statistics'][bucket]['buckets']


def get_bucket_count(bucket, res, lexconf):
    # print(res["aggregations"]["q_statistics"][bucket])
    return res["aggregations"]["q_statistics"][bucket]["value"]


def get_classbucket(iclass, res, lexconf):
    return get_bucket(lexconf['inflectionalclass'][iclass], res, lexconf)


def get_classcount(iclass, res, lexconf):
    return get_bucket_count(lexconf['inflectionalclass'][iclass], res, lexconf)


def firstform(table):
    return table.split(',')[0].split('|')[0]


def give_info(lexicon, identifier, id_field, mode, resource, show=[]):
    " Show information for the word infobox "
    q = 'extended||and|%s.search|equals|%s' %\
        (id_field, identifier)
    body = {'q': q}
    request = 'query'
    if show:
        body['show'] = ','.join(show)
        request = 'minientry'
    res = karp_query(request, body, mode=mode, resource=resource)
    if es_total(res) > 0:
        return es_first_source(res)
    return {}


def format_entry(lexconf, entry):
    func = extra_src(lexconf, 'show_wordentry', lambda x: x)
    return func(entry)


def authenticate(lexconf={}, action='read'):
    if action == 'checkopen':
        auth = None
    else:
        auth = request.authorization
    postdata = {"include_open_resources": "true"}
    if auth is not None:
        user, pw = auth.username, auth.password
        server = C.config['AUTH_SERVER']
        mdcode = user + pw + C.config['SECRET_KEY']
        postdata["checksum"] = md5(mdcode.encode('utf8')).hexdigest()
        postdata["username"] = user
        postdata["password"] = pw
    else:
        server = C.config['AUTH_RESOURCES']

    data = urllib.parse.urlencode(postdata).encode()
    response = urllib.request.urlopen(server, data).read().decode('utf8')
    auth_response = json.loads(response)
    lexitems = auth_response.get("permitted_resources", {})
    if action == 'checkopen':
        return [lex for lex, per in lexitems.get("lexica", {}).items()
                if per['read']]
    else:
        permissions = lexitems.get("lexica", {}).get(lexconf['wsauth_name'], {})
        if not permissions.get(action, False):
            raise e.MflException("Action %s not allowed in lexicon %s" %
                                 (action, lexconf['lexiconName']),
                                 code="authentication", status_code=401)
