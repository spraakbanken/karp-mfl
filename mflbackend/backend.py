import errors as e
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import json
import logging
import sys
import configmanager as C
sys.path.append(C.config['paradigmextract'])
import morphparser as mp
import pextract as pex
# Must be imported after pextract is found
import handleparadigms as handle
import helpers
import parsecandidates as pc
import parseparadigms as pp

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
    if not lex:
        res = []
        for l in C.config['all_lexicons']:
            lex = {'name': l['name'], 'open': l.get('open', False)}
            res.append(lex)
        return jsonify({"lexicons": res})
    else:
        lexconf = helpers.get_lexiconconf(lex)
        return jsonify(lexconf)


@app.route('/wordinfo')
@app.route('/wordinfo/<word>')
def wordinfo(word=''):
    " Show information for the word infobox "
    lexicon = request.args.get('lexicon', C.config['default'])
    identifier = word or request.args.get('identifier')
    lexconf = helpers.get_lexiconconf(lexicon)
    obj = helpers.give_info(lexicon, identifier, lexconf['identifier'],
                            lexconf['lexiconMode'], lexconf["lexiconName"])
    lexobj = helpers.format_entry(lexconf, obj)
    # Add info about paradigm_entries and variable instances
    paraobj = helpers.give_info(lexicon, lexobj['paradigm'], pp.id_field,
                                lexconf['paradigmMode'],
                                lexconf["paradigmlexiconName"])
    pp.word_add_parainfo(lexobj, paraobj)
    return jsonify(lexobj)


@app.route('/paradigminfo')
@app.route('/paradigminfo/<paradigm>')
def paradigminfo(paradigm=''):
    " Show information for the paradigm infobox "
    lexicon = request.args.get('lexicon', C.config['default'])
    paradigm = request.args.get('paradigm', paradigm)
    short = request.args.get('short', '')
    short = short in [True, 'true', 'True']
    lexconf = helpers.get_lexiconconf(lexicon)
    # print('lexconf', lexconf)
    show = pp.show_short() if short else []
    obj = helpers.give_info(lexicon, paradigm, pp.id_field,
                            lexconf['paradigmMode'],
                            lexconf["paradigmlexiconName"],
                            show=show)
    return jsonify(obj)


@app.route('/partofspeech')
def all_pos():
    " Show all part of speech tags that the lexicon use "
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    helpers.authenticate(lexconf, 'read')
    # TODO also check in lexicon and give combined info about
    # which exist and which that have paradigms?
    logging.debug(dir(paradigmdict[lexicon]))
    logging.debug('ok %s' % list(paradigmdict[lexicon].keys()))
    return jsonify({"partOfSpeech": list(paradigmdict[lexicon].keys())})


@app.route('/defaulttable')
def defaulttable():
    " Show an empty table suiting the lexicon and part of speech "
    ans = helpers.get_defaulttable()
    return jsonify(ans)


# Inflections
@app.route('/inflectclass')
def inflectclass():
    " Inflect a word according to a user defined category "
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    word = request.args.get('wordform', '')
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    classname = request.args.get('classname', '')
    classval = request.args.get('classval', '')
    pos = helpers.read_one_pos(lexconf)
    lemgram = helpers.make_identifier(lexconf, word, pos)
    q = 'extended||and|%s.search|equals|%s||and|%s|equals|%s'\
        % (classname, classval, lexconf['pos'], pos)
    res = helpers.karp_query('statlist',
                             {'q': q,
                              'buckets': '_id',
                              'mode': lexconf['paradigmMode'],
                              'resource': lexconf['paradigmlexiconName']
                              }
                             )
    possible_p = [line[0] for line in res['stat_table']]
    logging.debug('possible_p %s' % possible_p)
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon,
                                                   pos, possible_p)
    # TODO what if there are no variables?
    var_inst = sorted([(int(key), val) for key, val in request.args.items()
                       if key.isdigit()])
    if classname == "paradigm" and var_inst:
        # Special case: '?classname=paradigm&classval=p14_oxe..nn.1?1=katt&2=a'
        # TODO rename to extractparadigm?
        if len(paras) < 1 or len(possible_p) < 1:
            raise e.MflException("Cannot find paradigm %s" % classval,
                                 code="unknown_paradigm")
        var_inst = [val for key, val in var_inst]
        logging.debug('look for %s as %s' % (classval, pos))
        table = helpers.make_table(lexconf, paras[0], var_inst, 0, pos, lemgram)
        ans = {"Results": [table]}

    else:
        restrict_to_baseform = helpers.read_restriction(lexconf)
        res = mp.run_paradigms(paras, [word], kbest=100, pprior=ppriorv,
                               lms=lms, numexamples=numex,
                               baseform=restrict_to_baseform)
        logging.debug('generated %s results' % len(res))
        results = helpers.format_inflection(lexconf, res, pos=pos, lemgram=lemgram)
        ans = {"Results": results}
    # print('asked', q)
    return jsonify(ans)


