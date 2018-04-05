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
