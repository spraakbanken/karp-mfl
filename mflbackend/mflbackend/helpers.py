import base64
import json
import logging
import re
import urllib.parse
import urllib.request
import uuid

from hashlib import md5
from flask import request

from mflbackend import configmanager as C
from mflbackend import errors as errs
from mflbackend import lexconfig


# Parsing results form ES #####################################################
def es_total(res):
    return res["hits"]["total"]


def es_first_source(res):
    return res["hits"]["hits"][0]["_source"]


def es_first_id(res):
    return res["hits"]["hits"][0]["_id"]


def es_all_source(res):
    return [hit["_source"] for hit in res["hits"]["hits"]]


def es_get_hits(res):
    return res["hits"]["hits"]


def es_get_id(hit):
    return hit["_id"]


def es_get_source(hit):
    return hit["_source"]


def es_get_bucket(bucket, res):
    return res["aggregations"]["q_statistics"][bucket]["buckets"]


def es_get_bucket_count(bucket, res):
    return res["aggregations"]["q_statistics"][bucket]["value"]


def es_get_classbucket(iclass, res, lexconf):
    return es_get_bucket(lexconf["inflectionalclass"][iclass], res)


def es_get_classcount(iclass, res, lexconf):
    return es_get_bucket_count(lexconf["inflectionalclass"][iclass], res)


# Basic communication with karp ##############################################
def karp_add(data, resource="saldomp", _id=None):
    data = {"doc": data, "message": "Mfl generated paradigm"}
    if _id:
        return karp_request(
            "readd/%s/%s" % (resource, _id), data=json.dumps(data).encode("utf8")
        )
    else:
        return karp_request("add/%s" % resource, data=json.dumps(data).encode("utf8"))


def karp_bulkadd(data, resource="saldomp"):
    data = {"doc": data, "message": "Mfl candidate list"}
    return karp_request("addbulk/%s" % resource, data=json.dumps(data).encode("utf8"))


def karp_delete(_id, resource="saldomp"):
    return karp_request("delete/%s/%s" % (resource, _id))


def karp_update(uuid, data, resource="saldomp"):
    data = {"doc": data, "message": "Mfl generated paradigm"}
    return karp_request(
        "mkupdate/%s/%s" % (resource, uuid), data=json.dumps(data).encode("utf8")
    )


def karp_query(action, query, mode="external", resource="saldomp", user=""):
    if "mode" not in query:
        query["mode"] = mode
    if "resource" not in query and "lexiconName" not in query:
        query["resource"] = resource
    if "size" not in query:
        query["size"] = 1000
    logging.debug("query %s %s", query, type(query))
    logging.debug("query %s %s", query, type(query))
    params = urllib.parse.urlencode(query)
    logging.debug("ask karp %s %s", action, params)
    return karp_request("%s?%s" % (action, params), user=user)


def karp_request(action, data=None, user=""):
    q = "%s/%s" % (C.config["KARP_BACKEND"], action)

    if user:
        userpw = user
    else:
        try:
            auth = request.authorization
            user, pw = auth.username, auth.password
        except:
            user, pw = "mfl", "mfl"
        userpw = "%s:%s" % (user, pw)
    basic = base64.b64encode(userpw.encode())
    print(f"urllib.request.Request(q={q}, data={data})")
    req = urllib.request.Request(q, data=data)
    req.add_header("Authorization", "Basic %s" % basic.decode())

    logging.debug("send %s", q)
    print(f"req = {str(req)}")
    response = urllib.request.urlopen(req).read().decode("utf8")
    return json.loads(response)


