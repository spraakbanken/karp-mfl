id_field = 'MorphologicalPatternID'
transform_field = 'TransformCategory'
varinst_field = 'VariableInstances'
entries = '_entries'
firstattest = 'first-attest'
pos_field = '_partOfSpeech'


def get_transformcat(hit, iclass):
    return hit[transform_field].get(iclass, [])


def get_entries(hit):
    return hit.get(entries, '0')


def word_add_parainfo(lexobj, paraobj):
    lexobj['paradigm_entries'] = get_entries(paraobj)
    for v in paraobj.get(varinst_field, []):
        if v.get(firstattest) == lexobj['identifier']:
            lexobj['variables'] = v
            break


def make_short(obj):
    short_obj = {}
    short_obj['MorphologicalPatternID'] = obj[id_field]
    short_obj['partOfSpeech'] = obj[pos_field]
    short_obj['entries'] = obj[entries]
    short_obj['TransformCategory'] = obj.get(transform_field, {})
    return
