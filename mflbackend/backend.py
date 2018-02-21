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


@app.route('/inflectbklass')
def inflectbklass():
    lexicon = request.args.get('lexicon', 'saldomp')
    word = request.args.get('word', '')
    bklass = request.args.get('bklass', '')
    pos = request.args.get('pos', 'nn')
    ppriorv = float(request.args.get('pprior', pprior))
    res = helpers.karp_query('statlist', {'q': 'extended||and|bklass.search|equals|%s||and|pos|startswith|nn' % bklass,
                                  'buckets': 'paradigm.bucket'})
    possible_p = [line[0] for line in res['stat_table']]
    res = generate.test_paradigms(['%s\t%s' % (word, '|'.join(possible_p))],
                                  paradigms, debug=True, kbest=10)
    ans = {"WordForms": helpers.format_simple_inflection(res)}
    print('ans', ans)
    return jsonify(ans)


@app.route('/inflect')
def inflect():
    lexicon = request.args.get('lexicon', 'saldomp')
    table = request.args.get('table', '')
    pos = request.args.get('pos', 'nn')
    ppriorv = float(request.args.get('pprior', pprior))
    ans = handle.inflect_table(table,
                               [paradigms, numexamples, lms, print_tables,
                               debug, ppriorv, choose])
    if 'paradigm' in ans:
        print('made new', ans)
        ans['paradigm'] = str(ans['paradigm'])
    else:
        print('found it', ans)
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
    word = request.args.get('word', '')
    pos = request.args.get('pos', 'nn')
    like = request.args.get('like')
    res = generate.test_paradigms(['%s\t%s' % (word, like)], paradigms, debug=True)
    print('res', res)
    ans = {"WordForms": helpers.format_simple_inflection(res)}
    print('ans', ans)
    return jsonify(ans)


# TODO fortsätt här
@app.route('/addtable')
def add_table():
    lexicon = request.args.get('lexicon', 'saldomp')
    table = request.args.get('table', '')
    pos = request.args.get('pos', 'nn')
    bklass = request.args.get('bklass')
    # get the paradigm
    lemgram = table[0].split('|')[0]
    ans = handle.inflect_table(table,
                               [paradigms, numexamples, lms, print_tables,
                                debug, pprior, choose])
    if ans['new']:
        print('add %s with paradigm %s' % (lemgram, ans['paradigm']))
        para = ans['paradigm']
        handle.add_paradigm(lemgram, para, paradigms)
    # else -> increase count for one and members
    else:
        score, para, v = ans['analyzes']
        print('add %s with analyze %s' % (para.name, v))
        handle.add_word_to_paradigm(lemgram, v, para)

    return jsonify({'added': str(para)})
    # send table to karp


@app.route('/search')
def searchtab():
    return render_template('search.html', infotext="mfl")


@app.route('/compile')
def compile():
    q = request.args.get('q', '')  # querystring
    s = request.args.get('s', '*')  # searchfield
    count, results = 0, []
    if s == "wf":
        res = helpers.karp_query('minientry',
                                 {'q': 'extended||and|baseformC|equals|%s||and|pos|startswith|nn' % q,
                                  'show': 'lemgram,bklass,paradigm,pos,inherent'})
        count = res['hits']['total']
        for r in res['hits']['hits']:
            results.append(r['_source'].get('FormRepresentations', [{}])[0])

        return render_template('wordlist.html', q=q, searchfield=s,
                               count=count, results=results)

    elif s == "paradigm":
        karp_q = 'extended||and|pos|startswith|nn'
        if q:
            logging.debug('q is %s' % q)
            karp_q += '||and|paradigm.search|equals|%s' % q
        res = helpers.karp_query('statistics',
                                 {'q': karp_q,
                                  'cardinality': True,
                                  'buckets': 'paradigm.bucket,bklass.bucket'})
        stats = res['aggregations']['q_statistics']
        buckets = stats['FormRepresentations.paradigm.raw']['buckets']
        count = 'X'  # TODO this is not the correct count

        return render_template('paralist.html', q=q, searchfield=s, count=count, results=buckets)

    elif s == "bklass":
        karp_q = 'extended||and|pos|startswith|nn'
        if q:
            karp_q += '||and|bklass|equals|%s' % q
        res = helpers.karp_query('statistics',
                                 {'q': karp_q,
                                  'cardinality': True,
                                  'buckets':'bklass.bucket.bucket,paradigm.bucket'})
        stats = res['aggregations']['q_statistics']
        buckets = stats['FormRepresentations.bklass']['buckets']
        count = 'X'  # TODO this is not the correct count

        return render_template('bklasslist.html', q=q, searchfield=s,
                               count=count, results=buckets)


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

if __name__ == '__main__':
    # sys.setdefaultencoding('utf8')
    parafile = sys.argv[1]
    # TODO how to set these?? i have increased pprior a lot, from 1.0 to 5.0
    print_tables, kbest, ngramorder, ngramprior, debug, pprior,choose = False, 10, 3, 0.01, False, 5.0, False
    paradigms, numexamples, lms = mp.build(parafile, ngramorder, ngramprior)
    parafile = open(parafile, encoding='utf8').readlines()
    app.run()
