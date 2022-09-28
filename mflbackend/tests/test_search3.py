# python3
import base64
import json
import random
import time
import traceback
import urllib.request
import urllib.parse

import pytest

from utility import get_json

# TODO some inflection tests fail. Change to warnings?

# the url to be tested
host = "http://localhost:5000"

simple_urls = ["index", "lexicon", "partofspeech", "defaulttable"]


def test_lexicon(client):
    resp = get_json(client, "/lexicon")

    assert "lexicons" in resp
    lex = resp.get("lexicons")
    assert "name" in lex[0]
    assert "open" in lex[0]


@pytest.mark.parametrize("lex", ["votiska"])
def test_lexiconname(client, lex):
    resp = get_json(client, f"/lexicon/{lex}")
    print(f"resp = {resp}")
    assert resp["lexiconName"] == lex


#     call('lexicon/'+lex)


# def wordinfo(word):
#     q, res = call('wordinfo/'+word)
#     assert type(res.get('WordForms', [])) is list, 'Bad Wordforms %s' % q
#     res['baseform']
#     res["identifier"]
#     res["lexiconName"]
#     res["paradigm"]
#     assert res["paradigm_entries"].isdigit(), 'Bad paradigm_entries %s' % q
#     res["partOfSpeech"]
#     res["variables"][0]['first-attest']


@pytest.mark.parametrize("para", ["p1_ahkõrõ..nn.1"])
def test_paradigminfo(client, para):
    #     q, res = call('paradigminfo/'+para)
    res = get_json(client, f"paradigminfo/{para}")
    assert "MorphologicalPatternID" in res
    assert res["MorphologicalPatternID"] == para

    # trans = res["TransformCategory"]
    # assert type(trans) is dict, "Bad TransFormCategory %s" % q
    trans = res["TransformSet"]
    assert isinstance(trans[0]["GrammaticalFeatures"], dict)
    assert res is None


#     process = trans[0]["Process"][0]
#     process["operator"]
#     process["processType"]
#     process["variableNum"]
#     res["VariableInstances"][0]['first-attest']
#     assert type(res["_entries"]) is int or res["_entries"].isdigit(), 'Bad _entries %s' % q
#     name = res["_lexiconName"]
#     res["_partOfSpeech"]
#     res["_uuid"]
#     assert res["lexiconName"] == name, 'Bad lexiconName %s %s %s' % (q, res['lexiconName'], name)


# def pos():
#     q, res = call('partofspeech')
#     assert type(res['partOfSpeech']) is list, 'Bad partOfSpeech %s' % q


# def defaulttable(pos="nn"):
#     q, res = call('defaulttable', {'pos': pos})
#     res["partOfSpeech"] == pos
#     row = res["WordForms"][0]
#     row["msd"]
#     row["writtenForm"]


# def listpara(pos="nn"):
#     paras = {'pos': pos, 'c': 'paradigm'}
#     test_list('list', pos, paras, 'list', 5)


# def listbklass(pos="nn"):
#     paras = {'pos': pos, 'c': 'class', 'classname': 'bklass'}
#     test_list('list', pos, paras, 'list', 3)


# def compilebklass(pos="nn"):
#     paras = {'pos': pos, 'c': 'class', 'classname': 'bklass'}
#     test_list('compile', pos, paras, 'stats', 2)


# def compilewf(pos="nn"):
#     paras = {'pos': pos, 'c': 'wf'}
#     test_list('compile', pos, paras, 'stats', 10)


# def compileparadigm(pos="nn"):
#     paras = {'pos': pos, 'c': 'paradigm'}
#     test_list('compile', pos, paras, 'stats', 8)


# def test_list(action, pos, paras, list, size):
#     paras['size'] = size
#     q, res = call(action, paras)
#     # print(res["compiled_on"], paras['c'])
#     if paras['c'] == 'class':
#         assert_it(res["compiled_on"], paras['classname'])
#     elif paras['c'] == 'wf':
#         assert_it(res["compiled_on"], 'wordform')
#     else:
#         assert_it(res["compiled_on"], paras['c'])
#     fields = len(res["fields"])
#     assert len(res[list][0]) == fields, 'field len %s /= %s, %s' % (len(res[list][0]), fields, q)
#     assert len(res[list]) == size, 'size not ok %s /= %s, %s' % (len(res[list]), size, q)


