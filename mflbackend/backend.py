import errors as e
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import json
import logging
import sys

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


@app.route('/wordinfo')
@app.route('/wordinfo/<word>')
def wordinfo(word=''):
    " Show information for the word infobox "
    lexicon = request.args.get('lexicon', 'saldomp')
    identifier = word or request.args.get('identifier')
    lexconf = helpers.get_lexiconconf(lexicon)
    obj = helpers.give_info(lexicon, identifier, lexconf['identifier'],
              lexconf['lexiconMode'], lexconf["lexiconName"])
    return jsonify(helpers.format_entry(lexconf, obj))


@app.route('/paradigminfo')
@app.route('/paradigminfo/<paradigm>')
def paradigminfo(paradigm=''):
    " Show information for the paradigm infobox "
    lexicon = request.args.get('lexicon', 'saldomp')
    paradigm = request.args.get('paradigm', paradigm)
    short = request.args.get('short', '')
    short = short in [True, 'true', 'True']
    lexconf = helpers.get_lexiconconf(lexicon)
    # TODO lexconf for extractParadigm should not be needed, same for all
    obj = helpers.give_info(lexicon, paradigm, lexconf['extractparadigm'],
                    lexconf['paradigmMode'], lexconf["paradigmlexiconName"])
    if short:
        short_obj = {}
        short_obj['MorphologicalPatternID'] = obj['MorphologicalPatternID']
        short_obj['partOfSpeech'] = obj['_partOfSpeech']
        short_obj['entries'] = obj['_entries']
        short_obj['TransformCategory'] = obj.get('TransformCategory', {})
        obj = short_obj
    return jsonify(obj)


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
    if not wfs:
        wfs.append({'writtenForm': '', 'msd': ''})

    ans = {'WordForms': wfs, 'partOfSpeech': pos}
    return jsonify(ans)


# Inflections
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
    lemgram = helpers.make_identifier(lexconf, word, pos)
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
            raise e.MflException("Cannot find paradigm %s" % classval, code="unknown_paradigm")
        var_inst.sort()
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
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = helpers.read_one_pos(lexconf)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    firstform = helpers.firstform(table)
    lemgram = helpers.make_identifier(lexconf, firstform, pos)
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    print('got %s paradigms for %s %s' % (len(paras), lexicon, pos))
    ans = handle.inflect_table(table,
                               [paras, numex, lms, config["print_tables"],
                                config["debug"], ppriorv],
                               lexconf, pos=pos, lemgram=lemgram)
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
    ans = {"Results": result}
    return jsonify(ans)


@app.route('/inflectcandidate')
def inflectcandidate():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    identifier = request.args.get('identifier', '')
    q = 'extended||and|%s.search|equals|%s' % ('identifier', identifier)
    res = helpers.karp_query('query', query={'q': q},
                             mode=lexconf['candidateMode'],
                             resource=lexconf['candidatelexiconName'])
    if res['hits']['total'] < 1:
        raise e.MflException("Could not find candidate %s" % identifier,
                             code="unknown_candidate")
    candidate = res['hits']['hits'][0]['_source']
    pos = candidate['partOfSpeech']
    lemgram = helpers.make_identifier(lexconf, candidate['baseform'], pos)
    ans = []
    for inflect in candidate['CandidateParadigms']:
        var_inst = inflect['VariableInstances'].values()
        paras, n, l = helpers.relevant_paradigms(paradigmdict, lexicon,
                                                 pos, possible_p=[inflect['uuid']])
        ans.append(helpers.make_table(lexconf, paras[0], var_inst, 0, pos, lemgram=lemgram))
    return jsonify({"Results": ans})


