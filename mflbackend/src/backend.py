import configmanager as C
import errors as e
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import json
import lexconfig
import logging
import sys
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
    if lex:
        lexconf = lexconfig.get_lexiconconf(lex)
        return jsonify(lexconf)
    else:
        res = []
        for lexdict in C.config['all_lexicons']:
            lexconf = {'name': lexdict['name'], 'open': lexdict.get('open', False)}
            res.append(lexconf)
        return jsonify({"lexicons": res})


@app.route('/wordinfo')
@app.route('/wordinfo/<word>')
def wordinfo(word=''):
    " Show information for the word infobox "
    lexicon = request.args.get('lexicon', C.config['default'])
    identifier = word or request.args.get('identifier')
    lexconf = lexconfig.get_lexiconconf(lexicon)
    obj = helpers.give_info(identifier, lexconf['identifier'],
                            lexconf['lexiconMode'], lexconf["lexiconName"])
    lexobj = helpers.format_entry(lexicon, obj)
    # Get info about paradigm_entries and variable instances
    paraobj = helpers.give_info(lexobj['paradigm'], pp.id_field,
                                lexconf['paradigmMode'],
                                lexconf["paradigmlexiconName"])
    # Merge the paradigmentry and the wordentry
    pp.word_add_parainfo(lexobj, paraobj)
    return jsonify(lexobj)


@app.route('/paradigminfo')
@app.route('/paradigminfo/<paradigm>')
def paradigminfo(paradigm=''):
    " Show information for the paradigm infobox "
    lexicon = request.args.get('lexicon', C.config['default'])
    paradigm = request.args.get('paradigm', paradigm)
    lexconf = lexconfig.get_lexiconconf(lexicon)
    # short: only show top 5 variable instances
    short = request.args.get('short', '')
    short = short in [True, 'true', 'True']
    show = pp.show_short() if short else []
    obj = helpers.give_info(paradigm, pp.id_field,
                            lexconf['paradigmMode'],
                            lexconf["paradigmlexiconName"],
                            show=show)
    return jsonify(obj)


@app.route('/partofspeech')
def all_pos():
    " Show all part of speech tags that the lexicon use "
    lexicon = request.args.get('lexicon', C.config['default'])
    # authentication is only needed when karp is not involved
    helpers.authenticate(lexicon, 'read')
    # TODO also give combined info about tags in (the karp) lexicon
    # that are not shown in mfl?
    logging.debug('ok %s', list(paradigmdict[lexicon].keys()))
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
    lexconf = lexconfig.get_lexiconconf(lexicon)
    word = request.args.get('wordform', '')
    # ppriorv: setting for pextract
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    classname = request.args.get('classname', '')
    classval = request.args.get('classval', '')
    pos = helpers.read_one_pos(lexconf)
    lemgram = helpers.make_identifier(lexicon, word, pos)
    # ask karp to filter out matching paradigm's IDs
    q = 'extended||and|%s.search|equals|%s||and|%s|equals|%s'\
        % (classname, classval, lexconf['pos'], pos)
    res = helpers.karp_query('statlist',
                             {'q': q,
                              'buckets': '_id',
                              'mode': lexconf['paradigmMode'],
                              'resource': lexconf['paradigmlexiconName']
                             }
                            )
    # get the internal objects for these paradigms
    possible_p = [line[0] for line in res['stat_table']]
    logging.debug('possible_p %s', possible_p)
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon,
                                                   pos, possible_p)
    # get the provided variable instances, if any
    var_inst = sorted([(int(key), val) for key, val in request.args.items()
                       if key.isdigit()])
    if classname == "paradigm" and var_inst:
        # Special case: '?classname=paradigm&classval=p14_oxe..nn.1&1=katt&2=a'
        # Will result in only one possible table
        # TODO rename to extractparadigm?
        if len(paras) < 1 or len(possible_p) < 1:
            raise e.MflException("Cannot find paradigm %s" % classval,
                                 code="unknown_paradigm")
        var_inst = [val for key, val in var_inst]
        logging.debug('look for %s as %s', classval, pos)
        table = helpers.make_table(lexicon, paras[0], var_inst, 0, pos, lemgram)
        ans = {"Results": [table]}

    else:
        # The user has provided a paradigm or inflection class:
        # '?classname=paradigm&classval=p14_oxe..nn.1&wordform=bolle'
        # Find the possible tables (zero or more).
        # is the given form necessarily the baseform?
        restrict_to_baseform = helpers.read_restriction(lexconf)
        res = mp.run_paradigms(paras, [word], kbest=100, pprior=ppriorv,
                               lms=lms, numexamples=numex,
                               baseform=restrict_to_baseform)
        logging.debug('generated %s results', len(res))
        results = helpers.format_kbest(lexicon, res, pos=pos, lemgram=lemgram)
        ans = {"Results": results}
    return jsonify(ans)


