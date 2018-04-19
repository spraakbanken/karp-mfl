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
    out = [base, identifier, pos, bklass, paradigm]
    fields = ["baseform", "identifier", "partOfSpeech", "bklass", "paradigm"]
    return out, fields


def get_baseform(entry={}, lemgram=''):
    # TODO must ask karp about this
    if lemgram:
        return 'default'
    elif len(entry.get('WordForms', [])) > 0:
        return entry['WordForms'][0]['writtenForm']
    return 'default'


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
        show = not tag.startswith('*')
        wfs.append({'writtenForm': form, 'msd': tag, 'show': show})
        if not baseform:
            baseform = form

    obj['WordForms'] = wfs
    obj['identifier'] = identifier
    obj['partOfSpeech'] = pos
    obj['baseform'] = baseform
    obj['paradigm'] = paradigm
    for key, val in classes.items():
        form[key] = val

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
            wf['show'] = not wf.get('tag', '').startswith('*')
    return entry


def show_wordentry(entry):
    " LMF -> MFL format "
    return entry