# def candidatelist():
#     q, res = call('candidatelist')
#     res['candidates']
#     cand = random.choice(res['candidates'])
#     cand['baseform']
#     cand['identifier']
#     cand['lexiconName']
#     cand['maxScore']
#     cand['partOfSpeech']
#     assert type(cand['WordForms']) is list, 'Bad Wordforms'
#     cp = random.choice(cand['CandidateParadigms'])
#     cp['VariableInstances']["1"]
#     cp["name"]
#     cp["score"]
#     cp["uuid"]


# def inflectlike():
#     # saldomp
#     # Bugg: seglet får fel variabler
#     lemgram = random.choice(['apelsin..nn.1','segel..nn.1','storm..nn.1',
#                              'timtal..nn.1', 'byxa..nn.1', 'katt..nn.1',
#                              'lus..nn.1','byggnad..nn.1','toffel..nn.1',
#                              'schampo..nn.1'])
#     base = lemgram.split('.')[0]
#     params = {'like': lemgram, 'wordform': base, 'pos': 'nn', 'lexicon': 'saldomp'}
#     q, res = call('inflectlike', params)
#     compareinflection(res, lemgram)


# def compareinflection(res, lemgram, diff=False, force=True):
#     ql, lres = call('wordinfo/'+lemgram, {'lexicon': 'saldomp'})
#     base = lemgram.split('.')[0]
#     test_f = assert_it if force else test_it
#     try:
#         assert res['Results'], res['Results']
#     except:
#         handle(force, res)
#         return
#     infl = res['Results'][0]
#     if not test_f(infl['baseform'], base):
#         return
#     _id = infl['identifier']
#     if not test_f(_id.split('.')[0], base):
#         return
#     if not test_f(_id, lemgram, eq=False):
#         return
#     if not diff:
#         try:
#             assert infl['paradigm_entries']
#             assert infl['score']
#         except:
#             handle(force, infl)

#     if not test_f(infl['paradigm'], lres['paradigm'], eq=not diff):
#         return
#     try:
#         assert base.startswith(infl['variables']['1'])
#     except:
#         handle(force, '%s != %s' % (infl['variables']['1'], base))
#         return
#     comparetables(infl['WordForms'], lres['WordForms'], msd=False, force=force)


# def handle(force, res):
#     if force:
#         raise
#     print('Warning, test failed', res)
#     traceback.print_exc()


# def comparetables(table1, table2, msd=True, force=True):
#     test_f = assert_it if force else test_it
#     for ix, wf in enumerate(table1):
#         wf2 = table2[ix]
#         if not test_f(wf.keys(), wf2.keys()):
#             return
#         for key, val in wf.items():
#             if not msd and key == 'msd':
#                 continue
#             if not test_f(wf[key], wf2[key]):
#                 return


# def inflectbklass():
#     # saldomp
#     lemgram, bklass = random.choice([('katt..nn.1', 3),('lus..nn.1', 7),
#                                      ('byggnad..nn.1', 3), ('toffel..nn.1', 1),
#                                      ('schampo..nn.1', 4)])
#     base = lemgram.split('.')[0]
#     params = {'class': 'bklass', 'classname': 'bklass', 'classval': bklass,
#               'wordform': base, 'pos': 'nn', 'lexicon': 'saldomp'}
#     q, res = call('inflectclass', params)
#     compareinflection(res, lemgram)


# def inflectparadigm():
#     # saldomp
#     # TODO test var_inst
#     lemgram, bklass = random.choice([('rallarros..nn.1', 'p100_rallarros..nn.1'),
#                                      ('namnskylt..nn.1', 'p2_namnskylt..nn.1'),
#                                      ('galgbacke..nn.1', 'p12_galgbacke..nn.1'),
#                                      ('paralympics..nn.1', 'p94_paralympics..nn.1'),
#                                      ('gas..nn.2', 'p169_gas..nn.2')])
#     base = lemgram.split('.')[0]
#     params = {'class': 'bklass', 'classname': 'paradigm',
#               'classval': bklass, 'wordform': base, 'pos': 'nn',
#               'lexicon': 'saldomp'}
#     q, res = call('inflectclass', params)
#     compareinflection(res, lemgram)


