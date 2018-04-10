import errors as e
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import logging
from hashlib import md5
import sys
import urllib.request

sys.path.append('/home/malin/Spraak/pextract/sbextract/src')
import morphparser as mp
import pextract as pex

import handleparadigms as handle
import helpers

app = Flask(__name__)
CORS(app)

# metadata and documentation
@app.route('/')
@app.route('/index')
def doc():
    " Get the documentation "
    return render_template('doc.html', url=request.url_root)


@app.route('/lexicon')
@app.route('/lexicon/<lex>')
def lexiconinfo(lex=''):
    " Give information about existing lexicons and their configs "
    # lex = request.args.get('lexicon', lex)
    if not lex:
        open_lex = authenticate(action='checkopen')
        res = []
        for l in json.load(open('config/lexicons.json')):
            lex = {}
            lex['name'] = l['name']
            lex['open'] = l['name'] in open_lex
            res.append(lex)
        return jsonify({"lexicons": res})
    else:
        lexconf = helpers.get_lexiconconf(lex)
        return jsonify(lexconf)


@app.route('/paradigminfo/<paradigm>')
def paradigminfo(paradigm=''):
    " Show information for the paradigm infobox "
    lexicon = request.args.get('lexicon', '')
    lexconf = helpers.get_lexiconconf(lexicon)
    authenticate(lexconf, 'read')
    paradigm = request.args.get('paradigm', paradigm)
    short = request.args.get('short', '')
    short = short in [True, 'true', 'True']
    q = 'extended||and|%s.search|equals|%s' %\
        (lexconf['extractparadigm'], paradigm)
    res = helpers.karp_query('query', {'q': q},
                             mode=lexconf['paradigmMode'],
                             resource=lexconf["paradigmlexiconName"])
    if res['hits']['total'] > 0:
        obj = res['hits']['hits'][0]['_source']
        if short:
            short_obj = {}
            short_obj['MorphologicalPatternID'] = obj['MorphologicalPatternID']
            short_obj['partOfSpeech'] = obj['_partOfSpeech']
            short_obj['entries'] = obj['_entries']
            short_obj['TransformCategory'] = obj.get('TransformCategory', {})
            obj = short_obj

        return jsonify(obj)
    else:
        return jsonify({})


@app.route('/partofspeech')
def all_pos():
    " Show all part of speech tags that the lexicon use "
    lexicon = request.args.get('lexicon', 'saldomp')
    # TODO also check in lexicon and give combined info about
    # which exist and which that have paradigms?
    logging.debug(dir(paradigmdict[lexicon]))
    logging.debug('ok %s' % list(paradigmdict[lexicon].keys()))
    return jsonify({"partOfSpeech": list(paradigmdict[lexicon].keys())})


@app.route('/defaulttable')
def defaulttable():
    " Show an empty table suiting the lexicon and part of speech "
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = helpers.read_one_pos(lexconf)
    q = 'extended||and|%s.search|equals|%s' % (lexconf['pos'], pos)
    res = helpers.karp_query('statlist',
                             {'q': q,
                              'mode': lexconf['lexiconMode'],
                              'resource': lexconf['lexiconName'],
                              'buckets': lexconf['msd']+'.bucket'
                              }
                             )

    wfs = []
    for tag in res['stat_table']:
        wfs.append({'writtenForm': '', 'msd': tag[0]})

    ans = {'WordForms': wfs, 'partOfSpeech': pos}
    return jsonify(ans)


