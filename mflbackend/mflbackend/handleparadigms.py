import logging
import uuid

from mflbackend import configmanager as C
from mflbackend import errors as errs
from mflbackend import helpers
from mflbackend import lexconfig
from paradigmextract import morphparser as mp
from mflbackend import parseparadigms as pp
from paradigmextract import pextract as pex


def add_paradigm(lexicon, pid, paradigm, paradigms, identifier, pos, classes):
    """
    Add a new paradigm (update language model, save to karp).
    Args:
        lexicon (str): the lexicon name
        pid (string): the paradigms name (human readable id)
        paradigm (obj): the paradigm (Paradigm.py)
        paradigms (list): a list of all internal paradigms
        identifier (str): the tables identifier
        pos (str): the tables word class
        classes (dict): inflectional classes to add '{"bklass": [3,4]}'
    """
    presource = lexconfig.get_paradigmlexicon(lexicon)
    lresource = lexconfig.get_lexiconname(lexicon)
    logging.debug(
        "id %s, para %s.\n classes %s, identifier %s",
        pid,
        paradigm,
        classes,
        identifier,
    )
    # Set name, id etc for the paradigm object
    paradigm.set_id(pid)
    puuid = str(uuid.uuid1())  # generate a uid and set it
    paradigm.set_uuid(puuid)
    paradigm.set_lexicon(presource)
    paradigm.set_pos(pos)
    paradigm._entries = 1
    for key, val in classes.items():
        paradigm.add_class(key, [val])
    logging.debug("uuid %s", puuid)

    # Add to our in memory paradigms and update language model
    if lresource not in paradigms:
        paradigms[lresource] = {}
    if pos not in paradigms[lresource]:
        paradigms[lresource][pos] = {}
    all_paras, numex, lms, alpha = paradigms[lresource].get(pos, ({}, 0, None))
    alpha = mp.extend_alphabet(paradigm, alpha)
    mp.lms_paradigm(
        paradigm,
        lms,
        alpha,
        lexconfig.get_ngramorder(lexicon),
        lexconfig.get_ngramprior(lexicon),
    )
    all_paras[puuid] = paradigm
    paradigms[lresource][pos] = (all_paras, numex + 1, lms, alpha)

    # Save to karp
    helpers.karp_add(paradigm.jsonify(), resource=presource, _id=puuid)


def add_word_to_paradigm(lexicon, paradigm, paradigms, identifier, pos, classes, inst):
    """
    Add a word to extisting paradigm (update language model, save to karp)
    Args:
        lexicon (str): the lexicon name
        paradigm (obj): the paradigm (Paradigm.py)
        paradigms (dict): a dictionary with all paradigms
            '{"lexname": {"nn": [], "vb": []}'
        identifier (str): the tables identifier
        pos (str): the tables word class
        classes (dict): all inflectional classes to add '{"bklass": [3,4]}'
        inst (list): this table's variable instantiations for the paradigm
    """
    presource = lexconfig.get_paradigmlexicon(lexicon)
    lresource = lexconfig.get_lexiconname(lexicon)
    logging.debug("old count %s", paradigm.count)
    # Set variabel instannces, count, resource etc for the paradigm object
    var_inst = [("first-attest", identifier)] + list(enumerate(inst, 1))
    paradigm.add_var_insts(var_inst)
    paradigm.members.append(identifier)
    for key, val in classes.items():
        paradigm.add_class(key, [val])
    paradigm.count += 1
    paradigm.set_lexicon(presource)

    # Update our in memory paradigms and update language model
    all_paras, numex, lms, alpha = paradigms[lresource].get(pos, ({}, 0, None))
    alpha = mp.extend_alphabet(paradigm, alpha)
    paradigms[lresource][pos] = (all_paras, numex, lms, alpha)
    logging.debug("new count %s", paradigm.count)

    # Save to karp
    helpers.karp_update(paradigm.uuid, paradigm.jsonify(), resource=presource)