# def inflect():
#     # NB! This test may fail since the
#     # saldomp
#     lemgram = random.choice(['rallarros..nn.1', 'skrutt..nn.1',
#                              'namnskylt..nn.1', 'getabock..nn.1',
#                              'galgbacke..nn.1', 'nisse..nn.1',
#                              'svamp..nn.1', 'mat..nn.1'])
#     base = lemgram.split('.')[0]
#     params = {'table': base, 'pos': 'nn', 'lexicon': 'saldomp'}
#     q, res = call('inflect', params)
#     compareinflection(res, lemgram, force=False)


# def inflecttable(tags=True, tagval=''):
#     # saldomp
#     lemgram = random.choice(['rallarros..nn.1', 'skrutt..nn.1',
#                              'namnskylt..nn.1', 'getabock..nn.1',
#                              'galgbacke..nn.1', 'nisse..nn.1',
#                              'svamp..nn.1', 'mat..nn.1'])
#     ql, lres = call('wordinfo/'+lemgram, {'lexicon': 'saldomp'})
#     table = []
#     for wf in lres['WordForms']:
#         if wf['msd'] not in ['sms', 'ci', 'cm']:
#             if tags and not tagval:
#                 table.append(wf['writtenForm']+'|'+wf['msd'])
#             elif tags:
#                 table.append(wf['writtenForm']+'|'+tagval)
#             else:
#                 table.append(wf['writtenForm'])
#     ','.join(table)
#     params = {'table': ','.join(table), 'pos': 'nn', 'lexicon': 'saldomp'}
#     q, res = call('inflect', params)
#     if tagval == "-":
#         compareinflection(res, lemgram, diff=True)
#     else:
#        compareinflection(res, lemgram)


# def addcandidate():
#     q0, res0 = call('candidatelist')
#     params = {}
#     data = 'test\tnn\nost\tnn'
#     q1, res1 = call('addcandidates', params, data)
#     cands = res1['saved']
#     added = len(data.split('\n'))
#     assert_it(len(cands), added)
#     candpara = cands[0]['CandidateParadigms'][0]
#     candpara['name']
#     candpara['score']
#     candpara['uuid']
#     assert type(candpara['VariableInstances']) is dict, candpara['VariableInstances']
#     cands[0]['WordForms']
#     assert_it(cands[0]['baseform'], data.split('\t')[0])
#     cands[0]['identifier']
#     cands[0]['lexiconName']
#     cands[0]['maxScore']
#     cands[0]['partOfSpeech']
#     time.sleep(1)
#     q2, res2 = call('candidatelist')
#     new_len = len(res2['candidates'])
#     assert_it(new_len, len(res0['candidates'])+added)


# def removecandidate():
#     params = {'lexicon': 'votiska'}
#     q0, res0 = call('candidatelist', params)
#     cand = random.choice(res0['candidates'])
#     _id = cand['identifier']
#     params['identifier'] = _id
#     q1, res1 = call('removecandidate', params)
#     assert_it(res1['deleted']['es_loaded'], 1)
#     time.sleep(1)
#     q2, res2 = call('candidatelist', params)
#     assert_it(len(res2['candidates']), len(res0['candidates'])-1)


# def inflectcandidate():
# # kolla att det blir rätt struktur
#     params = {'lexicon': 'votiska'}
#     q0, res0 = call('candidatelist', params)
#     cand = random.choice(res0['candidates'])
#     _id = cand['identifier']
#     pos = cand['partOfSpeech']
#     base = cand['baseform']
#     params['identifier'] = _id
#     q1, res1 = call('inflectcandidate', params)
#     alt1 = res1["Results"][0]
#     alt1['score']
#     assert alt1['paradigm_entries'] > 0, alt1['paradigm_entries']
#     alt1['paradigm']
#     assert_it(alt1['partOfSpeech'], pos)
#     alt1['new']
#     assert_it(alt1['baseform'], base)
#     alt1['identifier']
#     assert_it(base, base)
#     comparetables(cand['WordForms'], alt1['WordForms'])


# def assert_it(a, b, eq=True):
#     if eq:
#         assert a == b, str(a) +'\n'+str(b)
#     else:
#         assert a != b, str(a) +'\n'+str(b)
#     return True


