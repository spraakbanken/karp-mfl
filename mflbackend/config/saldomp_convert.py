import re


def get_baseform(entry={}, lemgram=''):
    if lemgram:
        return lemgram.split('.')[0]
    elif 'lemgram' in entry:
        return entry['lemgram'].split('.')[0]
    elif len(entry.get('WordForms', [])) > 0:
        return entry['WordForms'][0]['writtenForm']
    return 'default'


def get_pos(lemgram):
    print('get pos', lemgram)
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
    form = {}
    form['lemgram'] = identifier
    form['partOfSpeech'] = pos
    form['baseform'] = baseform
    form['paradigm'] = paradigm
    for key, val in classes.items():
        form[key] = val
    obj['FormRepresentations'] = [form]

    return obj


def yield_identifier(baseform, pos):
    for ix in range(1, 101):
        yield '%s..%s.%s' % (baseform, pos, ix)


def show_wordentry(entry):
    " LMF -> MFL format "
    result = {}
    form = entry.get("FormRepresentations", [{}])[0]
    result['bklass'] = form.get("bklass", "")
    result['inherent'] = form.get("inherent", "")
    result['baseform'] = form.get("baseform", "")
    result['identifier'] = form.get("lemgram", "")
    result['partOfSpeech'] = form.get("partOfSpeech", "")
    result['paradigm'] = form.get("paradigm", "")
    result['fm_paradigm'] = form.get("fm_paradigm", "")
    result['WordForms'] = entry.get('WordForms', [])
    return result
