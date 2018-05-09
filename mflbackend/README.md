This is a pilot version of the backend for Morfologilabbet.
It is under development and only for playing around.

To run it:

* Download the repo `git clone git@github.com:spraakbanken/karp-mfl.git`

## Install karp
* Install [Docker](https://docs.docker.com/engine/installation/)
* Download this repo `git clone https://github.com/spraakbanken/karp-docker.git`
* `cd karp-docker` (and stay here for the next commands)
* Change branch `git fetch && git branch es6`
* Install karp-backend `git clone https://github.com/spraakbanken/karp-backend.git`
* Change branch `cd karp-backend && git fetch && git branch es6 && cd ..`

* Move mflkarpconf.zip from mflkarp to karp-backend
* `unzip karp-backend/mflkarpconf.zip`
* Run `installmflsaldom.sh`

* Run `docker-compose build`
* Run `docker-compose up -d`
* `cd karp-backend`
* Run `docker-compose run --rm  karp python offline.py --create_metadata`
* Run `docker-compose run --rm karp python offline.py --create_mode karp test`
* Run `docker-compose run --rm karp python offline.py --publish_mode karp test`
* Test: `curl 'localhost:8081/app/'`

  configer, mappingconfig, lexikon


## Install paradigmextract
See https://github.com/spraakbanken/paradigmextract

* `git clone git@github.com:spraakbanken/paradigmextract.git`
* `cd paradigmextract && git fetch && git branch dev`


## Create links from paradigmextract to mfl
 * go to `karp-mfl`
 * `mkdir pextract`
 * `link.sh /path/to/paradigmextract/src`