# Test inflections
@app.route('/inflectclass')
def inflectclass():
    " Inflect a word according to a user defined category "
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    word = request.args.get('wordform', '')
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    classname = request.args.get('classname', '')
    classval = request.args.get('classval', '')
    pos = helpers.read_one_pos(lexconf)

    q = 'extended||and|%s.search|equals|%s||and|%s|equals|%s'\
        % (classname, classval, lexconf['pos'], pos)
    res = helpers.karp_query('statlist',
                             {'q': q,
                              'mode': lexconf['paradigmMode'],
                              'resource': lexconf['paradigmlexiconName'],
                              'buckets': '_id'
                              }
                             )
    possible_p = [line[0] for line in res['stat_table']]
    logging.debug('possible_p %s' % possible_p)
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon,
                                                   pos, possible_p)
    # TODO what if there are no variables?
    var_inst = sorted([(key, val) for key, val in request.args.items()
                       if key.isdigit()])
    if classname == "paradigm" and var_inst:
        # Special case: '?classname=paradigm&classval=p14_oxe..nn.1?1=katt&2=a'
        # TODO rename to extractparadigm?
        if len(paras) < 1 or len(possible_p) < 1:
            raise e.MflException("Cannot find paradigm %s" % classval)
        var_inst.sort()
        var_inst = [val for key, val in var_inst]
        logging.debug('look for %s as %s' % (classval, pos))
        if len(paras) < 1:
            raise e.MflException("Cannot find paradigm %s" % classval)
        table = helpers.make_table(lexconf, paras[0], var_inst, 0, pos)
        ans = {"Results": [table]}

    else:
        restrict_to_baseform = helpers.read_restriction(lexconf)
        res = mp.run_paradigms(paras, [word], kbest=100, pprior=ppriorv,
                               lms=lms, numexamples=numex,
                               baseform=restrict_to_baseform)
        logging.debug('generated %s results' % len(res))
        results = helpers.format_inflection(lexconf, res, pos=pos)
        ans = {"Results": results}
    # print('asked', q)
    return jsonify(ans)


@app.route('/inflect')
def inflect():
    " Inflect a word or table "
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = helpers.read_one_pos(lexconf)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    ans = handle.inflect_table(table,
                               [paras, numex, lms, config["print_tables"],
                                config["debug"], ppriorv],
                               lexconf,
                               pos=pos)
    #logging.debug('ans')
    if 'paradigm' in ans:
        ans['paradigm'] = str(ans['paradigm'])
    elif 'analyzes' in ans:
        del ans['analyzes']  # don't return this
    return jsonify(ans)


@app.route('/inflectlike')
def inflectlike():
    " Inflect a word similarly to another word "
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    word = request.args.get('wordform', '')
    like = request.args.get('like')
    logging.debug('like %s' % like)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    pos = helpers.identifier2pos(lexconf, like)
    q = 'extended||and|%s.search|equals|%s' % ('first-attest', like)
    res = helpers.karp_query('statlist',
                             {'q': q,
                              'mode': lexconf['paradigmMode'],
                              'resource': lexconf['paradigmlexiconName'],
                              'buckets': '_id'
                              }
                             )
    possible_p = [line[0] for line in res['stat_table']]
    if possible_p:
        paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon,
                                                       pos,
                                                       possible_p=possible_p)

        logging.debug('test %s paradigms' % len(paras))
        restrict_to_baseform = helpers.read_restriction(lexconf)
        res = mp.run_paradigms(paras, [word], kbest=100, pprior=ppriorv,
                               lms=lms, numexamples=numex, vbest=20,
                               baseform=restrict_to_baseform)
        result = helpers.format_inflection(lexconf, res, pos=pos)
    else:
        result = []
    ans = {"Results": result}
    return jsonify(ans)


@app.route('/list')
def listing():
    q = request.args.get('q', '')  # querystring
    s = request.args.get('c', '*')  # searchfield
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    authenticate(lexconf, 'read')
    pos = helpers.read_pos(lexconf)
    query = []
    if pos:
        query.append('and|%s|startswith|%s' % (lexconf["pos"], '|'.join(pos)))

    if s == 'class':
        classname = request.args.get('classname', '')
        query = helpers.search_q(query, classname, q, lexicon)
        res = helpers.karp_query('statlist',
                                 {'q': query,
                                  'buckets': classname+'.bucket'},
                                 mode=lexconf['lexiconMode'])
        return jsonify({"compiled_on": classname,
                        "list": res['stat_table'],
                        "fields": ["entries"]})

    if s == "wf":
        # TODO this is probably not correct, due to ES approx
        query = helpers.search_q(query, lexconf["baseform"], q, lexicon)
        res = helpers.karp_query('statlist',
                                 {'q': query,
                                  'buckets': lexconf["baseform"]+'.bucket'},
                                 mode=lexconf['lexiconMode'])
        return jsonify({"compiled_on": "wf",
                        "list": res['stat_table'],
                        "fields": ["entries"]})

    elif s == "paradigm":
        query = helpers.search_q(query, lexconf["extractparadigm"], q, lexicon)
        res = helpers.karp_query('statlist',
                                 {'q': query,
                                  'buckets': lexconf["extractparadigm"]+'.bucket'},
                                 mode=lexconf['lexiconMode'])
        return jsonify({"compiled_on": "paradigm",
                        "list": res['stat_table'],
                        "fields": ["entries"]})
    else:
        return "Don't know what to do"