# def test_it(a, b, eq=True):
#     try:
#         assert_it(a, b, eq)
#         return True
#     except Exception as e:
#         print('Warning, test failed')
#         traceback.print_exc()
#         return False


# def addtable():
#     # saldomp
#     lexparams = {'lexicon': 'saldomp'}
#     paradigm = 'p6_brännässla..nn.1'
#     q0, res0 = call('paradigminfo/'+urllib.parse.quote(paradigm), lexparams)
#     oldcount = res0['_entries']
#     _id = 'labbedissa..nn.7'
#     classes = 'bklass:9'
#     pos = 'nn'
#     base = 'labbedissa'
#     table = 'labbedissa|sg indef nom,labbedissas|sg indef gen,labbedissan|sg def nom,labbedissans|sg def gen,labbedissor|pl indef nom,labbedissors|pl indef gen,labbedissorna|pl def nom,labbedissornas|pl def gen'
#     params = {'table': table, 'pos': pos, 'lexicon': 'saldomp',
#               'identifier': _id, 'classes': classes, 'paradigm': paradigm,
#               'baseform': base}
#     q1, res1 = call('addtable', params)
#     assert_it(res1['paradigm'], paradigm)
#     assert_it(res1['identifier'], _id)
#     assert_it(res1['partOfSpeech'], pos)
#     assert type(res1['var_inst']) is dict, res1['var_inst']
#     classes_dict = dict([c.split(':') for c in classes.split(',')])
#     assert_it(res1['classes'], classes_dict)
#     new_count = res1['members']
#     time.sleep(1)
#     assert_it(oldcount+1, new_count)
#     q2, res2 = call('paradigminfo/'+urllib.parse.quote(paradigm), lexparams)
#     assert_it(res2['_entries'], new_count)
#     for iclass, val in classes_dict.items():
#         assert val in res2['TransformCategory'][iclass], res2['TransformCategory'][iclass]
#     q3, res3 = call('wordinfo/'+_id, lexparams)
#     assert_it(res3['paradigm'], paradigm)
#     params = {'like': _id, 'wordform': base, 'pos': pos, 'lexicon': 'saldomp'}
#     q4, res4 = call('inflectlike', params)
#     compareinflection(res4, _id)


# def addtable2():
#     # saldomp
#     lexparams = {'lexicon': 'saldomp'}
#     paradigm = 'p6_test..nn.4'
#     _id = 'klabbedissa..nn.2'
#     classes = 'bklass:9'
#     pos = 'nn'
#     base = 'klabbedissa'
#     table = 'klabbedisssa|sg indef nom,klabbedissan|sg def nom,klabbedissor|pl indef nom,klabbedissorna|pl def nom'
#     params = {'table': table, 'pos': pos, 'lexicon': 'saldomp',
#               'identifier': _id, 'classes': classes, 'paradigm': paradigm,
#               'baseform': base, 'new': True}
#     q1, res1 = call('addtable', params)
#     assert_it(res1['paradigm'], paradigm)
#     assert_it(res1['identifier'], _id)
#     assert_it(res1['partOfSpeech'], pos)
#     assert type(res1['var_inst']) is dict, res1['var_inst']
#     classes_dict = dict([c.split(':') for c in classes.split(',')])
#     assert_it(res1['classes'], classes_dict)
#     new_count = res1['members']
#     assert_it(1, new_count)
#     time.sleep(1)
#     q2, res2 = call('paradigminfo/'+paradigm, lexparams)
#     assert_it(res2['_entries'], new_count)
#     for iclass, val in classes_dict.items():
#         assert_it(res2['TransformCategory'][iclass], res2['TransformCategory'][iclass])
#     q3, res3 = call('wordinfo/'+_id, lexparams)
#     assert_it(res3['paradigm'], paradigm)
#     params = {'like': _id, 'wordform': base, 'pos': pos, 'lexicon': 'saldomp'}
#     q4, res4 = call('inflectlike', params)
#     compareinflection(res4, _id)