@app.route('/inflect')
def inflect():
    " Inflect a word or table "
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = helpers.read_one_pos(lexconf)
    # strict: the resulting table may not contain more forms than the input
    strict = request.args.get('strict', '')
    strict = strict in [True, 'true', 'True']
    # ppriorv: setting for pextract
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    # authentication is only needed when karp is not involved
    helpers.authenticate(lexicon, 'read')
    firstform = helpers.firstform(table)
    lemgram = helpers.make_identifier(lexicon, firstform, pos)
    ans = handle.inflect_table(lexicon, table, paradigmdict, lemgram, pos, ppriorv,
                               match_all=strict)

    return jsonify(ans)


@app.route('/inflectlike')
def inflectlike():
    " Inflect a word similarly to another word "
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    # the word to inflect
    word = request.args.get('wordform', '')
    pos = helpers.read_one_pos(lexconf)
    # the word (or word form) with known inflection
    like = request.args.get('like')
    logging.debug('like %s', like)
    # ppriorv: setting for pextract
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    if not pos:
        pos = helpers.identifier2pos(lexicon, like)
    lemgram = helpers.make_identifier(lexicon, word, pos)
    # ask karp to filter out the paradigm's ID
    q = 'extended||and|%s.search|equals|%s' % ('first-attest', like)
    res = helpers.karp_query('statlist',
                             {'q': q,
                              'mode': lexconf['paradigmMode'],
                              'resource': lexconf['paradigmlexiconName'],
                              'buckets': '_id'
                             }
                            )
    # get the internal objects for these paradigms
    possible_p = [line[0] for line in res['stat_table']]
    if possible_p:
        paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon,
                                                       pos,
                                                       possible_p=possible_p)

        logging.debug('test %s paradigms', len(paras))
        # is the given form necessarily the baseform?
        restrict_to_baseform = helpers.read_restriction(lexconf)
        res = mp.run_paradigms(paras, [word], kbest=100, pprior=ppriorv,
                               lms=lms, numexamples=numex, vbest=20,
                               baseform=restrict_to_baseform)
        result = helpers.format_kbest(lexicon, res, pos=pos, lemgram=lemgram)
    else:
        # the wordform could not be inflected like the given word
        result = []
    return jsonify({"Results": result})


@app.route('/inflectcandidate')
def inflectcandidate():
    " Inflect a known candidate according to it's assigned paradigms "
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    identifier = request.args.get('identifier', '')
    # ask karp for the saved candidates and its assigned paradigms
    q = 'extended||and|%s.search|equals|%s' % ('identifier', identifier)
    res = helpers.karp_query('query', query={'q': q},
                             mode=lexconf['candidateMode'],
                             resource=lexconf['candidatelexiconName'])
    if helpers.es_total(res) < 1:
        raise e.MflException("Could not find candidate %s" % identifier,
                             code="unknown_candidate")
    candidate = helpers.es_first_source(res)
    pos = pc.get_pos(candidate)
    lemgram = helpers.make_identifier(lexicon, pc.get_baseform(candidate), pos)
    ans = []
    # go through each possible paradigm
    for inflection in pc.candidateparadigms(candidate):
        var_inst = []
        # get the variable instansiation
        for varname, var in pc.inflectionvariables(inflection):
            if varname.isdigit():
                var_inst.append((int(varname), var))
        var_inst = [var for key, var in sorted(var_inst)]
        # get the paradigm with the given ID
        paras, n, l = helpers.relevant_paradigms(paradigmdict, lexicon,
                                                 pos,
                                                 possible_p=[pc.get_uuid(inflection)])
        # the paradigm might be removed, then skip it
        # if not, save the table
        if paras:
            ans.append(helpers.make_table(lexicon, paras[0], var_inst, 0, pos,
                                          lemgram=lemgram))

    if not pc.candidateparadigms(candidate):
        # if the candidate don't have assigned paradigms, make a table with all
        # known forms
        table = helpers.tableize_obj(candidate, add_tags=True, identifier=lemgram)
        # get the paradigm representation from pextract
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
        ans = [helpers.show_inflected(lexicon, obj)]
    return jsonify({"Results": ans})