@app.route('/inflect')
def inflect():
    " Inflect a word or table "
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = helpers.read_one_pos(lexconf)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    # no call to karp, must check auth
    helpers.authenticate(lexconf, 'read')
    firstform = helpers.firstform(table)
    lemgram = helpers.make_identifier(lexconf, firstform, pos)
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    # print('got %s paradigms for %s %s' % (len(paras), lexicon, pos))
    ans = handle.inflect_table(table,
                               [paras, numex, lms, C.config["print_tables"],
                                C.config["debug"], ppriorv],
                               lexconf, pos=pos, lemgram=lemgram)
    # logging.debug('ans')
    return jsonify(ans)


@app.route('/inflectlike')
def inflectlike():
    " Inflect a word similarly to another word "
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    word = request.args.get('wordform', '')
    pos = helpers.read_one_pos(lexconf)
    like = request.args.get('like')
    logging.debug('like %s' % like)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    if not pos:
        pos = helpers.identifier2pos(lexconf, like)
    lemgram = helpers.make_identifier(lexconf, word, pos)
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
        result = helpers.format_inflection(lexconf, res, pos=pos, lemgram=lemgram)
    else:
        result = []
    return jsonify({"Results": result})


@app.route('/inflectcandidate')
def inflectcandidate():
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    identifier = request.args.get('identifier', '')
    q = 'extended||and|%s.search|equals|%s' % ('identifier', identifier)
    res = helpers.karp_query('query', query={'q': q},
                             mode=lexconf['candidateMode'],
                             resource=lexconf['candidatelexiconName'])
    if helpers.es_total(res) < 1:
        raise e.MflException("Could not find candidate %s" % identifier,
                             code="unknown_candidate")
    candidate = helpers.es_first_source(res)
    pos = pc.get_pos(candidate)
    lemgram = helpers.make_identifier(lexconf, pc.get_baseform(candidate), pos)
    ans = []
    for inflect in pc.candidateparadigms(candidate):
        var_inst = []
        for varname, var in pc.inflectionvariables(inflect):
            if varname.isdigit():
                var_inst.append((int(varname), var))
        var_inst = [var for key, var in sorted(var_inst)]
        paras, n, l = helpers.relevant_paradigms(paradigmdict, lexicon,
                                                 pos,
                                                 possible_p=[pc.get_uuid(inflect)])
        # the paradigm might be removed, then skip it
        if paras:
            ans.append(helpers.make_table(lexconf, paras[0], var_inst, 0, pos,
                                          lemgram=lemgram))

    if not pc.candidateparadigms(candidate):
        table = helpers.tableize_obj(candidate, add_tags=True, identifier=lemgram)
        paradigm = pex.learnparadigms([table])[0]
        obj = {'score': 0, 'paradigm': '', 'new': True}
        if paradigm is not None:
            obj['variables'] = [var for ix, var in paradigm.var_insts[0][1:]]
            obj['paradigm'] = paradigm.name
            obj['pattern'] = paradigm.jsonify()
        obj['WordForms'] = pc.get_wordforms(candidate)
        obj['identifier'] = lemgram
        obj['partOfSpeech'] = pos
        obj['count'] = 0
        ans = [helpers.show_inflected(obj)]
    return jsonify({"Results": ans})