# def updatetable():
# # TODO kolla att det gamla paradigmet inte har kvar bklassen eller ordet
#     # saldomp
#     lexparams = {'lexicon': 'saldomp'}
#     paradigm = 'p6_test..nn.1'
#     _id = 'labbedissa..nn.7'
#     classes = 'bklass:9'
#     pos = 'nn'
#     base = 'labbedissa'
#     table = 'labbedissa|sg indef nom,labbedissan|sg def nom,labbedissor|pl indef nom,labbedissorna|pl def nom'
#     q0, res0 = call('paradigminfo/'+urllib.parse.quote(paradigm), lexparams)
#     q5, res5 = call('wordinfo/'+_id, lexparams)
#     old_para = res5['paradigm']
#     oldcount = res0['_entries']
#     params = {'table': table, 'pos': pos, 'lexicon': 'saldomp',
#               'identifier': _id, 'classes': classes, 'paradigm': paradigm,
#               'baseform': base}
#     q1, res1 = call('updatetable', params)
#     assert_it(res1['paradigm'], paradigm)
#     assert_it(res1['identifier'], _id)
#     assert_it(res1['partOfSpeech'], pos)
#     time.sleep(1)
#     assert type(res1['var_inst']) is dict, res1['var_inst']
#     classes_dict = dict([c.split(':') for c in classes.split(',')])
#     assert_it(res1['classes'], classes_dict)
#     new_count = res1['members']
#     assert_it(oldcount+1, new_count)
#     q2, res2 = call('paradigminfo/'+paradigm, lexparams)
#     assert_it(res2['_entries'], new_count)
#     for iclass, val in classes_dict.items():
#         print('look for', iclass, val)
#         assert val in res2['TransformCategory'][iclass], res2['TransformCategory'][iclass]
#     q3, res3 = call('wordinfo/'+_id, lexparams)
#     q6, res6 = call('paradigminfo/'+urllib.parse.quote(old_para), lexparams)
#     if oldcount == 1:
#         assert_it(res6, {})
#     else:
#         assert_it(res6['MorphologicalPatternID'], paradigm)
#         assert_it(res6['_entries'], oldcount-1)

#     params = {'like': _id, 'wordform': base, 'pos': pos, 'lexicon': 'saldomp'}
#     q4, res4 = call('inflectlike', params)
#     compareinflection(res4, _id)
#     assert_it(res3['paradigm'], old_para, eq=False)

# # TODO
# #
# # lägg till ord till ett paradigm via paradigm+variabler, samma grundform.
# # första förslaget == samma tabell som starttabellen.
# #
# #
# #
# #
# # updatetable
# # flytta till nytt paradigm
# # kolla att det gamla paradigmet inte har kvar bklassen eller ordet
# # kolla att det nya paradigmet har bklassen och ordet
# # gör inflectlike (på samma grundform) och se att det blir rätt
# # kolla att wordinfo finns och är rätt


# def call(url, params={}, data=None, is_json=True):
#     """ Makes a GET call to the given host and path.
#     """
#     try:
#         params = urllib.parse.urlencode(params)
#         if params:
#             url = '%s?%s' % (url, params)
#         q = "%s/%s" % (host, url)
#         user, pw = 'mfl', 'mfl'
#         userpw = '%s:%s' % (user, pw)
#         basic = base64.b64encode(userpw.encode())
#         if data:
#             data = data.encode()
#         req = urllib.request.Request(q, data=data)
#         req.add_header('Authorization', 'Basic %s' % basic.decode())

#         print('send %s' % q)
#         # print('headers %s' % req.headers)
#         response = urllib.request.urlopen(req).read().decode('utf8')
#         # print('reps', response)
#         if is_json:
#             response = json.loads(response)
#         return q, response
#     except:
#         print('calling',host+url)
#         raise


# if __name__ == '__main__':
#     lexicon()
#     lexiconname('votiska')
#     paradigminfo('p1_test')
#     pos()
#     defaulttable(pos="nn")
#     listpara(pos="nn")
#     listbklass(pos="nn")
#     compilebklass(pos="nn")
#     compilewf(pos="nn")
#     compileparadigm(pos="nn")
#     candidatelist()
#     inflectlike()
#     inflectbklass()
#     inflectparadigm()
#     inflect()
#     inflecttable()
#     inflecttable(tags=False)
#     inflecttable(tagval='-')
#     addcandidate()
#     removecandidate()
#     inflectcandidate()
#     addtable()
#     addtable2()
#     updatetable()
#     print('alive')