@app.route('/list')
def listing():
    """
    Make a short listing of possible values. Used for population dropdowns
    Possible values to list: class, wf/wordform, paradigm
    """
    q = request.args.get('q', '')  # querystring
    s = request.args.get('c', '*')  # compilation field
    lexicon = request.args.get('lexicon', C.config['default'])
    size = request.args.get('size', '100')
    lexconf = lexconfig.get_lexiconconf(lexicon)
    pos = helpers.read_pos(lexconf)
    query = []  # will contain all parts of the karp query
    # if pos tag(s) is given, filter out this/these
    if pos:
        query.append('and|%s|equals|%s' % (lexconf["pos"], '|'.join(pos)))

    if s == 'class':
        # list all inflectional classes
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
        # list all words
        # TODO this is probably not correct, due to ES approx
        # TODO fix bug for es6 in karp
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
        # list all (extract)paradigms
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
        raise e.MflException("Don't know what to do", code="unknown_action")


@app.route('/compile')
def compile():
    """
    Make a compilation, possible filtered. Contains more information than /list
    Possible values to compile: class, wf/wordform, paradigm
    """
    querystr = request.args.get('q', '')  # querystring
    search_f = request.args.get('s', '')  # search field
    compile_f = request.args.get('c', '')  # compilation field
    # if isfilter is true, the given query string will searched for as a
    # substring: ".*apa.*", instead of "apa"
    isfilter = request.args.get('filter', '')
    isfilter = isfilter in ['true', 'True', True]
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    pos = helpers.read_pos(lexconf)
    size = request.args.get('size', '100')
    start = request.args.get('start', '0')
    query = []  # will contain all parts of the karp query
    if ',' in search_f:
        # Search many fields: 'q=katt,p100_rallarros..nn.1&s=wordform,paradigm'
        # Process and add to the karp query
        helpers.multi_query(lexicon, query, search_f.split(','),
                            querystr.split(','), isfilter)
        # Empty fields so that they are not added to the karp query again
        search_f = ''
        querystr = ''

    # Look up the correct search field name
    search_f = lexconf.get(search_f, search_f)
    if pos:
        query.append('and|%s|equals|%s' % (lexconf["pos"], '|'.join(pos)))

    if compile_f == 'class':
        # Compile on inflectional class: 'class=bklass&classname=2'
        classname = request.args.get('classname', '')
        if querystr:
            # if no search field is given, search the class to compile on
            s_field = search_f or classname
            operator = 'equals' if not isfilter else 'regexp'
            if isfilter:
                querystr = '.*'+querystr+'.*'
            query.append('and|%s|%s|%s' % (s_field, operator, querystr))
        if query:
            query = 'extended||' + '||'.join(query)
        else:
            # if no query is given, list all entries in the lexicon
            query = 'extended||and|lexiconName|equals|%s' %\
                    lexconf['lexiconName']

        buckets = [classname, lexconf['extractparadigm']]

        # ask karp how many classes that are matching the criteria
        count = helpers.karp_query('statistics',
                                   {'q': query,
                                    'buckets': '%s.bucket' % classname,
                                    'cardinality': True,
                                    'size': 1},
                                   resource=lexconf['lexiconName'],
                                   mode=lexconf['lexiconMode'])
        # ask karp for the combination of classes and paradigms (will result in
        # a nested structure from which the count cannot be easily read).
        res = helpers.karp_query('statistics',
                                 {'q': query,
                                  'size': start+size,
                                  'buckets': ','.join(['%s.bucket' % b for b in buckets])},
                                 resource=lexconf['lexiconName'],
                                 mode=lexconf['lexiconMode'])
        ans = []
        for pbucket in helpers.es_get_classbucket(classname, res, lexconf)[int(start):]:
            pcount = len(pbucket[lexconf['extractparadigmpath']]['buckets'])
            # [class name, number of paradigms, number of words]
            ans.append([pbucket["key"], pcount, pbucket["doc_count"]])

        return jsonify({"compiled_on": classname, "stats": ans,
                        "fields": [classname, "paradigm", "entries"],
                        "total": helpers.es_get_classcount(classname, count, lexconf)})

    elif compile_f in ["wf", "wordform"]:
        # Compile on words
        mode = lexconf['lexiconMode']
        # if no search field is given, search the baseform
        s_field = search_f or lexconf["baseform"]
        ans = helpers.compile_list(query, s_field, querystr, lexicon,
                                   lexconf["show"], size, start, mode,
                                   isfilter)

        # get lexicon specific function for how to present the entries
        def default(obj):
            return [obj['baseform']], ['baseform']
        func = helpers.extra_src(lexicon, 'make_overview', default)
        out, fields = [], []
        for obj in ans["ans"]:
            row, fields = func(obj)
            out.append(row)

        return jsonify({"compiled_on": "wordform", "stats": out,
                        "fields": fields, "total": ans["total"]})

    elif compile_f == "paradigm":
        # Compile on paradigms
        # if no search field is given, search the baseform
        s_field = search_f or pp.id_field
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
            # the inflectional classes that are present.
            # only need one instance, so empty each iteration
            iclasses = []
            stats = [hit[pp.id_field]]
            for iclass in lexconf['inflectionalclass'].keys():
                stats.append(len(pp.get_transformcat(hit, iclass)))
                iclasses.append(iclass)
            stats.append(pp.get_entries(hit))
            res.append(stats)
        return jsonify({"compiled_on": "paradigm", "stats": res,
                        "fields": ['paradigm']+iclasses+['entries'],
                        "total": ans["total"]})

    else:
        raise e.MflException("Don't know what to do", code="unknown_action")


