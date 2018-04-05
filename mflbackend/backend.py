import errors as e
from flask import Flask, jsonify, render_template, request
import logging
import sys
sys.path.append('/home/malin/Spraak/pextract/sbextract/src')
import generate as generate
import morphparser as mp
import pextract as pex

import handleparadigms as handle
import helpers

app = Flask(__name__)

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
        lexicons = [l['name'] for l in json.load(open('config/lexicons.json'))]
        return jsonify({"lexicons": lexicons})
    else:
        lexconf = helpers.get_lexiconconf(lex)
        return jsonify(lexconf)


@app.route('/paradigminfo/<paradigm>')
def paradigminfo(paradigm=''):
    " Show information for the paradigm infobox "
    lexicon = request.args.get('lexicon', '')
    paradigm = request.args.get('paradigm', paradigm)
    short = request.args.get('short', '')
    short = short in [True, 'true', 'True']
    lexconf = helpers.get_lexiconconf(lexicon)
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
    pos = request.args.get('pos', '') or\
          request.args.get('partOfSpeech', lexconf['defaultpos'])
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
    pos = request.args.get('pos', '') or\
          request.args.get('partOfSpeech', lexconf['defaultpos'])

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
    if classname == "paradigm":
        # Special case: '?classname=extractparadigm&classval=p14_oxe..nn.1?1=katt&2=a'
        # TODO rename to extractparadigm
        #if classname == "extractparadigm":
        if len(paras) < 1 or len(possible_p) < 1:
            raise e.MflException("Cannot find paradigm %s" % classval)
        var_inst = sorted([(key,val) for key,val in request.args.items() if key.isdigit()])
        var_inst.sort()
        var_inst = [val for key, val in var_inst]
        logging.debug('look for %s as %s' % (classval, pos))
        if len(paras) < 1:
            raise e.MflException("Cannot find paradigm %s" % classval)
        table = helpers.make_table(lexconf, paras[0], var_inst, 0, pos)
        ans = {"Results": [table]}

    else:
        # q = 'extended||and|%s.search|equals|%s||and|%s|equals|%s'\
        #     % (classname, classval, lexconf['pos'], pos)
        # res = helpers.karp_query('statlist',
        #                          {'q': q,
        #                           'mode': lexconf['paradigmMode'],
        #                           'resource': lexconf['paradigmlexiconName'],
        #                           'buckets': '_id'
        #                           }
        #                          )
        # possible_p = [line[0] for line in res['stat_table']]
        # logging.debug('possible_p %s' % possible_p)
        # paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon,
        #                                                pos, possible_p)

        res = generate.run_paradigms(paras, [word], kbest=100, pprior=ppriorv,
                                     lms=lms, numexamples=numex)
        # print('generated', res)
        logging.debug('generated %s results' % len(res))
        ans = {"Results": helpers.format_simple_inflection(lexconf, res, pos=pos)}
    # print('asked', q)
    return jsonify(ans)


@app.route('/inflect')
def inflect():
    " Inflect a word or table "
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = request.args.get('pos', '') or\
          request.args.get('partOfSpeech', lexconf['defaultpos'])
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    ans = handle.inflect_table(table,
                               [paras, numex, lms, config["print_tables"],
                                config["debug"], ppriorv],
                               pos=pos)
    logging.debug('ans')
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
    pos = helpers.get_pos(lexconf, like)
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
        res = generate.run_paradigms(paras, [word], kbest=100, pprior=ppriorv,
                                     lms=lms, numexamples=numex, vbest=20)
        result = helpers.format_simple_inflection(lexconf, res, pos=pos)
    else:
        result = []
    ans = {"Results": result}
    return jsonify(ans)


