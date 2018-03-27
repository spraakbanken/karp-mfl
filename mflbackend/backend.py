from flask import Flask, jsonify, render_template, request
import logging
import sys
sys.path.append('pextract')
import pextract.generate as generate
import pextract.morphparser as mp
import pextract.pextract as pex

import handleparadigms as handle
import helpers

app = Flask(__name__)

# TODO handle tags
# TODO first check if given forms and restriction already exists in karp?


# metadata and documentation
@app.route('/')
@app.route('/index')
def doc():
    return render_template('doc.html', url=request.url_root)


@app.route('/lexicon')
@app.route('/lexicon/<lex>')
def lexiconinfo(lex=''):
    lex = request.args.get('lexicon', lex)
    if not lex:
        lexicons = [l['name'] for l in json.load(open('config/lexicons.json'))]
        return jsonify({"lexicons": lexicons})
    else:
        lexconf = helpers.get_lexiconconf(lex)
        return jsonify(lexconf)


@app.route('/paradigminfo')
def paradigminfo():
    lexicon = request.args.get('lexicon', '')
    paradigm = request.args.get('paradigm', '')
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


@app.route('/pos')
@app.route('/partofspeech')
def all_pos():
    lexicon = request.args.get('lexicon', 'saldomp')
    # TODO also check in lexicon? give combined info about
    # which exist and which that have paradigms?
    logging.debug(dir(paradigmdict[lexicon]))
    logging.debug('ok %s' % list(paradigmdict[lexicon].keys()))
    return jsonify({"pos": list(paradigmdict[lexicon].keys())})


# TODO Probably remove this ??
@app.route('/autocomplete')
def autocomplete():
    return render_template('doc.html', url=request.url_root)


# TODO Probably remove this ??
@app.route('/autocompleteparadigm')
def autocompleteparadigm():
    lexicon = request.args.get('q', '')
    return render_template('doc.html', url=request.url_root)


# TODO Probably remove this ??
@app.route('/search')
def searchtab():
    return render_template('search.html', infotext="mfl")

# För alla inflect, ge tillbaka
#   lemgram
#   grundform
#   paradigmnamn
#   ordklass
#   annan klass

# Test inflections
@app.route('/inflectclass')
def inflectclass():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    word = request.args.get('wordform', '')
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    classname = request.args.get('classname', '')
    classval = request.args.get('classval', '')
    pos = request.args.get('pos', lexconf['defaultpos'])
    q = 'extended||and|%s.search|equals|%s||and|%s|startswith|%s'\
        % (classname, classval, "pos", pos)
    # TODO using minientry will speed up things, but paradigm solts won't be happy
    res = helpers.karp_query('query',
                             {'q': q,
                              'mode': lexconf['paradigmMode'],
                              'resource': lexconf['paradigmlexiconName'],
                              'buckets': 'MorphologicalPatternID.bucket',
                              'show': 'standard'}
                             )
    #res = helpers.karp_query('statlist',
    #                         {'q': q,
    #                          'mode': lexconf['lexiconMode'],
    #                          'buckets': lexconf['extractparadigm']+'.bucket'}
    #                         )
    #possible_p = [line[0] for line in res['stat_table']][0]
    print('conf1', lexconf)
    #paras, numex, lms = helpers.relevant_paradigms(lexconf, paradigmdict, lexicon, pos, possible_p)

    numex, lms = paradigmdict[lexicon][pos]
    paras = helpers.load_paradigms(res, lexconf)
    print('available', [p.name for p in paras])
    res = generate.run_paradigms(paras, [word], kbest=100, pprior=ppriorv, lms=lms, numexamples=numex)
    # res = generate.test_name_paradigms(['%s\t%s' % (word, '|'.join(possible_p))],
    #                               paras, debug=True, kbest=10, pprior=ppriorv,
    #                               lms=lms, numexamples=len(paras))
    print('generated', res)
    print('generated', len(res))
    ans = {"Results": helpers.format_simple_inflection(res, pos=pos)}
    print('asked', q)
    return jsonify(ans)