@app.route('/list')
def listing():
    q = request.args.get('q', '')  # querystring
    s = request.args.get('c', '*')  # searchfield
    lexicon = request.args.get('lexicon', C.config['default'])
    size = request.args.get('size', '100')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = helpers.read_pos(lexconf)
    query = []
    if pos:
        query.append('and|%s|equals|%s' % (lexconf["pos"], '|'.join(pos)))

    if s == 'class':
        classname = request.args.get('classname', '')
        query = helpers.search_q(query, classname, q, lexicon)
        res = helpers.karp_query('statlist',
                                 {'q': query,
                                  'size': size,
                                  'buckets': classname+'.bucket'},
                                 resource=lexconf['lexiconName'],
                                 mode=lexconf['lexiconMode'])
        return jsonify({"compiled_on": classname,
                        "list": res['stat_table'],
                        "fields": [classname, "entries"]})

    if s in ["wf", "wordform"]:
        # TODO this is probably not correct, due to ES approx
        query = helpers.search_q(query, lexconf["baseform"], q, lexicon)
        res = helpers.karp_query('statlist',
                                 {'q': query,
                                  'size': size,
                                  'buckets': lexconf["baseform"]+'.bucket'},
                                 resource=lexconf['lexiconName'],
                                 mode=lexconf['lexiconMode'])
        return jsonify({"compiled_on": "wordform",
                        "list": res['stat_table'],
                        "fields": ["baseform", "entries"]})

    elif s == "paradigm":
        query = helpers.search_q(query, lexconf["extractparadigm"], q, lexicon)
        res = helpers.karp_query('statlist',
                                 {'q': query,
                                  'size': size,
                                  'buckets': lexconf["extractparadigm"]+'.bucket'},
                                 resource=lexconf['lexiconName'],
                                 mode=lexconf['lexiconMode'])
        return jsonify({"compiled_on": "paradigm",
                        "list": res['stat_table'],
                        "fields": ["paradigm", "entries"]})
    else:
        return "Don't know what to do"


@app.route('/compile')
def compile():
    querystr = request.args.get('q', '')  # querystring
    search_f = request.args.get('s', '')  # searchfield
    compile_f = request.args.get('c', '')  # searchfield
    isfilter = request.args.get('filter', '')  # filter the hits?
    isfilter = isfilter in ['true', 'True', True]
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
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

    search_f = lexconf.get(search_f, search_f)
    if pos:
        query.append('and|%s|equals|%s' % (lexconf["pos"], '|'.join(pos)))

    if compile_f == 'class':
        classname = request.args.get('classname', '')
        if querystr:
            s_field = search_f or classname
            operator = 'equals' if not isfilter else 'regexp'
            if isfilter:
                querystr = '.*'+querystr+'.*'
            query.append('and|%s|%s|%s' % (s_field, operator, querystr))
        if query:
            query = 'extended||' + '||'.join(query)
        else:
            query = 'extended||and|lexiconName|equals|%s' %\
                    lexconf['lexiconName']

        if extra:
            buckets = [classname, lexconf['extractparadigm']]
        else:
            buckets = [classname]

        count = helpers.karp_query('statistics',
                                   {'q': query,
                                    'buckets': '%s.bucket' % classname,
                                    'cardinality': True,
                                    'size': 1},
                                   resource=lexconf['lexiconName'],
                                   mode=lexconf['lexiconMode'])
        res = helpers.karp_query('statistics',
                                 {'q': query,
                                  'size': start+size,
                                  'buckets': ','.join(['%s.bucket' % b for b in buckets])},
                                 resource=lexconf['lexiconName'],
                                 mode=lexconf['lexiconMode'])
        ans = []
        for pbucket in helpers.get_classbucket(classname, res, lexconf)[int(start):]:
            if extra:
                pcount = len(pbucket[lexconf['extractparadigmpath']]['buckets'])
                ans.append([pbucket["key"], pcount, pbucket["doc_count"]])
            else:
                ans.append([pbucket["key"]])

        logging.debug('extra? %s' % extra)
        return jsonify({"compiled_on": classname, "stats": ans,
                        "fields": [classname, "paradigm", "entries"],
                        "total": helpers.get_classcount(classname, count, lexconf)})

    elif compile_f in ["wf", "wordform"]:
        mode = lexconf['lexiconMode']
        s_field = search_f or lexconf["baseform"]
        ans = helpers.compile_list(query, s_field, querystr, lexicon,
                                   lexconf["show"], size, start, mode,
                                   isfilter)
        out, fields = [], []

        def default(obj):
            return [obj['baseform']], ['baseform']

        func = helpers.extra_src(lexconf, 'make_overview', default)
        for obj in ans["ans"]:
            row, fields = func(obj)
            out.append(row)

        return jsonify({"compiled_on": "wordform", "stats": out,
                        "fields": fields, "total": ans["total"]})

    elif compile_f == "paradigm":
        # TODO no need to look in config for this, it should always be the same
        # if querystr:
        s_field = search_f or pp.id_field
        # else:
        #     s_field = search_f
        show = ','.join([pp.id_field,
                         pp.transform_field,
                         pp.entries])
        lexicon = lexconf['paradigmlexiconName']
        mode = lexconf['paradigmMode']
        ans = helpers.compile_list(query, s_field, querystr, lexicon, show,
                                   size, start, mode, isfilter)
        res = []
        iclasses = []
        for hit in ans["ans"]:
            iclasses = []  # only need one instance
            stats = [hit[pp.id_field]]
            for iclass in lexconf['inflectionalclass'].keys():
                stats.append(len(pp.get_transformcat(hit, iclass)))
                iclasses.append(iclass)
            stats.append(pp.get_entries(hit))
            res.append(stats)
        return jsonify({"compiled_on": "paradigm", "stats": res,
                        "fields": ['paradigm']+iclasses+['entries'], "total": ans["total"]})

    else:
        raise e.MflException("Don't know what to do", code="unknown_action")