def remove_word_from_paradigm(lexicon, paradigm, paradigms, identifier, pos):
    """
    Remove a word from a paradigm  (update language model, save to karp)
    Args:
        lexicon (str): the lexicon name
        paradigm (obj): the paradigm (Paradigm.py)
        paradigms (dict): a dictionary with all paradigms
            '{"lexname": {"nn": [], "vb": []}'
        identifier (str): the tables identifier
        pos (str): the tables word class
    """
    logging.debug("old count %s", paradigm.count)
    # remove variable_instances
    for ix, var_inst in enumerate(paradigm.var_insts):
        if dict(var_inst).get("first-attest", "") == identifier:
            paradigm.var_insts.pop(ix)
            break

    # remove from members
    try:
        paradigm.members.remove(identifier)
    except Exception as e:
        logging.exception(e)
        logging.warning(
            "identifier %s cannot be removed, since it was not present in %s",
            identifier,
            paradigm.p_id,
        )

    # remove the words classes from the paradigm if they are not used by other
    # words, by first removing all and then readding the all classes used by
    # other words
    paradigm.empty_classes()
    # get all classes from all other words, add to paradigm:
    q = "extended||and|paradigm|equals|%s||not|%s|equals|%s" % (
        paradigm.p_id,
        lexconfig.get_identifierfield(lexicon),
        identifier,
    )
    for iclass in lexconfig.get_inflectionalclassnames(lexicon):
        res = helpers.karp_query(
            "statlist",
            {"q": q, "size": 1000, "buckets": "%s.bucket" % iclass},
            resource=lexconfig.get_lexiconname(lexicon),
            mode=lexconfig.get_lexiconmode(lexicon),
        )
        paradigm.add_class(iclass, [cl[0] for cl in res.get("stattable", [])])

    # decrease paradigm member count
    paradigm.count -= 1
    logging.debug("new count %s", paradigm.count)
    if paradigm.count > 0:
        # TODO remove from alphabet
        helpers.karp_update(
            paradigm.uuid,
            paradigm.jsonify(),
            resource=lexconfig.get_paradigmlexicon(lexicon),
        )
    else:
        remove_paradigm(lexicon, paradigm, paradigms, pos)


def remove_paradigm(lexicon, paradigm, paradigms, pos):
    """
    Remove a  paradigm  (update language model, delete from karp)
    Args:
        lexicon (str): the lexicon name
        paradigm (obj): the paradigm (Paradigm.py)
        paradigms (dict): a dictionary with all paradigms
            '{"lexname": {"nn": [], "vb": []}'
        pos (str): the tables word class
    """
    helpers.karp_delete(paradigm.uuid, lexconfig.get_paradigmlexicon(lexicon))
    lresource = lexconfig.get_lexiconname(lexicon)
    all_paras, numex, lms, alpha = paradigms[lresource].get(pos, ({}, 0, None))
    del all_paras[paradigm.uuid]
    del lms[paradigm.uuid]
    alpha = mp.paradigms_to_alphabet(all_paras.values())
    # update the internal model, save the recomputed alphabet
    paradigms[lresource][pos] = all_paras, numex - 1, lms, alpha


