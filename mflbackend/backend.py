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


@app.route('/')
@app.route('/index')
def doc():
    return render_template('doc.html', url=request.url_root)


@app.route('/inflectclass')
def inflectbklass():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    word = request.args.get('word', '')
    for d in lexconf['inflectionalclass'].keys():
        if d in request.args:
            bklasskey = d
            bklassval = request.args.get(bklasskey)
    pos = request.args.get('pos', lexconf['defaultpos'])
    q = 'extended||and|%s.search|equals|%s||and|%s|startswith|%s'\
        % (bklasskey, bklassval, lexconf["pos"], pos)
    res = helpers.karp_query('statlist',
                             {'q': q,
                              'mode': lexconf['mode'],
                              # TODO from config!
                              'buckets': 'paradigm.bucket'}
                             )
    possible_p = [line[0] for line in res['stat_table']]
    paradigms, numex, lms = paradigmdict[lexicon][pos]
    res = generate.test_paradigms(['%s\t%s' % (word, '|'.join(possible_p))],
                                  paradigms, debug=True, kbest=10)
    ans = {"WordForms": helpers.format_simple_inflection(res)}
    return jsonify(ans)


@app.route('/inflect')
def inflect():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = request.args.get('pos', lexconf['defaultpos'])
    ppriorv = float(request.args.get('pprior', lexconf["pprior"]))
    paradigms, numex, lms = paradigmdict[lexicon][pos]
    ans = handle.inflect_table(table,
                               [paradigms, numex, lms, config["print_tables"],
                                config["debug"], ppriorv, config["choose"]])
    if 'paradigm' in ans:
        # print('made new', ans)
        ans['paradigm'] = str(ans['paradigm'])
    else:
        # print('found it', ans)
        ans['analyzes'] = ''  # TODO can't string encode this
    # print('res', res)
    # ans = {"WordForms": helpers.format_inflection(res, kbest, debug=debug)}
    # if not res:
    #     ans = {'new': True, 'pattern': '%s' % generate.make_new_paradigm(table),
    #            'WordForms': helpers.tableize(table)}
    # print('ans', ans)
    return jsonify(ans)


@app.route('/inflectlike')
def inflectlike():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    word = request.args.get('word', '')
    pos = request.args.get('pos', lexconf['defaultpos'])
    like = request.args.get('like')
    print(paradigmdict[lexicon][pos])
    paradigms, numex, lms = paradigmdict[lexicon][pos]
    res = generate.test_paradigms(['%s\t%s' % (word, like)], paradigms,
                                  debug=True)
    ans = {"Results": helpers.format_simple_inflection(res)}
    # print('ans', ans)
    return jsonify(ans)


@app.route('/addtable')
def add_table():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    table = request.args.get('table', '')
    pos = request.args.get('pos', lexconf['defaultpos'])
    bklass = request.args.get('class')  # TODO go through all classes and see if any matching are in there
    # TODO handle class
    # TODO get the paradigm, ?and tell where the paradigm is found?
    lemgram = table[0].split('|')[0]
    paradigms, numex, lms = paradigmdict[lexicon][pos]
    ans = handle.inflect_table(table,
                               [paradigms, numex, lms,
                                config["print_tables"],
                                config["debug"],
                                lexconf["pprior"],
                                config["choose"]])
    if ans['new']:
        # print('add %s with paradigm %s' % (lemgram, ans['paradigm']))
        para = ans['extractparadigm']
        handle.add_paradigm(lemgram, para, paradigms)
    # else -> increase count for one and members
    else:
        score, para, v = ans['analyzes']
        # print('add %s with analyze %s' % (para.name, v))
        handle.add_word_to_paradigm(lemgram, v, para)

    return jsonify({'added': str(para)})
    # send table to karp


@app.route('/search')
def searchtab():
    return render_template('search.html', infotext="mfl")


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
                              'mode': lexconf['mode'],
                              'buckets': ','.join(['%s.bucket' % b for b in buckets])})
    stats = res['aggregations']['q_statistics']
    buckets = stats[lexconf["paradigmpath"]]['buckets']
    count = stats["doc_count"]
    return render_template('paralist.html', count=count, results=buckets)


# TODO add to doc
@app.route('/inflectionalclass')
def inflectionalclass():
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    iclass = request.args.get('class')
    pos = request.args.get('pos', lexconf['defaultpos'])
    karp_q = 'extended||and|%s|startswith|%s' % (lexconf["pos"], pos)
    buckets = [iclass, lexconf['extractparadigm']]
    for c in lexconf['inflectionalclass'].keys():
        if c != iclass:
            buckets.append(c)
    res = helpers.karp_query('statistics',
                             {'q': karp_q,
                              'cardinality': True,
                              'mode': lexconf['mode'],
                              'buckets': ','.join(['%s.bucket' % b for b in buckets])})
                              # 'buckets':'bklass.bucket.bucket,paradigm.bucket'})
    stats = res['aggregations']['q_statistics']
    buckets = stats[lexconf["inflectionalclass"][iclass]]['buckets']
    # buckets = stats['FormRepresentations.bklass']['buckets']
    count = stats["doc_count"]
    return render_template('bklasslist.html', count=count, results=buckets)


