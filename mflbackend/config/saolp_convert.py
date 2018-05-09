import sys
import configmanager as C
sys.path.append(C.config['paradigmextract'])
import helpers


def make_overview(obj):
    bklass = obj.get("bklass", "")
    base = obj.get("baseform", "")
    pos = obj.get("partOfSpeech", "")
    paradigm = obj.get("paradigm", "")
    identifier = obj.get("identifier", "")
    out = [identifier, base, pos, bklass, paradigm]
    fields = ["identifier", "baseform", "partOfSpeech", "bklass", "paradigm"]
    return out, fields


def get_baseform(entry={}, lemgram=''):
    # TODO must ask karp about this
    if lemgram:
        return 'default'
    elif len(entry.get('WordForms', [])) > 0:
        return entry['WordForms'][0]['writtenForm']
    return 'default'


def get_paradigm(entry):
    return entry.get("paradigm", "")

# def get_pos(lemgram):
    # TODO must ask karp about this
    # pass


def lmf_wftableize(paradigm, table, classes={}, baseform='', identifier='',
                   pos='', resource=''):
    " Url table format -> LMF format"
    table = table.split(',')
    obj = {'lexiconName': resource}
    wfs = []
    for l in table:
        if '|' in l:
            form, tag = l.split('|')
        else:
            form = l
            tag = ''
        # TODO will change in the future, make better structure for msd
        show = not tag.startswith('*')
        # tag = tag[1:] if tag.startswith('*') else tag
        wfs.append({'writtenForm': form, 'msd': tag, 'show': show})
        if not baseform:
            baseform = form

    obj['WordForms'] = wfs
    obj['identifier'] = identifier
    obj['partOfSpeech'] = pos
    obj['baseform'] = baseform
    obj['paradigm'] = paradigm
    for key, val in classes.items():
        obj[key] = val

    return obj


def yield_identifier(baseform, pos):
    ans = helpers.karp_request('suggestid/saolp').get('suggested_id', 99999999)
    for ix in range(100):
        yield str(ans+ix)


def show_inflected(entry):
    " MFL format -> Lexicon MFL format "
    print('hello', entry)
    for wf in entry.get('WordForms', []):
        if 'show' not in wf:
            wf['show'] = not wf.get('msd', '').startswith('*')
        # TODO will change in the future, make better structure for msd
        # if wf.get('msd', '').startswith('*'):
        #     wf['msd'] = wf['msd'][1:]
    return entry


def show_wordentry(entry):
    " LMF -> MFL format "
    return entry


def defaulttable(pos):
    lookup = {
        'subst.': ["NCUSNI", "NCUSGI", "NCUSND", "NCUSGD", "NCUPNI", "NCUPGI", "NCUPND", "NCUPGD"]
    }
    return lookup.get(pos, [])