@app.route('/inflect')
def inflect():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = request.args.get('pos', lexconf['defaultpos'])
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
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    word = request.args.get('wordform', '')
    # TODO remove, should be the lemgrams pos
    # conf shoud tell how to get pos from lemgram
    pos = request.args.get('pos', lexconf['defaultpos'])
    like = request.args.get('like')
    print('like',like)
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    # TODO ask karp for the right paradigms?
    # q = 'extended||and|%s.search|equals|%s' % (lexconf['lemgram'], lemgram)
    # res = helpers.karp_query('minientry',
    #                         {'q': query, 'show': lexconf["show"],
    #                           'size': size, 'start': start},
    #                         mode=lexconf['lexiconmode'])
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    logging.debug('test %s paradigms' % len(paras))
    res = generate.test_member_paradigms(['%s\t%s' % (word, like)], paras,
                                  debug=True, pprior=ppriorv, lms=lms,
                                  numexamples=len(paras))
    ans = {"Results": helpers.format_simple_inflection(res, pos=pos), 'new': False}
    # print('ans', ans)
    return jsonify(ans)


@app.route('/paradigms')
def paradigms():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = request.args.get('pos', lexconf['defaultpos'])
    karp_q = 'extended||and|%s|startswith|%s||and|lexiconName|equals|%s'\
             % (lexconf['pos'], pos, lexicon)
    buckets = [lexconf['extractparadigm']] + list(lexconf['inflectionalclass'].keys())
    res = helpers.karp_query('statistics',
                             {'q': karp_q,
                              'cardinality': True,
                              'mode': lexconf['lexiconMode'],
                              'buckets': ','.join(['%s.bucket' % b for b in buckets])})
    stats = res['aggregations']['q_statistics']
    buckets = stats[lexconf["paradigmpath"]]['buckets']
    count = stats["doc_count"]
    return render_template('paralist.html', count=count, results=buckets)


@app.route('/list')
def list():
    q = request.args.get('q', '')  # querystring
    s = request.args.get('s', '*')  # searchfield
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = request.args.get('pos', '')
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
        return jsonify({"compiled_on": "wf",
                        "list": res['stat_table'],
                        "fields": ["entries"]})
    else:
        return "Don't know what to do"


# TODO all compiled_on: visa entries sist
@app.route('/compile')
def compile():
    q = request.args.get('q', '')  # querystring
    s = request.args.get('s', '*')  # searchfield
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = request.args.get('pos', '')
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
            query.append('||and|%s|equals|%s' % (classname, q))
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
                pcount = len(pbucket[lexconf['paradigmbucketpath']]['buckets'])
                ans.append([pbucket["key"], pcount, pbucket["doc_count"]])
            else:
                ans.append([pbucket["key"]])

        print('extra', extra)
        return jsonify({"compiled_on": classname, "stats": ans,
                        "fields": ["paradigm", "entries"]})

    if s == "wf":
        mode = lexconf['lexiconMode']
        ans = helpers.compile_list(query, lexconf["baseform"], q, lexicon,
                                   lexconf["show"], size, start, mode)
        return jsonify({"compiled_on": "wordforms", "stats": ans, "fields": ["entries"]})

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
        for hit in ans:
            iclasses = []
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
    identifier = request.args.get('identifier', '')
    paradigm = request.args.get('paradigm', '')
    if not identifier or not paradigm or not pos:
        e = Exception()
        e.message = "Both identifier, partOfSpeech and paradigm must be given!"
        raise e
    classes = request.args.getlist('class', '')
    is_new = request.args.get('new')
    is_new = is_new in ['True', 'true', True]
    try:
        print(classes)
        classes = dict([c.split(':') for c in classes])
    except Exception as e1:
        e = Exception()
        e.message = "Could not parse classes. Format should be 'classname:apa,classname2:bepa'" % (classes)
        raise e
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    if is_new and paradigm in [p.name for p in paras]:
        e = Exception()
        e.message = "Paradigm name %s is already used" % (paradigm)
        raise e

    pex_table = helpers.tableize(table, add_tags=False)
    wf_table = helpers.lmf_wftableize(paradigm, table, classes, baseform='',
                                      identifier=identifier, pos=pos,
                                      resource=lexconf['lexiconName'])
    if not is_new:
        fittingparadigms = [p for p in paras if p.name == paradigm]

    else:
       fittingparadigms = [p for p in paras]

    print('fitting', fittingparadigms)
    ans = mp.test_paradigms([pex_table], fittingparadigms, numex, lms,
                            config["print_tables"], config["debug"],
                            lexconf["pprior"], returnempty=False)
    if not is_new and len(ans) < 1:
        # ans = ans[0][1]  # use first variable instantiation (if many),
        #                 # [1] to get score, p, v
        print('ans', ans)
        logging.warning("Could not inflect %s as %s" % (table, paradigm))
        e = Exception()
        e.message = "Table can not belong to paradigm %s" % (paradigm)
        raise e

    if not ans:
        print(ans)
        # TODO make work
        para = pex.learnparadigms([pex_table])[0]
        print('para is', para)
        v = para.var_insts
       # ans = mp.test_paradigms([pex_table], [para], numex, lms,
       #                          config["print_tables"], config["debug"],
       #                          lexconf["pprior"], returnempty=False)
       # score, para, v = ans[0][1][0]
        handle.add_paradigm(lexconf['paradigmlexiconName'],
                            lexconf['lexiconName'], paradigm, para, paras,
                            identifier, pos, classes, wf_table)
    else:
        # else -> increase count for one and members
        p = ans[0][1][0][1]
        print('name', p.name)
        print('name', p.name)
        print('lexicno', p.lex)
        print('ans',ans[0][1][0][1])
        score, para, v = ans[0][1][0]
        # TODO make work
        # TODO send along table to save
        handle.add_word_to_paradigm(lexconf['paradigmlexiconName'],
                                    lexconf['lexiconName'], identifier, v,
                                    classes, para, wf_table)

    return jsonify({'added': paradigm, 'identifier': identifier,
                    'var_inst': dict(enumerate(v, 1)), 'classes': classes,
                    'pattern': para.pattern()})