def inflect_table(
    lexicon, table, paradigms, identifier, pos, ppriorv=None, kbest=10, match_all=False
):
    """
    Find matching paradigms for an inflectiontable, possibly by adding
    word forms to the original table.
    Args:
        lexicon (str): the lexicon name
        table (list): the comma separated word forms, possibly with msds.
                      "katt,katter|pl indef nom,katts"
        paradigms (dict): a dictionary with all paradigms
            '{"lexname": {"nn": [], "vb": []}'
        identifier (str, optional): the word's identifier
        pos (str): the tables word class
        ppriorv (int, optional): setting for pextract.
            Defaults to the lexicon config's value.
        kbest (int, optional): how many suggestion to return. Defaults to 10.
        match_all (bool, optional): must the output strictly match the input?
             Defaults to false. Set to true if the input table is complete and
             no extra forms may be added.
    Returns:
       {"Results": [results]}
         where a result consits of:
           {score: float, paradigm: str, new: bool,
            identifier: str,
            baseform: str,
            variables: dict of variable instansiations,
            WordForms: [{writtenForm: str, msd: str}]
            partOfSpeech: str,
            paradigm_entries: int,
            }
        If the paradigm is new, the key 'pattern' (str) will show a compact
        represention of the paradigm.
        Possibly more, lexicon specific fields are added.
    """
    lexconf = lexconfig.get_lexiconconf(lexicon)
    restrict_baseform = helpers.read_restriction(lexconf)
    paras, numex, lms = helpers.relevant_paradigms(paradigms, lexicon, pos)
    fill_tags = "|" in table
    pex_table = helpers.tableize(table, add_tags=False, fill_tags=fill_tags)
    logging.debug(
        "inflect forms %s msd %s. Restricted %s",
        pex_table[0],
        pex_table[1],
        restrict_baseform,
    )
    res = []
    if paras:
        # if there are known paradigms for the current lexicon and part of
        # speech, try these
        if ppriorv is None:
            ppriorv = lexconfig.get_pprior(lexicon)
        res = mp.test_paradigms(
            pex_table,
            paras,
            numex,
            lms,
            C.config["print_tables"],
            C.config["debug"],
            ppriorv,
            returnempty=False,
            baseform=restrict_baseform,
            match_all=match_all,
        )
    if res:
        ans = {
            "Results": helpers.format_kbest(
                lexicon, res, kbest=kbest, pos=pos, lemgram=identifier
            )
        }
    else:
        # if no results are found (no matching paradigms), make a new paradigm
        # giving exactly the input forms
        logging.debug("invent! %s", len(res))
        pex_table = helpers.tableize(table, add_tags=True, identifier=identifier)
        paradigm = pex.learnparadigms([pex_table])[0]
        logging.debug("learned %s", paradigm)
        ans = {
            "Results": [
                helpers.karp_tableize(
                    lexicon, table, paradigm=paradigm, pos=pos, identifier=identifier
                )
            ]
        }
    return ans