# Update
@app.route('/renameparadigm')
def renameparadigm():
    # TODO!
    return "Not implemented"


@app.route('/updatetable')
def update_table():
    """
    Update the  inflection table of a word.
    Also update/add the corresponding paradigm, and remove the word
    from the old paradigm.
    """
    identifier = request.args.get('identifier', '')
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    pos = helpers.read_one_pos(lexconf)
    old_para = helpers.get_current_paradigm(identifier, pos, lexconf, paradigmdict)
    table = request.args.get('table', '')
    paradigm = request.args.get('paradigm', '')
    baseform = request.args.get('baseform', '')
    classes = request.args.get('class', '') or request.args.get('classes', '')
    is_new = request.args.get('new')
    is_new = is_new in ['True', 'true', True]

    # remove from the old paradigm
    handle.remove_word_from_paradigm(lexicon, old_para, paradigmdict, identifier, pos)

    # make inflection, assign to the new paradigm
    res = handle.make_new_table(lexicon, table, paradigm, paradigmdict,
                                identifier, baseform, pos, classes,
                                newpara=is_new)
    identifier, wf_table, para, v, classes = res

    # ask karp for the word's ID
    karp_id = helpers.get_es_identifier(identifier,
                                        lexconf['identifier'],
                                        lexconf['lexiconName'],
                                        lexconf['lexiconMode'])
    # save the inflection table in karp
    helpers.karp_update(karp_id, wf_table, resource=lexconf['lexiconName'])
    return jsonify({'paradigm': para.name, 'identifier': identifier,
                    'var_inst': dict(enumerate(v, 1)), 'classes': classes,
                    'pattern': para.jsonify(), 'partOfSpeech': pos,
                    'members': para.count})