@app.route('/list')
def listing():
    q = request.args.get('q', '')  # querystring
    s = request.args.get('c', '*')  # searchfield
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
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

        count = helpers.karp_query('statistics',
                                 {'q': query,
                                  'buckets': '%s.bucket' % classname,
                                  'cardinality': True,
                                  'size': 1},
                                 resource=lexconf['lexiconName'],
                                 mode=lexconf['lexiconMode'])
        res = helpers.karp_query('statistics',
                                 {'q': query,
                                  'size': size,
                                  'buckets': ','.join(['%s.bucket' % b for b in buckets])},
                                 resource=lexconf['lexiconName'],
                                 mode=lexconf['lexiconMode'])
        ans = []
        # TODO give a total count
        for pbucket in helpers.get_classbucket(classname, res, lexconf):
            if extra:
                pcount = len(pbucket[lexconf['extractparadigmpath']]['buckets'])
                ans.append([pbucket["key"], pcount, pbucket["doc_count"]])
            else:
                ans.append([pbucket["key"]])

        logging.debug('extra? %s' % extra)
        return jsonify({"compiled_on": classname, "stats": ans,
                        "fields": ["paradigm", "entries"],
                        "count": helpers.get_classcount(classname, count, lexconf)})

    elif compile_f == "wf":
        mode = lexconf['lexiconMode']
        #if querystr:
        s_field = search_f or lexconf["baseform"]
        #else:
        #    s_field = search_f
        ans = helpers.compile_list(query, s_field, querystr, lexicon,
                                   lexconf["show"], size, start, mode)
        out, fields = [], []
        def default(obj):
            return [obj['baseform']], ['baseform']
        func = helpers.extra_src(lexconf, 'make_overview', default)
        for obj in ans["ans"]:
            row, fields = func(obj)
            out.append(row)

        return jsonify({"compiled_on": "wordforms", "stats": out,
                        "fields": fields, "total": ans["total"]})

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
        for hit in ans["ans"]:
            iclasses = []  # only need one instance
            stats = [hit['MorphologicalPatternID']]
            for iclass in lexconf['inflectionalclass'].keys():
                stats.append(len(hit['TransformCategory'].get(iclass, [])))
                iclasses.append(iclass)
            stats.append(hit['_entries'])
            res.append(stats)
        return jsonify({"compiled_on": "paradigm", "stats": res,
                        "fields": iclasses+['entries'] ,"total": ans["total"]})

    else:
        raise e.MflException("Don't know what to do", code="unknown_action")


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
    table = request.args.get('table', '')
    pos = helpers.read_one_pos(lexconf)
    paradigm = request.args.get('paradigm', '')
    # check that the table's identier is unique
    identifier = request.args.get('identifier', '')
    helpers.check_identifier(identifier, lexconf['identifier'],
                             lexconf['lexiconName'], lexconf['lexiconMode'])
    for name, field in [('identifier', identifier), ('paradigm', paradigm), ('partOfSpeech', pos)]:
        if not field:
            raise e.MflException("Both identifier, partOfSpeech and paradigm must be given!",
                                 code="unknown_%s" % name)
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
        raise e.MflException("Could not parse classes. Format should be 'classname:apa,classname2:bepa'" % (classes),
                             code="unparsable_class")
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    if is_new and paradigm in [p.name for p in paras]:
        raise e.MflException("Paradigm name %s is already used" % (paradigm),
                             code="unique_paradigm")

    pex_table = helpers.tableize(table, add_tags=False)
    wf_table = helpers.lmf_wftableize(lexconf, paradigm, table, classes,
                                      baseform='', identifier=identifier,
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

    logging.debug('fitting', fittingparadigms)
    ans = mp.test_paradigms(pex_table, fittingparadigms, numex, lms,
                            config["print_tables"], config["debug"],
                            lexconf["pprior"], returnempty=False,
                            match_all=True)
    if not is_new and len(ans) < 1:
        # print('ans', ans)
        logging.warning("Could not inflect %s as %s" % (table, paradigm))
        raise e.MflException("Table can not belong to paradigm %s" % (paradigm),
                             code="inflect_problem")

    if not ans:
        # print(ans)
        para = pex.learnparadigms([pex_table])[0]
        # print('para is', para)
        v = para.var_insts
        handle.add_paradigm(lexconf['paradigmlexiconName'],
                            lexconf['lexiconName'], paradigm, para, paras,
                            identifier, pos, classes, wf_table)
    else:
        # TODO used to be ans[0][0], see slack 13:26 12/4
        score, para, v = ans[0]
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
        lemgram = helpers.make_identifier(lexconf, baseform, pos, default=True)
        paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
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
    if not _id:
        try:
            identifier = request.args.get('identifier', '')
            q = 'extended||and|%s.search|equals|%s' % ('identifier', identifier)
            res = helpers.karp_query('query', query={'q': q},
                                     mode=lexconf['candidateMode'],
                                     resource=lexconf['candidatelexiconName'])
            _id = res['hits']['hits'][0]['_id']
        except Exception as e1:
            logging.error(e1)
            raise e.MflException("Could not find candidate %s" % identifier,
                                 code="unknown_candidate")
    return jsonify({"deleted": helpers.karp_delete(_id, lexconf['candidatelexiconName'])})


@app.route('/recomputecandidates')
# ￼`'/recomputecandidates?pos=nn&lexicon=saldomp'`
def recomputecandiadtes():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    postags = helpers.read_pos(lexconf)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    print('postags', postags)
    counter = 0
    for pos in postags:
        print('pos', pos)
        q = 'extended||and|%s.search|equals|%s' % (lexconf['pos'], pos)
        res = helpers.karp_query('query', query={'q': q},
                                 mode=lexconf['candidateMode'],
                                 resource=lexconf['candidatelexiconName'])
        paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
        for hit in res['hits']['hits']:
            _id = hit['_id']
            table = hit['_source']
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
                                    config["print_tables"], config["debug"],
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
    res = helpers.karp_query('query', query, mode=mode, resource=lexicon)
    return [hit['_source'] for hit in res['hits']['hits']]


def update_model(lexicon, pos, paradigmdict, lexconf):
    paras = read_paradigms(lexconf['paradigmlexiconName'], pos,
                           lexconf['paradigmMode'])
    logging.debug('memorize %s paradigms??' % len(paras))
    paras, numex, lms = mp.build(paras, lexconf["ngramorder"],
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
        if 'status_code' in dir(error):
            status = error.status_code
            content = json.dumps({
                        "message": "Error!!\n%s" % error.message,
                       "code": error.code
                      })
        else:
            status = 404
            content = json.dumps({
                        "message": "Error!!\n%s" % error,
                      })
        return content, status
    except Exception:
        return {"message": "Oops, something went wrong\n",
                "code": "unexpected error"}, 500


# TODO how to set these??
# For saldomp, i have increased pprior a lot, from 1.0 to 5.0
config = {"print_tables": False,
          "kbest": 10,
          "debug": False,
          "choose": False,
          }


if __name__ == '__main__':
    paradigmdict = {}
    snabb = sys.argv[-1] == '--snabb'
    for lex in json.load(open('config/lexicons.json')):
        lexconf = helpers.get_lexiconconf(lex['name'])
        paradigmdict[lex['name']] = {}
        if not snabb:
            for pos in lex['pos']:
                update_model(lex['name'], pos, paradigmdict, lexconf)
    app.run(threaded=True)