# Update
@app.route('/renameparadigm')
def renameparadigm():
    # TODO!
    return "Not implemented"


@app.route('/updatetable')
def update_table():
    identifier = request.args.get('identifier', '')
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = helpers.read_one_pos(lexconf)
    old_para = helpers.get_current_paradigm(identifier, pos, lexconf, paradigmdict)

    wf_table, para, v, classes = handle.make_new_table(paradigmdict)
    handle.remove_word_from_paradigm(identifier, pos, old_para, lexconf, paradigmdict)

    karp_id = helpers.get_es_identifier(identifier,
                                        lexconf['identifier'],
                                        lexconf['lexiconName'],
                                        lexconf['lexiconMode'])
    helpers.karp_update(karp_id, wf_table, resource=lexconf['lexiconName'])
    return jsonify({'paradigm': para.name, 'identifier': identifier,
                    'var_inst': dict(enumerate(v, 1)), 'classes': classes,
                    'pattern': para.jsonify(), 'partOfSpeech': pos,
                    'members': para.count})


@app.route('/addtable')
def add_table():
    # TODO see config for needed and possible fields
    # or is that not needed?
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    identifier = request.args.get('identifier', '')
    pos = helpers.read_one_pos(lexconf)
    wf_table, para, v, classes = handle.make_new_table(paradigmdict, newword=True)

    helpers.karp_add(wf_table, resource=lexconf['lexiconName'])
    return jsonify({'paradigm': para.name, 'identifier': identifier,
                    'var_inst': dict(enumerate(v, 1)), 'classes': classes,
                    'pattern': para.jsonify(), 'partOfSpeech': pos,
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
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    to_save = []
    for table in tables:
        if not table:
            continue
        logging.debug('table %s' % table)
        # TODO move the parsing somewhere else
        forms, pos = table.strip().split('\t')
        forms = forms.split(',')
        baseform = forms[0]
        if '|' in baseform:
            baseform = baseform.split('|')[0]
            forms = [baseform] + forms
        lemgram = helpers.make_identifier(lexconf, baseform, pos, default=True)
        paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
        pex_table = helpers.tableize(','.join(forms), add_tags=False)
        logging.debug('inflect forms %s msd %s' % pex_table)
        restrict_to_baseform = helpers.read_restriction(lexconf)
        res = mp.test_paradigms(pex_table, paras, numex, lms,
                                C.config["print_tables"], C.config["debug"],
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
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = helpers.read_pos(lexconf)
    q = 'extended||and|%s.search|equals|%s' % (lexconf['pos'], '|'.join(pos))
    res = helpers.karp_query('query', query={'q': q},
                             mode=lexconf['candidateMode'],
                             resource=lexconf['candidatelexiconName'])
    return jsonify({"candidates": helpers.es_all_source(res)})


@app.route('/removecandidate')
def removecandidate(_id=''):
    ''' Either use this with the ES id:
        /removecandidate?es_identifier=ABC83Z
        or with the lexcion's identifiers
        /removecandidate?identifier=katt..nn.1
    '''
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    try:
        identifier = request.args.get('identifier', '')
        q = 'extended||and|%s.search|equals|%s' % ('identifier', identifier)
        res = helpers.karp_query('query', query={'q': q},
                                 mode=lexconf['candidateMode'],
                                 resource=lexconf['candidatelexiconName'])
        _id = helpers.es_first_id(res)
    except Exception as e1:
        logging.error(e1)
        raise e.MflException("Could not find candidate %s" % identifier,
                             code="unknown_candidate")
    return jsonify({"deleted": helpers.karp_delete(_id, lexconf['candidatelexiconName'])})


@app.route('/recomputecandidates')
# ￼`'/recomputecandidates?pos=nn&lexicon=saldomp'`
def recomputecandiadtes():
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = helpers.get_lexiconconf(lexicon)
    postags = helpers.read_pos(lexconf)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    # print('postags', postags)
    counter = 0
    for pos in postags:
        # print('pos', pos)
        q = 'extended||and|%s.search|equals|%s' % (lexconf['pos'], pos)
        res = helpers.karp_query('query', query={'q': q},
                                 mode=lexconf['candidateMode'],
                                 resource=lexconf['candidatelexiconName'])
        paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
        for hit in helpers.es_get_hits(res):
            _id = helpers.es_get_id(hit)
            table = helpers.es_get_source(hit)
            logging.debug('table %s' % table)
            forms = [table['baseform']]
            for wf in table.get('WordForms', []):
                form = wf['writtenForm']
                msd = wf.get('msd', '')
                if msd:
                    forms.append(form+'|'+msd)
                else:
                    forms.append(form)
            pex_table = helpers.tableize(','.join(forms), add_tags=False)
            logging.debug('inflect forms %s msd %s' % pex_table)
            restrict_to_baseform = helpers.read_restriction(lexconf)
            res = mp.test_paradigms(pex_table, paras, numex, lms,
                                    C.config["print_tables"], C.config["debug"],
                                    ppriorv, returnempty=False,
                                    baseform=restrict_to_baseform)
            to_save = helpers.make_candidate(lexconf['candidatelexiconName'],
                                             table['identifier'], forms, res,
                                             table['partOfSpeech'])
            counter += 1
        logging.debug('will save %s' % to_save)
        helpers.karp_update(_id, to_save, resource=lexconf['candidatelexiconName'])
    return jsonify({"updated": counter})


def read_paradigms(lexicon, pos, mode):
    # get all paradigms from ES
    query = {'size': 10000, 'q': 'extended||and|pos|equals|%s' % pos}
    user = C.config.get('DBPASS', '')
    res = helpers.karp_query('query', query, mode=mode, resource=lexicon, user=user)
    return helpers.es_all_source(res)


def update_model(lexicon, pos, paradigmdict, lexconf):
    paras = read_paradigms(lexconf['paradigmlexiconName'], pos,
                           lexconf['paradigmMode'])
    logging.debug('memorize %s paradigms??' % len(paras))
    paras, numex, lms, alphabet = mp.build(paras, lexconf["ngramorder"],
                                           lexconf["ngramprior"],
                                           lexicon=lexconf['paradigmlexiconName'],
                                           inpformat='json',
                                           pos=pos,
                                           small=False)
    logging.debug('memorize %s paradigms' % len(paras))
    paradigms = {}
    for para in paras:
        paradigms[para.uuid] = para
    # print('keys', paradigms.keys())
    paradigmdict[lexicon][pos] = (paradigms, numex, lms, alphabet)


logging.basicConfig(stream=sys.stderr, level='DEBUG')


@app.errorhandler(Exception)
def handle_invalid_usage(error):
    try:
        # print(error)
        # print(dir(error))
        request.get_data()
        logging.debug('Error on url %s' % request.full_path)
        logging.exception(error)
        if 'status_code' in dir(error):
            status = error.status_code
            content = json.dumps({"message": "Error!!\n%s" % error.message,
                                  "code": error.code
                                  })
        else:
            status = 404
            content = json.dumps({"message": "Error!!\n%s" % error,
                                  "code": "unknown_error"})
        return content, status
    except Exception:
        return {"message": "Oops, something went wrong\n",
                "code": "unexpected error"}, 500


# For saldomp, i have increased pprior a lot, from 1.0 to 5.0


def start():
    for lex in C.config['all_lexicons']:
        lexconf = helpers.get_lexiconconf(lex['name'])
        paradigmdict[lex['name']] = {}
        for pos in lex['pos']:
            update_model(lex['name'], pos, paradigmdict, lexconf)

paradigmdict = {}

if __name__ == '__main__':
    paradigmdict = {}
    snabb = sys.argv[-1] == '--snabb'
    for lex in C.config['all_lexicons']:
        lexconf = helpers.get_lexiconconf(lex['name'])
        paradigmdict[lex['name']] = {}
        if not snabb:
            for pos in lex['pos']:
                update_model(lex['name'], pos, paradigmdict, lexconf)
    app.run(threaded=True)