def search_q(fullquery, searchfield, q, lexicon, isfilter=False):
    """
    Construct a Karp query string.
    Args:
        fullquery (list): previously composed queries
        searchfield (str): a karp search field
        q (str): a term to search for
        lexicon (str): the lexicon to search
        isfilter (bool, optional): search for q as a substring if true.
            Defaults to false.
    Returns:
       fullquery (list): the input fullquery list, with the new query appended.
    """
    if q:
        operator = "equals" if not isfilter else "regexp"
        if isfilter:
            q = ".*" + q + ".*"
        logging.debug("q is %s", q)
        fullquery.append("and|%s.search|%s|%s" % (searchfield, operator, q))
    if fullquery:
        fullquery = "extended||" + "||".join(fullquery)
    else:
        fullquery = "extended||and|lexiconName|equals|%s" % lexicon
    return fullquery


def multi_query(lexicon, fullquery, fields, query, isfilter):
    """
    Construct a Karp query string, searching for different terms in different
    fields.
    Args:
        lexicon (str): the lexicon name
        fullquery (list): previously composed queries
        fields (list): a list of fields to search
        query (list): a list of terms to search for
        isfilter (bool, optional): search for q as a substring if true.
            Defaults to false.
    Returns:
       fullquery (list): the input fullquery list, with the new query appended.
    """
    operator = "equals" if not isfilter else "regexp"
    for ix, field in enumerate(fields):
        q = query[ix]
        if isfilter:
            q = ".*" + q + ".*"
        fullquery.append(
            "and|%s.search|%s|%s"
            % (lexconfig.get_field(lexicon, field, field), operator, q)
        )
    return fullquery


def authenticate(lexicon, action="read"):
    """
    Authentication check. Used when but data is sent to the user, but Karp is
    not involved (Karp takes care of this otherwise).
    Args:
        lexicon (str): the lexicon name
        action (str, optional): defines which permission to verify.
            Possible values: read, write.
    Raises:
        MflException: if the user is not granted the action in the lexicon
    """
    if action == "checkopen":
        auth = None
    else:
        auth = request.authorization
    postdata = {"include_open_resources": "true"}
    if auth is not None:
        user, pw = auth.username, auth.password
        server = C.config["AUTH_SERVER"]
        mdcode = user + pw + C.config["SECRET_KEY"]
        postdata["checksum"] = md5(mdcode.encode("utf8")).hexdigest()
        postdata["username"] = user
        postdata["password"] = pw
    else:
        server = C.config["AUTH_RESOURCES"]

    data = urllib.parse.urlencode(postdata).encode()
    response = urllib.request.urlopen(server, data).read().decode("utf8")
    auth_response = json.loads(response)
    lexitems = auth_response.get("permitted_resources", {})
    if action == "checkopen":
        return [lex for lex, per in lexitems.get("lexica", {}).items() if per["read"]]
    else:
        permissions = lexitems.get("lexica", {}).get(
            lexconfig.get_wsauth_name(lexicon), {}
        )
        if not permissions.get(action, False):
            raise errs.MflException(
                "Action %s not allowed in lexicon %s"
                % (action, lexconfig.get_lexiconname(lexicon)),
                code="authentication",
                status_code=401,
            )
        return permissions


# Formatting #################################################################
def format_entry(lexicon, entry):
    func = extra_src(lexicon, "show_wordentry", lambda x: x)
    return func(entry)


def format_kbest(lexicon, ans, kbest=0, pos="", lemgram="", debug=False):
    " Format the kbest tables "
    out = []
    for aindex, (score, p, v) in enumerate(ans):
        if kbest and aindex >= kbest:
            break
        res = make_table(lexicon, p, v, score, pos, lemgram=lemgram)
        if res is not None:
            out.append(res)
    return out