@app.route('/list')
def listing():
    q = request.args.get('q', '')  # querystring
    s = request.args.get('s', '*')  # searchfield
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = request.args.get('pos', '') or\
          request.args.get('partOfSpeech', '')
    query = []
    if pos:
        query.append('and|%s|startswith|%s' % (lexconf["pos"], pos))

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
    q = request.args.get('q', '')  # querystring
    s = request.args.get('s', '*')  # searchfield
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = request.args.get('pos', '') or\
          request.args.get('partOfSpeech', '')
    size = request.args.get('size', '100')
    start = request.args.get('start', '0')
    extra = request.args.get('extra', 'true')
    extra = extra in ['True', 'true', True]
    query = []
    if pos:
        query.append('and|%s|startswith|%s' % (lexconf["pos"], pos))

    if s == 'class':
        classname = request.args.get('classname', '')
        if q:
            query.append('and|%s|equals|%s' % (classname, q))
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
        for pbucket in res['aggregations']['q_statistics'][lexconf['inflectionalclass'][classname]]['buckets']:
            if extra:
                pcount = len(pbucket[lexconf['extractparadigmpath']]['buckets'])
                ans.append([pbucket["key"], pcount, pbucket["doc_count"]])
            else:
                ans.append([pbucket["key"]])

        logging.debug('extra? %s' % extra)
        return jsonify({"compiled_on": classname, "stats": ans,
                        "fields": ["paradigm", "entries"]})

    elif s == "wf":
        mode = lexconf['lexiconMode']
        ans = helpers.compile_list(query, lexconf["baseform"], q, lexicon,
                                   lexconf["show"], size, start, mode)
        return jsonify({"compiled_on": "wordforms", "stats": ans,
                        "fields": ["wf"]})

    elif s == "paradigm":
        # TODO no need to look in config for this, it should always be the same
        show = ','.join([lexconf['extractparadigm'], 'TransformCategory',
                        '_entries'])
        lexicon = lexconf['paradigmlexiconName']
        mode = lexconf['paradigmMode']
        ans = helpers.compile_list(query, lexconf["extractparadigm"], q,
                                   lexicon, show, size, start, mode)
        res = []
        # TODO iclasses may not be in the same order every time
        iclasses = []
        for hit in ans:
            iclasses = []  # only need one instance
            stats = [hit['MorphologicalPatternID']]
            for iclass in lexconf['inflectionalclass'].keys():
                stats.append(len(hit['TransformCategory'][iclass]))
                iclasses.append(iclass)
            stats.append(hit['_entries'])
            res.append(stats)
        return jsonify({"compiled_on": "paradigm", "stats": res,
                        "fields": iclasses+['entries']})

    else:
        return "Don't know what to do"


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
    pos = request.args.get('pos', '') or\
          request.args.get('partOfSpeech', lexconf['defaultpos'])
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
        fittingparadigms = [p for p in paras]
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
        # else -> increase count for one and members
        # print('ans', ans)
        p = ans[0][1][0][1]
        # print('name', p.name)
        # print('name', p.name)
        # print('lexicon', p.lex)
        # print('ans', ans[0][1][0][1])
        score, para, v = ans[0][1][0]
        handle.add_word_to_paradigm(lexconf['paradigmlexiconName'],
                                    lexconf['lexiconName'], identifier, v,
                                    classes, para, wf_table)

    return jsonify({'paradigm': paradigm, 'identifier': identifier,
                    'var_inst': dict(enumerate(v, 1)), 'classes': classes,
                    'pattern': para.pattern(), 'partOfSpeech': pos})




@app.route('/addcandidates', methods=['POST'])
def addcandidates():
    # TODO test and run
    '''  katt..nn.1
         hund..nn.1,hundar|pl indef nom
         mås..nn.2,måsars
    '''
    data = request.get_data().decode() # decode from bytes
    logging.debug('data %s' % data)
    tables = data.split('\n')
    pos = request.args.get('pos', '') or\
          request.args.get('partOfSpeech', lexconf['defaultpos'])
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    lexicon = request.args.get('lexicon', 'saldomp')
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
        res = mp.test_paradigms(pex_table, paras, numex, lms,
                                 config["print_tables"], config["debug"],
                                 ppriorv, returnempty=False)
        to_save.append(helpers.make_candidate(lexconf['candidatelexiconName'], lemgram, forms, res, pos))
    logging.debug('will save %s' % to_save)

    helpers.karp_bulkadd(to_save, resource=lexconf['candidatelexiconName'])
    return jsonify({'saved': to_save, 'candidatelexiconName': lexconf['candidatelexiconName']})


@app.route('/candidatelist')
def candidatelist():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = request.args.get('pos', '') or\
          request.args.get('partOfSpeech', lexconf['defaultpos'])
    q = 'extended||and|%s.search|equals|%s' % (lexconf['pos'], pos)
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
        /removecandidate?identifier=ABC83Z
    '''
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
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

        return "Error!!\n%s" % error.message, 400
    except Exception:
        return "Oops, something went wrong\n", 500


# TODO how to set these??
# For saldomp, i have increased pprior a lot, from 1.0 to 5.0
config = {"print_tables": False,
          "kbest": 10,
          "debug": False,
          "choose": False
          }


if __name__ == '__main__':
    import json
    # sys.setdefaultencoding('utf8')
    # TODO how to handle the paradigms? In memory? On disk?
    paradigmdict = {}
    for lex in json.load(open('config/lexicons.json')):
        # TODO which lexconf
        lexconf = helpers.get_lexiconconf("saldomp")
        # TODO can't have same pos for many pfiles, in that case, they
        # must be merged
        paradigmdict[lex['name']] = {}
        for pos in lex['pos']:
            update_model(lex['name'], pos, paradigmdict, lexconf)
    app.run()
