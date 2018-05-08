id_field = 'MorphologicalPatternID'
transform_field = 'TransformCategory'
transform_set = 'TransformSet'
varinst_field = 'VariableInstances'
top_varinst = 'Top_VariableInstances'
entries = '_entries'
firstattest = 'first-attest'
pos_field = '_partOfSpeech'
karp_pos = 'pos'


def get_transformcat(hit, iclass):
    return hit.get(transform_field, {}).get(iclass, [])


def get_entries(hit):
    return hit.get(entries, '0')


def word_add_parainfo(lexobj, paraobj):
    lexobj['paradigm_entries'] = get_entries(paraobj)
    for v in paraobj.get(varinst_field, []):
        if v.get(firstattest) == lexobj['identifier']:
            lexobj['variables'] = v
            break


def show_short():
    return [id_field, karp_pos, entries, transform_field, top_varinst, transform_set]


def make_short(obj):
    short_obj = {}
    short_obj[id_field] = obj[id_field]
    short_obj['partOfSpeech'] = obj[pos_field]
    short_obj['entries'] = obj[entries]
    short_obj[transform_field] = obj.get(transform_field, {})
    short_obj[top_varinst] = obj.get(top_varinst, {})
    return obj