def make_table(lexicon, paradigm, v, score, pos, lemgram=""):
    """
    Formats an inflection table.
    Returns:
       A dictionary or None if somethings goes wrong
    """
    try:
        infl = {
            "paradigm": paradigm.name,
            "WordForms": [],
            "variables": dict(zip(range(1, len(v) + 1), v)),
            "score": score,
            "paradigm_entries": paradigm.count,
            "new": False,
            "partOfSpeech": pos,
            "identifier": lemgram,
        }
        logging.debug("%s:, %s", paradigm.name, v)
        table = paradigm(*v)  # Instantiate table with vars from analysis
        logging.debug("table %s", table)
        for form, msd in table:
            for tag in msd:
                infl["WordForms"].append({"writtenForm": form, "msd": tag[1]})
            if not msd:
                infl["WordForms"].append({"writtenForm": form})

        infl["baseform"] = get_baseform_infl(lexicon, infl)
        # logging.debug('could use paradigm %s' % paradigm)
        return show_inflected(lexicon, infl)
    except Exception as e:
        # fails if the inflection does not work (instantiation fails)
        logging.debug("could not use paradigm %s", paradigm.name)
        logging.exception(e)
        return None


def show_inflected(lexicon, entry):
    " Extra, lexicon specific formating "
    func = extra_src(lexicon, "show_inflected", lambda x: x)
    return func(entry)


def karp_wftableize(
    lexicon,
    paradigm,
    table,
    classes=None,
    baseform="",
    identifier="",
    pos="",
    resource="",
):
    """ Format a word table into a Karp friendly json object """

    def default(paradigm, table, classes, baseform, identifier, pos, resource):
        # TODO implement something more generic?
        table = table.split(",")
        obj = {"lexiconName": resource}
        wfs = []
        for l in table:
            if "|" in l:
                form, tag = l.split("|")
            else:
                form = l
                tag = ""
            wfs.append({"writtenForm": form, "msd": tag})
            if not baseform:
                baseform = form

        obj["WordForms"] = wfs
        form = {}
        form["identifier"] = identifier
        form["partOfSpeech"] = pos
        form["baseform"] = baseform
        form["paradigm"] = paradigm
        for key, val in classes.items():
            form[key] = val
        obj["FormRepresentations"] = [form]
        obj["used_default"] = "true"
        return obj

    func = extra_src(lexicon, "karp_wftableize", default)

    if not classes:
        classes = {}
    return func(paradigm, table, classes, baseform, identifier, pos, resource)


def karp_tableize(lexicon, table, paradigm=None, pos="", identifier="", score=0):
    " Format a generated inflection table into a Karp friendly json object "
    table = table.split(",")
    obj = {"score": score, "paradigm": "", "new": True}
    if paradigm is not None:
        obj["variables"] = dict([var for var in paradigm.var_insts[0][1:]])
        obj["paradigm"] = paradigm.name
        obj["pattern"] = paradigm.jsonify()
    wfs = []
    for l in table:
        if "|" in l:
            form, tag = l.split("|")
        else:
            form = l
            tag = "X"
        wfs.append({"writtenForm": form, "msd": tag})

    obj["WordForms"] = wfs
    func = extra_src(lexicon, "get_baseform", "")
    obj["baseform"] = func(obj)
    obj["partOfSpeech"] = pos
    obj["paradigm_entries"] = 0
    obj["identifier"] = identifier
    return show_inflected(lexicon, obj)


def tableize(table, add_tags=True, fill_tags=True, identifier=""):
    """ Parse an input table, from string format to the pextract format.
    Args:
        table (str): the comma separated word forms, possibly with msds.
            "katt,katter|pl indef nom,katts"
        add_tags (bool, optional): add the dummy tag 'tag' for all forms
            without msd. Defaults to true. Overrides fill_tags.
        fill_tags (bool, optional): add empty tags for all forms without msd.
        identifier. Defaults to true.
    Returns:
        a list of forms and a list of tags:
            forms: ["katt", "katts"]
            tags : [[("msd", "sg indef nom")], [("msd", "sg indef gen")]]
            More complex types of tags:
            [[("num", "sg"), ("def", "indef"), ("case", "nom")],
             [("num", "sg"), ("def", "indef"), ("case", "gen")]]
    """
    thistable, thesetags = [], []
    table = table.split(",")

    if identifier:
        thistable.append(identifier)
        thesetags.append([("msd", "identifier")])
    for l in table:
        if "|" in l:
            form, tag = l.split("|")
        else:
            form = l
            tag = "tag" if add_tags else ""
        thistable.append(form)
        if add_tags or tag:
            thesetags.append([("msd", tag)])
        elif fill_tags:
            thesetags.append([])
    return (thistable, thesetags)