@app.route('/compile')
def compile():
    querystr  = request.args.get('q', '')  # querystring
    search_f  = request.args.get('s', '')  # searchfield
    compile_f = request.args.get('c', '')  # searchfield
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    authenticate(lexconf, 'read')
    pos = helpers.read_pos(lexconf)
    size = request.args.get('size', '100')
    start = request.args.get('start', '0')
    extra = request.args.get('extra', 'true')
    extra = extra in ['True', 'true', True]
    query = []
    if ',' in search_f:
        helpers.multi_query(lexconf, search_f.split(','), querystr.split(','), query)
        search_f = ''
        querystr = ''
    print('query is now', query)

    search_f = lexconf.get(search_f, search_f)
    if pos:
        query.append('and|%s|startswith|%s' % (lexconf["pos"], '|'.join(pos)))

    if compile_f == 'class':
        classname = request.args.get('classname', '')
        if querystr:
            s_field = search_f or classname
            query.append('and|%s|equals|%s' % (s_field, querystr))
        if query:
            query = 'extended||' + '||'.join(query)
        else:
            query = 'extended||and|lexiconName|equals|%s' %\
                    lexconf['lexiconName']

        if extra:
            buckets = [classname, lexconf['extractparadigm']]
        else:
            buckets = [classname]

        res = helpers.karp_query('statistics',
                                 {'q': query,
                                  'buckets': ','.join(['%s.bucket' % b for b in buckets])},
                                 mode=lexconf['lexiconMode'])
        ans = []
        for pbucket in helpers.get_classbucket(classname, res,lexconf):
            if extra:
                pcount = len(pbucket[lexconf['extractparadigmpath']]['buckets'])
                ans.append([pbucket["key"], pcount, pbucket["doc_count"]])
            else:
                ans.append([pbucket["key"]])

        logging.debug('extra? %s' % extra)
        return jsonify({"compiled_on": classname, "stats": ans,
                        "fields": ["paradigm", "entries"]})

    elif compile_f == "wf":
        mode = lexconf['lexiconMode']
        #if querystr:
        s_field = search_f or lexconf["baseform"]
        #else:
        #    s_field = search_f
        ans = helpers.compile_list(query, s_field, querystr, lexicon,
                                   lexconf["show"], size, start, mode)
        out = []
        def default(obj):
            return [obj['baseform']], ['baseform']
        func = helpers.extra_src(lexconf, 'make_overview', default)
        for ans in ans:
            row, fields = func(ans)
            out.append(row)

        return jsonify({"compiled_on": "wordforms", "stats": out,
                        "fields": fields})

    elif compile_f == "paradigm":
        # TODO no need to look in config for this, it should always be the same
        # if querystr:
        s_field = search_f or lexconf["extractparadigm"]
        # else:
        #     s_field = search_f
        show = ','.join([lexconf['extractparadigm'],
                        'TransformCategory',
                        '_entries'])
        lexicon = lexconf['paradigmlexiconName']
        mode = lexconf['paradigmMode']
        ans = helpers.compile_list(query, s_field, querystr, lexicon, show,
                                   size, start, mode)
        res = []
        iclasses = []
        for hit in ans:
            iclasses = []  # only need one instance
            stats = [hit['MorphologicalPatternID']]
            for iclass in lexconf['inflectionalclass'].keys():
                stats.append(len(hit['TransformCategory'].get(iclass, [])))
                iclasses.append(iclass)
            stats.append(hit['_entries'])
            res.append(stats)
        return jsonify({"compiled_on": "paradigm", "stats": res,
                        "fields": iclasses+['entries']})

    else:
        raise e.MflException("Don't know what to do")


# Update
@app.route('/renameparadigm')
def renameparadigm():
    # TODO!
    return "Not implemented"


