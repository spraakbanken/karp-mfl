
def candidateparadigms(candidate):
    return candidate.get('CandidateParadigms', [])


def inflectionvariables(inflect):
    return inflect.get('VariableInstances', {}).items()


def get_pos(candidate):
    return candidate['partOfSpeech']


def get_baseform(candidate):
    return candidate['baseform']


def get_wordforms(candidate):
    return candidate['WordForms']


def get_uuid(obj):
    return obj['uuid']