def tableize_obj(obj, add_tags=True, fill_tags=True, identifier=""):
    """ Parse an input table, from karp object into the pextract format.
    Args:
        obj (obj): a Karp style object (eg a candidate)
        add_tags (bool, optional): add the dummy tag 'tag' for all forms
            without msd. Defaults to true. Overrides fill_tags.
        fill_tags (bool, optional): add empty tags for all forms without msd.
        identifier. Defaults to true.
    Returns:
        a list of forms and a list of tags:
            forms: ["katt", "katts"]
            tags : [[("msd", "sg indef nom")], [("msd", "sg indef gen")]]
            More complex types of tags:
            [[("num", "sg"), ("def", "indef"), ("case", "nom")],
             [("num", "sg"), ("def", "indef"), ("case", "gen")]]
    """
    thistable, thesetags = [obj["baseform"]], [""]
    if identifier:
        thistable.append(identifier)
        thesetags.append([("msd", "identifier")])
    for wf in obj["WordForms"]:
        thistable.append(wf["writtenForm"])
        tag = wf.get("msd", "tag" if add_tags else "")
        if add_tags or tag:
            thesetags.append([("msd", tag)])
        elif fill_tags:
            # TODO changed from '' to []. Check if it works
            thesetags.append([])
        tag = "tag" if add_tags else ""
    return (thistable, thesetags)


def make_candidate(lexicon, identifier, table, paradigms, pos, kbest=5):
    """ Construct a candidate Karp object
    Args:
        lexicon (str): the name of the candidate resource
        identifier (str): the candidate identifier
        table (list): a list of word forms, possibly with msds.
            "katt,katter|pl indef nom,katts"
        paradigms (list): a list of matching paradigms
            [(score (float), paradigm (obj), variables (list))]
        pos (str): the tables word class
        kbest (int, optional): how many paradigms to save. Defaults to 5.
    Returns:
        an Karp candidate object

    """
    obj = {"identifier": identifier, "partOfSpeech": pos, "baseform": table[0]}
    obj["lexiconName"] = lexicon
    obj["CandidateParadigms"] = []
    obj["WordForms"] = []
    # attested forms
    wftable = table[1:] if len(table) > 1 else table
    for form in wftable:
        if "|" in form:
            form, tag = form.split("|")
            wf = {"writtenForm": form, "msd": tag}
        else:
            wf = {"writtenForm": form}
        obj["WordForms"].append(wf)
    cands = []
    for score, p, v in paradigms:
        cand = {}
        cand["name"] = p.name
        cand["uuid"] = p.uuid
        cand["VariableInstances"] = dict(enumerate(v, 1))
        cand["score"] = score
        cands.append((score, cand))

    cands.sort(reverse=True, key=lambda x: x[0])
    if cands:
        obj["maxScore"] = cands[0][0]

    obj["CandidateParadigms"] = [c for score, c in cands[:kbest]]
    return obj


def make_identifier(lexicon, baseform, pos, field="", default=False):
    """ Suggest an identifier for an entry
    Args:
        lexicon (str): the name of the lexicon in which the identifier
            should be used
        baseform (str): the entry's baseform
        pos (str): the entry's word class
        field (str, optional): the identier's field name.
            Defaults to the lexicon config's value.
        default (bool, optional): always create a standard uuid, even if the
            lexicon has got a function for creating identifiers.
            Defaults to false.
    """
    lexconf = lexconfig.get_lexiconconf(lexicon)
    func = extra_src(lexicon, "yield_identifier", None)

    if default or func is None:
        return str(uuid.uuid1())

    field = field or lexconf["identifier"]
    mode = lexconf["lexiconMode"]

    for _id in func(baseform, pos):
        if check_identifier(_id, field, lexicon, mode, fail=False):
            return _id

    raise errs.MflException(
        "Could not come up with an identifier for %s, %s in lexicon %s"
        % (baseform, pos, lexicon),
        code="id_generation",
    )