@app.route('/addtable')
def add_table():
    # TODO see config for needed and possible fields
    # or is that not needed?
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    authenticate(lexconf, 'write')
    table = request.args.get('table', '')
    pos = helpers.read_one_pos(lexconf)
    paradigm = request.args.get('paradigm', '')
    # check that the table's identier is unique
    identifier = request.args.get('identifier', '')
    helpers.check_identifier(identifier, lexconf['identifier'],
                             lexconf['lexiconName'], lexconf['lexiconMode'])
    if not identifier or not paradigm or not pos:
        raise e.MflException("Both identifier, partOfSpeech and paradigm must be given!")
    classes = request.args.get('class', '')
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
        raise e.MflException("Could not parse classes. Format should be 'classname:apa,classname2:bepa'" % (classes))
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    if is_new and paradigm in [p.name for p in paras]:
        raise e.MflException("Paradigm name %s is already used" % (paradigm))

    pex_table = helpers.tableize(table, add_tags=False)
    wf_table = helpers.lmf_wftableize(lexconf, paradigm, table, classes,
                                      baseform='', identifier=identifier,
                                      pos=pos, resource=lexconf['lexiconName'])
    if not is_new:
        logging.debug('not new, look for %s' % paradigm)
        fittingparadigms = [p for p in paras if p.p_id == paradigm]
        if not fittingparadigms:
            raise e.MflException("Could not find paradigm %s" % paradigm)

    else:
        # TODO If an paradigm is already fitting, refuse to add as new?
        fittingparadigms = paras
        # check that this is a new name
        helpers.check_identifier(paradigm, 'MorphologicalPatternID',
                                 lexconf['paradigmlexiconName'],
                                 lexconf['paradigmMode'])

    logging.debug('fitting', fittingparadigms)
    ans = mp.test_paradigms(pex_table, fittingparadigms, numex, lms,
                            config["print_tables"], config["debug"],
                            lexconf["pprior"], returnempty=False,
                            match_all=True)
    if not is_new and len(ans) < 1:
        # print('ans', ans)
        logging.warning("Could not inflect %s as %s" % (table, paradigm))
        raise e.MflException("Table can not belong to paradigm %s" % (paradigm))

    if not ans:
        # print(ans)
        para = pex.learnparadigms([pex_table])[0]
        # print('para is', para)
        v = para.var_insts
        handle.add_paradigm(lexconf['paradigmlexiconName'],
                            lexconf['lexiconName'], paradigm, para, paras,
                            identifier, pos, classes, wf_table)
    else:
        score, para, v = ans[0][0]
        handle.add_word_to_paradigm(lexconf['paradigmlexiconName'],
                                    lexconf['lexiconName'], identifier, v,
                                    classes, para, wf_table)

    return jsonify({'paradigm': para.name, 'identifier': identifier,
                    'var_inst': dict(enumerate(v, 1)), 'classes': classes,
                    'pattern': para.pattern(), 'partOfSpeech': pos,
                    'members': para.count})


@app.route('/addcandidates', methods=['POST'])
def addcandidates():
    '''  katt..nn.1
         hund..nn.1,hundar|pl indef nom
         mås..nn.2,måsars
    '''
    data = request.get_data().decode()  # decode from bytes
    logging.debug('data %s' % data)
    tables = data.split('\n')
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = helpers.read_one_pos(lexconf)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    authenticate(lexconf, 'write')
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    to_save = []
    for table in tables:
        if not table:
            continue
        logging.debug('table %s' % table)
        forms = table.split(',')
        lemgram = forms[0]
        forms = [helpers.get_baseform(lexconf, lemgram)] + forms[1:]
        pex_table = helpers.tableize(','.join(forms), add_tags=False)
        logging.debug('inflect forms %s msd %s' % pex_table)
        restrict_to_baseform = helpers.read_restriction(lexconf)
        res = mp.test_paradigms(pex_table, paras, numex, lms,
                                config["print_tables"], config["debug"],
                                ppriorv, returnempty=False,
                                baseform=restrict_to_baseform)
        to_save.append(helpers.make_candidate(lexconf['candidatelexiconName'],
                                              lemgram, forms, res, pos))
    logging.debug('will save %s' % to_save)

    helpers.karp_bulkadd(to_save, resource=lexconf['candidatelexiconName'])
    return jsonify({'saved': to_save,
                    'candidatelexiconName': lexconf['candidatelexiconName']})


@app.route('/candidatelist')
def candidatelist():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    authenticate(lexconf, 'read')
    pos = helpers.read_pos(lexconf)
    q = 'extended||and|%s.search|equals|%s' % (lexconf['pos'], '|'.join(pos))
    res = helpers.karp_query('query', query={'q': q},
                             mode=lexconf['candidateMode'],
                             resource=lexconf['candidatelexiconName'])
    return jsonify({"candidates": [hit['_source'] for hit in res['hits']['hits']]})


