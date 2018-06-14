import json
import logging

import src.configmanager as C
import src.errors as e


def get_lexiconconf(lexicon):
    try:
        return json.load(open(C.config['lexiconpath'][lexicon]))
    except Exception as err:
        logging.exception(err)
        raise e.MflException("Could not open lexicon %s" % lexicon,
                             code="unknown_lexicon")


def get_lexiconname(lexicon):
    return get_lexiconconf(lexicon)['lexiconName']


def get_paradigmlexicon(lexicon):
    return get_lexiconconf(lexicon)['paradigmlexiconName']


def get_ngramorder(lexicon):
    return get_lexiconconf(lexicon)['ngramorder']


def get_ngramprior(lexicon):
    return get_lexiconconf(lexicon)['ngramprior']


def get_pprior(lexicon):
    return get_lexiconconf(lexicon)['pprior']


def get_identifierfield(lexicon):
    return get_lexiconconf(lexicon)['identifier']


def get_inflectionalclassnames(lexicon):
    return get_lexiconconf(lexicon)['inflectionalclass'].keys()


def get_lexiconmode(lexicon):
    return get_lexiconconf(lexicon)['lexiconMode']


def get_paradigmmode(lexicon):
    return get_lexiconconf(lexicon)['paradigmMode']


def get_wsauth_name(lexicon):
    return get_lexiconconf(lexicon)['wsauth_name']


def get_field(lexicon, field, default):
    return get_lexiconconf(lexicon).get(field, default)
