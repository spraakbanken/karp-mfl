This is a pilot version of the backend for Morfologilabbet,
Språkbanken's morphology lab.

The code is under development.

You can try the current full version of Morfologilabbet [here](https://spraakbanken.gu.se/morfologilabbet/).


# To run it:

* Download the repo `git clone git@github.com:spraakbanken/karp-mfl.git`

### Download paradigmextract
`https://github.com/spraakbanken/paradigmextract`

Test it:
`python3 src/pextract.py < exempel.txt`


### Get a Karp backend
Either use an external Karp, or set up your own:

Follow the instruction [here](https://github.com/spraakbanken/karp-docker),
but use the branch `es6`!
Skip the step "Setup Karps configurations". Instead do this:

- Go to `karp-backend`
- Get `example_mflkarpconfig.zip` (included in the mfl-repo under `testdata`),
    put it in `/karp-backend`, unzip it.
- Copy `config/lexiconconf.json` to `../dummyauth`.

Continue following the instruttions on GitHub.

Finally do:

`docker-compose run --rm karp python offline.py --import_mode paradigms test`

`docker-compose run --rm karp python offline.py --publish_mode paradigms test`



### Get mfl-backend
Go back to your mfl-backend.

Open `config/config.json` and update it:

 * update `paradigmextract` to the full path of your paradigmextract version

If you run the default docker Karp setup, just leave the below fields as they are.

 * karp_backend - set the address to the Karp you want to use
 * DBPASS - login credentials for Karp. This is needed so that the mfl-backend can
   read all paradigms from Karp on start-up.

All calls from mfl-backend to Karp are authenticated by Karp itself, using the current
user's credentials.
But since the mfl-backend stores all paradigms internally, calls like
`inflect` do not include Karp and are hence not authenticated. Therefore, the mfl-backend
makes calls directly to the authentication server. To enable this, you need to set the
following:
 * SECRET_KEY - the authentication server's secret key
 * AUTH_SERVER - the address to the server
 * AUTH_RESOURCES - the address to the server for seeing open resoures


Start your mfl backned on `localhost:5000` by running: `python3 backend.py`

Test `curl localhost:5000`. This should show some documentation.