# Getting and reading configs, request parameters and defaults ################
def read_pos(lexconf):
    " Return a list of pos tags, either from the parameters or the config "
    pos = request.args.get("pos", "")
    partofspeech = request.args.get("partOfSpeech", lexconf["defaultpos"])
    pos = pos or partofspeech
    return pos.split(",")


def read_one_pos(lexconf):
    " Return one pos tag, either from the parameters or the config "
    return read_pos(lexconf)[0]


def read_restriction(lexconf):
    """ Check whether restrict_to_baseform is true,
        either from the parameters or the config """
    restrict = request.args.get("restrict_to_baseform")
    if restrict is None:
        return lexconf["restrict_to_baseform"]
    return restrict in ["True", "true", True]


def get_defaulttable():
    """ Return an empty inflection table with msds """
    lexicon = request.args.get("lexicon", C.config["default"])
    lexconf = lexconfig.get_lexiconconf(lexicon)
    pos = read_one_pos(lexconf)
    func = extra_src(lexicon, "defaulttable", lambda x: [])
    stattable = func(pos)
    if not stattable:
        q = "extended||and|%s.search|equals|%s" % (lexconf["pos"], pos)
        res = karp_query(
            "statlist",
            {
                "q": q,
                "mode": lexconf["lexiconMode"],
                "resource": lexconf["lexiconName"],
                "buckets": lexconf["msd"] + ".bucket",
            },
        )
        stattable = (tag[0] for tag in res["stat_table"])
    wfs = []
    for tag in stattable:
        wfs.append({"writtenForm": "", "msd": tag})

    if not wfs:
        wfs.append({"writtenForm": "", "msd": ""})

    return {"WordForms": wfs, "partOfSpeech": pos}


def identifier2pos(lexicon, lemgram):
    " Try to find the pos tag by looking at the identfier "
    func = extra_src(lexicon, "get_pos", lambda x: re.search(".*\.\.(.*?)\..*", x))
    return func(lemgram)


def get_baseform_infl(lexicon, infl):
    " Try to find the baseform by looking at the inflection table "
    func = extra_src(
        lexicon, "get_baseform", lambda entry=infl: entry["WordForms"][0]["writtenForm"]
    )
    return func(entry=infl)


def get_baseform(lexconf, lemgram):
    " Try to find the baseform by looking at the identifier "
    func = extra_src(lexconf, "get_baseform", lambda x: x.split("\.")[0])
    return func(lemgram=lemgram)


def firstform(table):
    " Return the first form of a table, formatted as a comma separated string"
    return table.split(",")[0].split("|")[0]


def extra_src(lexicon, funcname, default):
    " Return a lexicon specific function if there is any "
    import importlib

    # If importing fails, try with a different path.
    logging.debug("look for %s", funcname)
    lexconf = lexconfig.get_lexiconconf(lexicon)
    try:
        logging.debug("file: %s", lexconf["src"])
        classmodule = importlib.import_module(lexconf["src"])
        logging.debug("\n\ngo look in %s\n\n", classmodule)
        func = getattr(classmodule, funcname)
        return func
    except:
        return default