def make_new_table(
    lexicon,
    table,
    paradigm,
    paradigms,
    identifier,
    baseform,
    pos,
    classes,
    ppriorv=None,
    newword=False,
    newpara=False,
):
    """
    Check that the given table and identifiers are ok, that the table matches
    given paradigm and then add the table to the paradigm,
    in karp and internally.
    Args:
        lexicon (str): the lexicon name
        table (str): the comma separated word forms, possibly with msds.
            "katt,katter|pl indef nom,katts"
        paradigm (str): a paradigm name
        paradigms (dict): a dictionary with all paradigms
            '{"lexname": {"nn": [], "vb": []}'
        identifier (str): the word's identifier
        baseform (str): the word's baseform
        pos (str): the tables word class
        classes (str): input classes 'bklass:2,cklass:3'
        ppriorv (int, optional): setting for pextract
        newword (bool, optional): is the word new? Defaults to false.
        newpara (bool, optional): is the paradigm new? Defaults to false.

    Returns:
       a tuple (identifier, wf_table, para, v, classes)
         where
         identifier (str): identifier of  the table
         wf_table (obj): the formatted inflection table
         para (obj): the paradigm object
         v (list): the variable instances
         classes (dict): the formatted classes of the word
    """
    # check that the table's identier is unique
    # if it is new: make sure that it doesn't already exists.
    #    otherwise: construct a new one
    # if it is not new: make sure that it does exists.
    #    otherwise: fail
    lresource = lexconfig.get_lexiconname(lexicon)
    ok = helpers.check_identifier(
        identifier,
        lexconfig.get_identifierfield(lexicon),
        lresource,
        lexconfig.get_lexiconmode(lexicon),
        unique=newword,
        fail=not newword,
    )
    if not ok:
        logging.debug("identifier %s not ok", identifier)
        lexconf = lexconfig.get_lexiconconf(
            lexicon
        )  # TODO remove after refactoring helpers
        word = baseform or helpers.get_baseform(lexconf, identifier)
        identifier = helpers.make_identifier(lexicon, word, pos)
        logging.debug("\t...use %s", identifier)

    # make sure that all required fields are present
    required = [
        ("identifier", identifier),
        ("paradigm", paradigm),
        ("partOfSpeech", pos),
    ]
    for name, field in required:
        if not field:
            raise errs.MflException(
                "Both identifier, partOfSpeech and paradigm must be given!",
                code="unknown_%s" % name,
            )
    # parse input classes
    try:
        logging.debug("make classes: %s", classes)
        if classes:
            classes = dict([c.split(":") for c in classes.split(",")])
        else:
            classes = {}
    except Exception as e1:
        logging.warning("Could not parse classes")
        logging.error(e1)
        raise errs.MflException(
            "Could not parse classes. Format should be 'classname:apa,classname2:bepa'",
            classes,
            code="unparsable_class",
        )

    paras, numex, lms = helpers.relevant_paradigms(paradigms, lexicon, pos)
    if newpara and paradigm in [p.name for p in paras]:
        raise errs.MflException(
            "Paradigm name %s is already used" % (paradigm), code="unique_paradigm"
        )

    # parse the input table into pextract and karp format
    pex_table = helpers.tableize(table, add_tags=False)
    wf_table = helpers.karp_wftableize(
        lexicon,
        paradigm,
        table,
        classes,
        baseform=baseform,
        identifier=identifier,
        pos=pos,
        resource=lresource,
    )
    if newpara:
        # prepare to try all paradigm
        fittingparadigms = paras
        # check that this is a new name
        helpers.check_identifier(
            paradigm,
            pp.id_field,
            lexconfig.get_paradigmlexicon(lexicon),
            lexconfig.get_paradigmmode(lexicon),
        )

    else:
        logging.debug("not new, look for %s", paradigm)
        # prepare to try only the given paradigm
        fittingparadigms = [p for p in paras if p.p_id == paradigm]
        if not fittingparadigms:
            raise errs.MflException(
                "Could not find paradigm %s" % paradigm, code="unknown_paradigm"
            )

    logging.debug("fitting %s", fittingparadigms)
    logging.debug("pex_table %s %s", pex_table[0], pex_table[1])
    if ppriorv is None:
        ppriorv = lexconfig.get_pprior(lexicon)

    ans = mp.test_paradigms(
        pex_table,
        fittingparadigms,
        numex,
        lms,
        C.config["print_tables"],
        C.config["debug"],
        ppriorv,
        returnempty=False,
        match_all=True,
    )

    if newpara and ans:
        logging.warning("Could inflect %s as %s", table, ans[0][1].p_id)
        raise errs.MflException(
            "Table should belong to paradigm %s" % (ans[0][1].p_id),
            code="inflect_problem",
        )

    if not newpara and not ans:
        logging.warning("Could not inflect %s as %s", table, paradigm)
        raise errs.MflException(
            "Table can not belong to paradigm %s" % (paradigm), code="inflect_problem"
        )

    if ans:
        # found a match, add the word to this paradig
        score, para, v = ans[0]
        add_word_to_paradigm(lexicon, para, paradigms, identifier, pos, classes, v)

    else:
        # if no results are found (no matching paradigms), make a new paradigm
        # giving exactly the input forms
        pex_table = helpers.tableize(table, add_tags=False, identifier=identifier)
        para = pex.learnparadigms([pex_table])[0]
        v = [var for ix, var in para.var_insts[0][1:]]
        add_paradigm(lexicon, paradigm, para, paradigms, identifier, pos, classes)

    return identifier, wf_table, para, v, classes
