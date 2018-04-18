import re

def get_baseform(entry={}, lemgram=''):
    if lemgram:
        return lemgram.split('.')[0]
    elif 'lemgram' in entry:
        return entry['lemgram'].split('.')[0]
    else:
        return entry['WordForms'][0]['writtenForm']


def get_pos(lemgram):
    return re.search('.*\.\.(.*?)\.', lemgram).group(1)

def make_overview(obj):
    bklass = obj.get("bklass", "")
    base = obj.get("baseform", "")
    lemgram = obj.get("lemgram", "")
    pos = obj.get("partOfSpeech", "")
    paradigm = obj.get("paradigm", "")
    out = [base, pos, lemgram, bklass, paradigm]
    fields = ["baseform", "partOfSpeech", "identifier", "bklass", "paradigm"]
    return out, fields


def lmf_wftableize(paradigm, table, classes={}, baseform='', identifier='',
                   pos='', resource=''):
    table = table.split(',')
    obj = {'lexiconName': resource}
    wfs = []
    for l in table:
        if '|' in l:
            form, tag = l.split('|')
        else:
            form = l
            tag = ''
        wfs.append({'writtenForm': form, 'msd': tag})
        if not baseform:
            baseform = form

    obj['WordForms'] = wfs
    obj['lemgram'] = identifier
    obj['partOfSpeech'] = pos
    obj['baseform'] = baseform
    obj['paradigm'] = paradigm
    for key, val in classes.items():
        form[key] = val

    return obj


def yield_identifier(baseform, pos):
    for ix in range(1, 101):
        yield '%s..%s.%s' % (baseform, pos, ix)


def show_wordentry(entry):
    entry['identifier'] = entry.get("lemgram", "")
    if 'lemgram' in entry:
        del entry['lemgram']
    return entry
