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
    form = obj["FormRepresentations"][0]
    print('form', form)
    bklass = form.get("bklass", "")
    inherent = form.get("inherent", "")
    base = form.get("baseform", "")
    lemgram = form.get("lemgram", "")
    pos = form.get("partOfSpeech", "")
    paradigm = form.get("paradigm", "")
    fm_paradigm = form.get("fm_paradigm", "")
    out = [base, pos, inherent, lemgram, bklass, fm_paradigm, paradigm]
    fields = ["baseform", "partOfSpeech", "inherent", "identifier", "bklass", "fm_paradigm", "paradigm"]
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
    form = {}
    form['lemgram'] = identifier
    form['partOfSpeech'] = pos
    form['baseform'] = baseform
    form['paradigm'] = paradigm
    for key, val in classes.items():
        form[key] = val
    obj['FormRepresentations'] = [form]

    return obj