@app.route('/removetable')
def remove_table():
    """
    Remove the  inflection table of a word (ie the whole entry).
    Also remove the word from its paradigm.
    """
    identifier = request.args.get('identifier', '')
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    pos = helpers.read_one_pos(lexconf)
    para = helpers.get_current_paradigm(identifier, pos, lexconf, paradigmdict)

    # remove from the old paradigm
    handle.remove_word_from_paradigm(lexicon, para, paradigmdict, identifier, pos)

    # ask karp for the word's ID
    karp_id = helpers.get_es_identifier(identifier,
                                        lexconf['identifier'],
                                        lexconf['lexiconName'],
                                        lexconf['lexiconMode'])
    # save the inflection table in karp
    # TODO
    helpers.karp_delete(karp_id, resource=lexconf['lexiconName'])
    return jsonify({'identifier': identifier, 'removed': True})


# Not tested, add url when tested
# @app.route('/removeparadigm')
def remove_paradigm():
    """
    Remove a paradigm.
    """
    identifier = request.args.get('identifier', '')
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    # para = helpers.get_current_paradigm(identifier, pos, lexconf, paradigmdict)


    # see if the paradigm is empty
    # TODO paradigm? look up
    query = helpers.search_q([], lexconf["extractparadigm"], identifier, lexicon)
    res = helpers.karp_query('query',
                             {'q': query, 'size': 0},
                             resource=lexconf['lexiconName'],
                             mode=lexconf['lexiconMode'])

    members = helpers.es_total(res)
    if members == 0:
        pres = helpers.karp_query('query',
                                 {'q': query, 'size': 1},
                                 resource=lexconf['paradigmlexiconName'],
                                 mode=lexconf['paradigmMode'])
        karp_id = helpers.es_first_id(pres)
        # remove the paradigm
        helpers.karp_delete(karp_id, resource=lexconf['lexiconName'])
    else:
        err = 'Try to remove paradigm with %s members %s'
        logging.error(err, members, identifier)
        raise e.MflException(err % (members, identifier))
    return jsonify({'identifier': identifier, 'removed': True})


@app.route('/addtable')
def add_table():
    """
    Add a word (an inflection table).
    Also update/add the corresponding paradigm.
    """
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    pos = helpers.read_one_pos(lexconf)
    table = request.args.get('table', '')
    paradigm = request.args.get('paradigm', '')
    identifier = request.args.get('identifier', '')
    baseform = request.args.get('baseform', '')
    classes = request.args.get('class', '') or request.args.get('classes', '')
    is_new = request.args.get('new')
    is_new = is_new in ['True', 'true', True]

    # make inflection, assign to the paradigm
    res = handle.make_new_table(lexicon, table, paradigm, paradigmdict,
                                identifier, baseform, pos, classes,
                                newword=True, newpara=is_new)
    identifier, wf_table, para, v, classes = res

    # add the inflection to karp
    helpers.karp_add(wf_table, resource=lexconf['lexiconName'])
    return jsonify({'paradigm': para.name, 'identifier': identifier,
                    'var_inst': dict(enumerate(v, 1)), 'classes': classes,
                    'pattern': para.jsonify(), 'partOfSpeech': pos,
                    'members': para.count})