@app.route('/removecandidate')
@app.route('/removecandidate/<_id>')
def removecandidate(_id=''):
    ''' Either use this with the ES id:
        /removecandidate/ABC83Z
        or with the lexcion's identifiers
        /removecandidate?identifier=katt..nn.1
    '''
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    authenticate(lexconf, 'write')
    if not _id:
        try:
            identifier = request.args.get('identifier', '')
            q = 'extended||and|%s.search|equals|%s' % (lexconf['identifier'], identifier)
            res = helpers.karp_query('query', query={'q': q},
                                     mode=lexconf['candidateMode'],
                                     resource=lexconf['candidatelexiconName'])
            _id = res['hits']['hits'][0]['_id']
        except Exception as e1:
            logging.error(e1)
            raise e.MflException("Could not find candidate %s" % identifier)
    return jsonify({"deleted": helpers.karp_delete(_id, lexconf['candidatelexiconName'])})


@app.route('/recomputecandidates')
# ￼`'/recomputecandidates?pos=nn&lexicon=saldomp'`
def recomputecandiadtes():
    # TODO
    pass


def read_paradigms(lexicon, pos, mode):
    # get all paradigms from ES
    query = {'size': 10000, 'q': 'extended||and|pos|equals|%s' % pos}
    res = helpers.karp_query('query', query, mode=mode, resource=lexicon)
    return [hit['_source'] for hit in res['hits']['hits']]


def update_model(lexicon, pos, paradigmdict, lexconf):
    paras = read_paradigms(lexconf['paradigmlexiconName'], pos,
                           lexconf['paradigmMode'])
    paras, numex, lms = mp.build(paras, lexconf["ngramorder"],
                                 lexconf["ngramprior"],
                                 lexicon=lexconf['paradigmlexiconName'],
                                 inpformat='json',
                                 pos=pos,
                                 small=False)
    paradigms = {}
    logging.debug('memorize %s paradigms' % len(paras))
    for para in paras:
        paradigms[para.uuid] = para
    # print('keys', paradigms.keys())
    paradigmdict[lexicon][pos] = (paradigms, numex, lms)


logging.basicConfig(stream=sys.stderr, level='DEBUG')


@app.errorhandler(Exception)
def handle_invalid_usage(error):
    try:
        # print(error)
        # print(dir(error))
        request.get_data()
        logging.debug('Error on url %s' % request.full_path)
        logging.exception(error)

        status = error.status_code
        return "Error!!\n%s" % error.message, status
    except Exception:
        return "Oops, something went wrong\n", 500


def authenticate(lexconf={}, action='read'):
    if action == 'checkopen':
        auth = None
    else:
        auth = request.authorization
    postdata = {"include_open_resources": "true"}
    if auth is not None:
        user, pw = auth.username, auth.password
        server = config['AUTH_SERVER']
        mdcode = user + pw + config['SECRET_KEY']
        postdata["checksum"] = md5(mdcode.encode('utf8')).hexdigest()
    else:
        server = config['AUTH_RESOURCES']

    data = json.dumps(postdata).encode('utf8')
    logging.debug('ask %s, data %s' % (server, postdata))
    response = urllib.request.urlopen(server, data).read().decode('utf8')
    auth_response = json.loads(response)
    lexitems = auth_response.get("permitted_resources", {})
    if action == 'checkopen':
        return [lex for lex,per in lexitems.get("lexica", {}).items()
                if per['read']]
    else:
        permissions = lexitems.get("lexica", {}).get(lexconf['wsauth_name'], {})
        logging.debug('permissions %s' % permissions)
        if not permissions.get(action, False):
            raise e.MflException("Action %s not allowed in lexicon %s" %
                                 (action, lexconf['lexiconName']), 401)

# TODO how to set these??
# For saldomp, i have increased pprior a lot, from 1.0 to 5.0
config = {"print_tables": False,
          "kbest": 10,
          "debug": False,
          "choose": False,
          "AUTH_RESOURCES": "http://localhost:8082/app/resources",
          "AUTH_SERVER": "http://localhost:8082/app/authenticate",
          "SECRET_KEY": "secret"
          }


if __name__ == '__main__':
    import json
    paradigmdict = {}
    snabb = sys.argv[-1] == '--snabb'
    for lex in json.load(open('config/lexicons.json')):
        lexconf = helpers.get_lexiconconf(lex['name'])
        paradigmdict[lex['name']] = {}
        if not snabb:
            for pos in lex['pos']:
                update_model(lex['name'], pos, paradigmdict, lexconf)
    app.run(threaded=True)
