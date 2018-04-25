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


def get_paradigm(entry):
    return entry.get("paradigm", "")


def make_overview(obj):
    bklass = obj.get("bklass", "")
    base = obj.get("baseform", "")
    lemgram = obj.get("lemgram", "")
    pos = obj.get("partOfSpeech", "")
    paradigm = obj.get("paradigm", "")
    out = [lemgram, base, pos, bklass, paradigm]
    fields = ["identifier", "baseform", "partOfSpeech", "bklass", "paradigm"]
    return out, fields


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
        wfs.append({'writtenForm': form, 'msd': tag})
        if not baseform:
            baseform = form

    obj['WordForms'] = wfs
    obj['lemgram'] = identifier
    obj['partOfSpeech'] = pos
    obj['baseform'] = baseform
    obj['paradigm'] = paradigm
    for key, val in classes.items():
        obj[key] = val

    return obj


def yield_identifier(baseform, pos):
    for ix in range(1, 101):
        yield '%s..%s.%s' % (baseform, pos, ix)


def show_wordentry(entry):
    " LMF -> MFL format "
    entry['identifier'] = entry.get("lemgram", "")
    if 'lemgram' in entry:
        del entry['lemgram']
    return entry