@app.route('/compile')
def compile():
    q = request.args.get('q', '')  # querystring
    s = request.args.get('s', '*')  # searchfield
    lexicon = request.args.get('lexicon', 'saldomp')
    lexconf = helpers.get_lexiconconf(lexicon)
    pos = request.args.get('pos', lexconf['defaultpos'])
    count, results = 0, []

    if s == "wf":
        q = 'extended||and|%s|equals|%s||and|%s|startswith|%s'\
            % (lexconf["baseform"], lexconf["pos"], q, pos),
        res = helpers.karp_query('minientry',
                                 {'q': q,
                                  'mode': lexconf['mode'],
                                  'show': lexconf["show"]})
        count = res['hits']['total']
        # TODO how to show??
        for r in res['hits']['hits']:
            results.append(r['_source'].get('FormRepresentations', [{}])[0])

        return render_template('wordlist.html', q=q, searchfield=s,
                               count=count, results=results)

    elif s == "paradigm":
        # TODO implement when we know if we will have an index
        # with paradigms and what information that will be there
        karp_q = 'extended||and|%s|startswith|%s' % (lexconf["pos"], pos)
        if q:
            logging.debug('q is %s' % q)
            karp_q += '||and|%s.search|equals|%s' % (lexconf["lemgram"], q)
            res = helpers.karp_query('minientry',
                                     {'q': karp_q,
                                      'mode': lexconf['mode'],
                                      'show': lexconf['extractparadigm']})
            # TODO how to get the path?
            ps = [hit['_source'].get('FormRepresentations', [{}])[0].get('paradigm', '') for hit in res['hits']['hits']]
            karp_q = 'extended||and|%s|startswith|%s||and|%s.search|equals|%s'\
                     % (lexconf['pos'], pos, lexconf['extractparadigm'], '|'.join(set(ps)))

        buckets = [lexconf['extractparadigm']] + list(lexconf['inflectionalclass'].keys())
        res = helpers.karp_query('statistics',
                                 {'q': karp_q,
                                  'cardinality': True,
                                  'mode': lexconf['mode'],
                                  'buckets': ','.join(['%s.bucket' % b for b in buckets])})
        stats = res['aggregations']['q_statistics']
        buckets = stats[lexconf['paradigmbucketpath']]['buckets']
        count = stats["doc_count"]

        return render_template('paralist.html', q=q, searchfield=s,
                               count=count, results=buckets)

    elif s in lexconf["inflectionalclass"].keys():
        karp_q = 'extended||and|%s|startswith|%s' % (lexconf['pos'], pos)
        if q:
            karp_q += '||and|%s|equals|%s' % (s, q)

        buckets = [s, lexconf['extractparadigm']]
        for c in lexconf['inflectionalclass'].keys():
            if c != s:
                buckets.append(c)
        res = helpers.karp_query('statistics',
                                 {'q': karp_q,
                                  'cardinality': True,
                                  'mode': lexconf['mode'],
                                  'buckets': ','.join(['%s.bucket' % b for b in buckets])})
        stats = res['aggregations']['q_statistics']
        buckets = stats[lexconf['paradigmbucketpath']]['buckets']
        count = stats["doc_count"]

        return render_template('bklasslist.html', q=q, searchfield=s,
                               count=count, results=buckets)
    else:
        return "Don't know what to do"


logging.basicConfig(stream=sys.stderr, level='DEBUG')


@app.errorhandler(Exception)
def handle_invalid_usage(error):
    try:
        request.get_data()
        logging.debug('Error on url %s' % request.full_path)
        logging.exception(error)

        return error.message, 400
    except Exception:
        return "Oops, something went wrong\n", 500

# TODO how to set these?? for saldomp, i have increased pprior a lot, from 1.0 to 5.0
config = {"print_tables": False,
          "kbest": 10,
          "debug": False,
          "choose": False
          }


if __name__ == '__main__':
    import collections
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
                                        lexconf["ngramprior"])
            paradigmdict[lex['name']][pos] = ((para, numex, lms))

    # parafile = sys.argv[1]
    # lexconf = helpers.get_lexiconconf("saldomp")
    # paradigms, numexamples, lms = mp.build(parafile, lexconf["ngramorder"], lexconf["ngramprior"])
    # parafile = open(parafile, encoding='utf8').readlines()
    app.run()