@app.route('/addcandidates', methods=['POST'])
def addcandidates():
    '''
    Add a list of candidates to the candidate list
         katt..nn.1
         hund..nn.1,hundar|pl indef nom
         mås..nn.2,måsars
    '''
    data = request.get_data().decode()  # decode from bytes
    logging.debug('data %s', data)
    tables = data.split('\n')
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    # ppriorv: setting for pextract
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    to_save = []
    for table in tables:
        if not table:
            continue
        logging.debug('table %s', table)
        # TODO move the parsing somewhere else
        forms, pos = table.strip().split('\t')
        forms = forms.split(',')
        baseform = forms[0]
        if '|' in baseform:
            baseform = baseform.split('|')[0]
            forms = [baseform] + forms
        lemgram = helpers.make_identifier(lexicon, baseform, pos, default=True)
        paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
        # put in pextract format
        pex_table = helpers.tableize(','.join(forms), add_tags=False)
        logging.debug('inflect forms %s msd %s', pex_table[0], pex_table[1])
        # is the given form necessarily the baseform?
        restrict_to_baseform = helpers.read_restriction(lexconf)
        # find matching paradigms and save these in the candidate
        res = mp.test_paradigms(pex_table, paras, numex, lms,
                                C.config["print_tables"], C.config["debug"],
                                ppriorv, returnempty=False,
                                baseform=restrict_to_baseform)
        to_save.append(helpers.make_candidate(lexconf['candidatelexiconName'],
                                              lemgram, forms, res, pos))
    logging.debug('will save %s', to_save)

    # save the candidate in karp
    helpers.karp_bulkadd(to_save, resource=lexconf['candidatelexiconName'])
    return jsonify({'saved': to_save,
                    'candidatelexiconName': lexconf['candidatelexiconName']})


@app.route('/candidatelist')
def candidatelist():
    " Return the candidate list"
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    pos = helpers.read_pos(lexconf)
    # ask karp
    q = 'extended||and|%s.search|equals|%s' % (lexconf['pos'], '|'.join(pos))
    res = helpers.karp_query('query', query={'q': q},
                             mode=lexconf['candidateMode'],
                             resource=lexconf['candidatelexiconName'])
    return jsonify({"candidates": helpers.es_all_source(res)})


@app.route('/removecandidate')
def removecandidate(_id=''):
    """
    Remove a candidate from the candidate list
    Use with the lexcion's identifiers
        /removecandidate?identifier=katt..nn.1
    """
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    try:
        identifier = request.args.get('identifier', '')
        # ask karp for the identifier
        q = 'extended||and|%s.search|equals|%s' % ('identifier', identifier)
        res = helpers.karp_query('query', query={'q': q},
                                 mode=lexconf['candidateMode'],
                                 resource=lexconf['candidatelexiconName'])
        _id = helpers.es_first_id(res)
    except Exception as e1:
        logging.error(e1)
        raise e.MflException("Could not find candidate %s" % identifier,
                             code="unknown_candidate")
    # delete it
    ans = helpers.karp_delete(_id, lexconf['candidatelexiconName'])
    return jsonify({"deleted": ans})


@app.route('/recomputecandidates')
def recomputecandiadtes():
    """
     Recompute the candidates' paradigm assignments
     Returns the number of candidates that have been updated
    """
    lexicon = request.args.get('lexicon', C.config['default'])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    postags = helpers.read_pos(lexconf)
    # ppriorv: setting for pextract
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    counter = 0
    for pos in postags:
        # ask karp for all relevant candidates
        q = 'extended||and|%s.search|equals|%s' % (lexconf['pos'], pos)
        res = helpers.karp_query('query', query={'q': q},
                                 mode=lexconf['candidateMode'],
                                 resource=lexconf['candidatelexiconName'])
        # get all relevant paradigms
        paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
        for hit in helpers.es_get_hits(res):
            # go through the candidates
            _id = helpers.es_get_id(hit)
            table = helpers.es_get_source(hit)
            logging.debug('table %s', table)
            # construct a pextract table from the datat
            forms = [table['baseform']]
            for wf in table.get('WordForms', []):
                form = wf['writtenForm']
                msd = wf.get('msd', '')
                if msd:
                    forms.append(form+'|'+msd)
                else:
                    forms.append(form)
            pex_table = helpers.tableize(','.join(forms), add_tags=False)
            logging.debug('inflect forms %s msd %s', pex_table[0], pex_table[1])
            # is the given form necessarily the baseform?
            restrict_to_baseform = helpers.read_restriction(lexconf)
            # get paradigm assignments from pextract
            res = mp.test_paradigms(pex_table, paras, numex, lms,
                                    C.config["print_tables"], C.config["debug"],
                                    ppriorv, returnempty=False,
                                    baseform=restrict_to_baseform)
            # format
            to_save = helpers.make_candidate(lexconf['candidatelexiconName'],
                                             table['identifier'], forms, res,
                                             table['partOfSpeech'])
            counter += 1
        logging.debug('will save %s', to_save)
        # save in karp
        helpers.karp_update(_id, to_save, resource=lexconf['candidatelexiconName'])
    return jsonify({"updated": counter})