def relevant_paradigms(paradigmdict, lexicon, pos, possible_p=[]):
    """ Returns a subset of the paradigms.
    Args:
        paradigmdict (dict): a dictionary with all paradigms
            '{"lexname": {"nn": [], "vb": []}'
        lexicon (str): the lexicon name
        pos (str): the tables word class
        possible_p (list, optional): a list of all acceptable paradigm id:s.
           If left empty, all paradigms are considered ok.
    Returns:
        (a list of paradigm object (obj),
         number of examples (float),
         alphabet/language model (set))
    Raises:
        MflException if the lexicon name could not be found
    """
    try:
        all_paras, numex, lms, alpha = paradigmdict[lexicon].get(pos, ({}, 0, None, ""))
        if possible_p:
            # print('search for %s (%s)' % (possible_p[0], all_paras))
            all_paras = [all_paras[p] for p in possible_p if p in all_paras]
        else:
            all_paras = list(all_paras.values())

        return all_paras, numex, lms
    except:
        raise errs.MflException(
            "Could not read lexicon %s" % lexicon, code="unknown_lexicon"
        )


# Complex queries involving Karp ##############################################
def compile_list(
    query, searchfield, querystr, lexicon, show, size, start, mode, isfilter=False
):
    " Ask karp about entries matching the given query "
    query = search_q(query, searchfield, querystr, lexicon, isfilter=isfilter)
    res = karp_query(
        "minientry",
        {
            "q": query,
            "show": show,
            "size": size,
            "start": start,
            "mode": mode,
            "resource": lexicon,
        },
    )
    ans = es_all_source(res)
    return {"ans": ans, "total": es_total(res)}


def get_current_paradigm(_id, pos, lexconf, paradigmdict):
    """ Return the paradigm object refererred to by a word entry
    Args:
        _id (str): the identifier of the word entry
         pos (str): the tables word class
        lexconf (dict): the lexicon configurations
        paradigmdict (dict): a dictionary with all paradigms
            '{"lexname": {"nn": [], "vb": []}'
    Returns:
       a paradigm object
    """

    field = lexconf["identifier"]
    q = {
        "size": 1,
        "q": "extended||and|%s.search|equals|%s" % ("first-attest", _id),
        "show": "_id",
    }
    res = karp_query(
        "query",
        q,
        mode=lexconf["paradigmMode"],
        resource=lexconf["paradigmlexiconName"],
    )
    if not es_total(res) > 0:
        raise errs.MflException(
            "Identifier %s not found" % _id, code="unknown_%s" % field
        )

    p_id = es_first_source(res)["_uuid"]
    logging.debug("p_id is %s", p_id)
    paras, numex, lms = relevant_paradigms(
        paradigmdict, lexconf["lexiconName"], pos, possible_p=[p_id]
    )
    if not paras:
        raise errs.MflException("Paradigm %s not found" % p_id, code="unknown_paradigm")
    return paras[0]


def get_es_identifier(_id, field, resource, mode):
    " Get the ES _id of an entry "
    q = {"size": 1, "q": "extended||and|%s.search|equals|%s" % (field, _id)}
    res = karp_query("query", q, mode=mode, resource=resource)
    if not es_total(res) > 0:
        raise errs.MflException(
            "Identifier %s not found" % _id, code="unknown_%s" % field
        )
    return es_first_id(res)


def check_identifier(_id, field, resource, mode, unique=True, fail=True):
    " Check whether an identifier has been used before "
    q = {"size": 0, "q": "extended||and|%s.search|equals|%s" % (field, _id)}
    res = karp_query("query", q, mode=mode, resource=resource)
    used = es_total(res) > 0
    ok = (used and not unique) or (not used and unique)
    if not ok and fail:
        text = "already in use" if unique else "not found"
        raise errs.MflException(
            "Identifier %s %s" % (_id, text), code="unique_%s" % field
        )
    return ok


def give_info(identifier, id_field, mode, resource, show=[]):
    " Give information for the word/paradigm infobox "
    q = "extended||and|%s.search|equals|%s" % (id_field, identifier)
    body = {"q": q}
    action = "query"
    if show:
        body["show"] = ",".join(show)
        action = "minientry"
    print(f"karp_query(action={action}, body={body}, mode={mode}, resource={resource}")
    res = karp_query(action, body, mode=mode, resource=resource)
    print(f"res = {res}")
    if es_total(res) > 0:
        return es_first_source(res)
    return {}
