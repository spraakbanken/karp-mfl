from flask import Flask, jsonify, render_template, request
import logging
import sys
sys.path.append('pextract')
import pextract.generate as generate
import pextract.morphparser as mp

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
    ans = {}
    if res['hits']['total'] > 0:
        obj = res['hits']['hits'][0]['_source']
        if short:
            short_obj = {}
            short_obj['MorphologicalPatternID'] = obj['MorphologicalPatternID']
            short_obj['partOfSpeech'] = obj['_partOfSpeech']
            short_obj['entries'] = obj['_entries']
            print('short', obj.get('TransformCategory'), obj.keys())
            for classname, classval in obj.get('TransformCategory', {}).items():
                print('class',classname,classval)
                if not 'categories' in short_obj:
                    short_obj['categories'] = {}
                short_obj['categories'][classname] = classval
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
        % (classname, classval, lexconf["pos"], pos)
    res = helpers.karp_query('statlist',
                             {'q': q,
                              'mode': lexconf['lexiconMode'],
                              'buckets': lexconf['extractparadigm']+'.bucket'}
                             )
    possible_p = [line[0] for line in res['stat_table']]
    paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
    res = generate.test_name_paradigms(['%s\t%s' % (word, '|'.join(possible_p))],
                                  paras, debug=True, kbest=10, pprior=ppriorv,
                                  lms=lms, numexamples=len(paras))
    ans = {"Results": helpers.format_simple_inflection(res, pos=pos)}
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
        for hit in ans:
            stats = [hit['MorphologicalPatternID']]
            for iclass in lexconf['inflectionalclass'].keys():
                stats.append(len(hit['TransformCategory'][iclass]))
            stats.append(hit['_entries'])
            res.append(stats)
        return jsonify({"compiled_on": "paradigm", "stats": res,
                        "fields": list(lexconf['inflectionalclass'].keys())+['entries']})

    else:
        return "Don't know what to do"


# Update
@app.route('/renameparadigm')
def renameparadigm():
    # TODO!
    return "Not implemented"


@app.route('/addtable')
def add_table():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = request.args.get('pos', lexconf['defaultpos'])
    identifier = request.args.get('identifier', '')
    paradigm = request.args.get('paradigm', '')
    classes = request.args.getlist('class', '')
    is_new = request.args.get('new', False)
    is_new = is_new in ['True', 'true', True]
    ans = ''
    try:
        classes = dict([c.split(':') for c in classes.split(',')])
    except:
        e = Exception()
        e.message = "Could not parse classes. Format should be 'classname1:apa,classname2:bepa'" % (classes)
        raise e
    if paradigm:
        # TODO make work. return score, para, var_inst
        ans = handle.validate_paradigm(table, paradigm, pos, lexicon)
    if not ans:
        paras, numex, lms = helpers.relevant_paradigms(paradigmdict, lexicon, pos)
        ans = handle.inflect_table(table,
                                   [paras, numex, lms,
                                    config["print_tables"],
                                    config["debug"],
                                    lexconf["pprior"]],
                                   pos=pos,
                                   kbest=1)

    if ans['new']:
        para = ans['extractparadigm']
        # TODO make work
        handle.add_paradigm(identifier, para, paras, classes, identifier)
    # else -> increase count for one and members
    else:
        score, para, v = ans['analyzes']
        # TODO make work
        handle.add_word_to_paradigm(identifier, v, classes, para)

    return jsonify({'added': str(para)})


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
    import os.path
    # sys.setdefaultencoding('utf8')
    # TODO how to handle the paradigms? In memory? On disk?
    paradigmdict = {}
    for lex in json.load(open('config/lexicons.json')):
        # TODO which lexconf
        lexconf = helpers.get_lexiconconf("saldomp")
        # TODO can't have same pos for many pfiles, in that case, they
        # must be merged
        paradigmdict[lex['name']] = {}
        for pfile in lex['pfiles']:
            pos = os.path.basename(os.path.splitext(pfile)[0])

            print("reading %s" % pfile)
            parafile = open(pfile, encoding='utf8').readlines()
            para, numex, lms = mp.build(pfile, lexconf["ngramorder"],
            # TODO small should be true
                                        lexconf["ngramprior"]) #, small=True)
            paradigmdict[lex['name']][pos] = ((para, numex, lms))
    #from pympler import asizeof
    #print('p big size', asizeof.asizeof(paradigmdict))

    # parafile = sys.argv[1]
    # lexconf = helpers.get_lexiconconf("saldomp")
    # paradigms, numexamples, lms = mp.build(parafile, lexconf["ngramorder"], lexconf["ngramprior"])
    # parafile = open(parafile, encoding='utf8').readlines()
    app.run()
