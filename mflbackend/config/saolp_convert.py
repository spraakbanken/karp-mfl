
def make_overview(obj):
    bklass = obj.get("bklass", "")
    base = obj.get("baseform", "")
    pos = obj.get("partOfSpeech", "")
    paradigm = obj.get("paradigm", "")
    identifier = obj.get("identifier", "")
    out = [base, identifier, pos, bklass, paradigm]
    fields = ["baseform", "identifier", "partOfSpeech", "bklass", "paradigm"]
    return out, fields