@app.errorhandler(Exception)
def handle_invalid_usage(error):
    try:
        request.get_data()
        logging.debug('Error on url %s', request.full_path)
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


# ----Helpers ----------------------------------------------------------------

def read_paradigms(lexicon, pos, mode):
    # get all paradigms from ES
    query = {'size': 10000, 'q': 'extended||and|pos|equals|%s' % pos}
    user = C.config.get('DBPASS', '')
    res = helpers.karp_query('query', query, mode=mode, resource=lexicon, user=user)
    return helpers.es_all_source(res)


def update_model(lexicon, pos, paradigmdict, lexconf, paras=None):
    # update the internal model (language model, alphabet, paradigms)
    if paras is None:
        paras = read_paradigms(lexconf['paradigmlexiconName'], pos,
                               lexconf['paradigmMode'])
    logging.debug('memorize %s paradigms??', len(paras))
    paras, numex, lms, alphabet = mp.build(paras, lexconf["ngramorder"],
                                           lexconf["ngramprior"],
                                           lexicon=lexconf['paradigmlexiconName'],
                                           inpformat='json',
                                           pos=pos,
                                           small=False)
    logging.debug('memorize %s paradigms', len(paras))
    paradigms = {}
    for para in paras:
        paradigms[para.uuid] = para
    paradigmdict[lexicon][pos] = (paradigms, numex, lms, alphabet)


def prepare_restart():
    # Prepare for restart by dumping all paradigms from ES to a file
    # By doing this, start-up takes < 1 minute instead of > 10 minutes.
    new_paradigms = {}
    for lex in C.config['all_lexicons']:
        lexconf = lexconfig.get_lexiconconf(lex['name'])
        new_paradigms[lex['name']] = {}
        for pos in lex['pos']:
            paras = read_paradigms(lexconf['paradigmlexiconName'], pos,
                                   lexconf['paradigmMode'])
            new_paradigms[lex['name']][pos] = paras

    json.dump(new_paradigms, open(C.config['tmpfile'], 'w'))


def offline_restart():
    # Start by reading all paradigms from file (created by prepare_restart)
    tmpparadigmdict = json.load(open(C.config['tmpfile']))
    for lex, plex in tmpparadigmdict.items():
        lexconf = lexconfig.get_lexiconconf(lex)
        paradigmdict[lex] = {}
        for pos, paras in plex.items():
            # pparas = P.load_json(paras, lex=lex, pos=pos)
            update_model(lex, pos, paradigmdict, lexconf, paras=paras)


def start():
    # Start by reading all paradigms from ES. May be very slow on non-local
    # set-ups
    for lex in C.config['all_lexicons']:
        lexconf = lexconfig.get_lexiconconf(lex['name'])
        paradigmdict[lex['name']] = {}
        for pos in lex['pos']:
            update_model(lex['name'], pos, paradigmdict, lexconf)


logging.basicConfig(stream=sys.stderr, level='DEBUG')
paradigmdict = {}


if __name__ == '__main__':
    snabb = sys.argv[-1] == '--snabb'
    offline = sys.argv[-1] == '--offline'
    dump = sys.argv[-1] == '--dump'
    if dump:
        prepare_restart()
    else:
        paradigmdict = {}
        if offline:
            offline_restart()
        else:
            for lexname in C.config['all_lexicons']:
                lexconfdict = lexconfig.get_lexiconconf(lexname['name'])
                paradigmdict[lexname['name']] = {}
                if not snabb:
                    for postag in lexname['pos']:
                        update_model(lexname['name'], postag, paradigmdict, lexconfdict)
        app.run(threaded=True)