#  add to doc
# @app.route('/inflectionalclass')
# def inflectionalclass():
#     lexicon = request.args.get('lexicon', 'saldomp')
#     lexconf = helpers.get_lexiconconf(lexicon)
#     iclass = request.args.get('class')
#     pos = request.args.get('pos', lexconf['defaultpos'])
#     karp_q = 'extended||and|%s|startswith|%s' % (lexconf["pos"], pos)
#     buckets = [iclass, lexconf['extractparadigm']]
#     for c in lexconf['inflectionalclass'].keys():
#         if c != iclass:
#             buckets.append(c)
#     res = helpers.karp_query('statistics',
#                              {'q': karp_q,
#                               'cardinality': True,
#                               'mode': lexconf['lexiconMode'],
#                               'buckets': ','.join(['%s.bucket' % b for b in buckets])})
#                               # 'buckets':'bklass.bucket.bucket,paradigm.bucket'})
#     stats = res['aggregations']['q_statistics']
#     buckets = stats[lexconf["inflectionalclass"][iclass]]['buckets']
#     # buckets = stats['FormRepresentations.bklass']['buckets']
#     count = stats["doc_count"]
#     return render_template('bklasslist.html', count=count, results=buckets)


def read_paradigms(lexicon, pos, mode):
    # get all paradigms from ES
    query = {'size': 10000, 'q': 'extended||and|pos|equals|%s' % pos}
    res = helpers.karp_query('query', query, mode=mode, resource=lexicon)
    return [hit['_source'] for hit in res['hits']['hits']]


def update_model(lexicon, pos, paradigmdict, conf):
    #paras = read_paradigms(conf['paradigmlexiconName'], pos, conf['paradigmMode'])
    # para, numex, lms = mp.build(paras, lexconf["ngramorder"],
    #                             lexconf["ngramprior"],
    #                             conf['paradigmlexiconName'],
    #                             inpformat='json')
    paradigmdict[lexicon][pos] = 1, 0



logging.basicConfig(stream=sys.stderr, level='DEBUG')


@app.errorhandler(Exception)
def handle_invalid_usage(error):
    try:
        print(error)
        print(dir(error))
        request.get_data()
        logging.debug('Error on url %s' % request.full_path)
        logging.exception(error)

        return "Error!!\n%s" % error.message, 400
    except Exception:
        return "Oops, something went wrong\n", 500


# TODO how to set these?? for saldomp, i have increased pprior a lot, from 1.0 to 5.0
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

    # import os.path
        # for pfile in lex['pfiles']:
        #     pos = os.path.basename(os.path.splitext(pfile)[0])

        #     print("reading %s" % pfile)
        #     parafile = open(pfile, encoding='utf8').readlines()
        #     para, numex, lms = mp.build(pfile, lexconf["ngramorder"],
        #                                 lexconf["ngramprior"],
        #                                 lexicon=lex['name']) #, small=True)
        #     # TODO small should be true
        #     paradigmdict[lex['name']][pos] = ((para, numex, lms))
    #from pympler import asizeof
    #print('p big size', asizeof.asizeof(paradigmdict))

    # parafile = sys.argv[1]
    # lexconf = helpers.get_lexiconconf("saldomp")
    # paradigms, numexamples, lms = mp.build(parafile, lexconf["ngramorder"], lexconf["ngramprior"])
    # parafile = open(parafile, encoding='utf8').readlines()
