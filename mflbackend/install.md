Hämta pextract
==============
`https://github.com/spraakbanken/paradigmextract`

Använd dev-branchen!
`git branch dev`

Testa att den funkar
`python3 src/pextract.py < exempel.txt`


Hämta karp-b
============
Följ instruktionerna [här](https://github.com/spraakbanken/karp-docker),

men använd es6-branchen!
Hoppa också över steget "Setup Karps configurations" och gör istället:

- Gå till `karp-backend`
- Hämta `mflkarpconf2.zip`, lägg den i `/karp-backend`, unzippa.
- Kopiera `config/lexiconconf.json` till docker-wsauth-mappen (`cp config/lexiconconf.json ../dummyauth`)
- Installera python moduler i karp-backend:

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

Fortsätt följa instruktionerna på github.

Avsluta med:

`docker-compose run --rm karp python offline.py --create_mode paradigms test`

`docker-compose run --rm karp python offline.py --publish_mode paradigms test`




Hämta mfl-backend
=================
`https://github.com/spraakbanken/karp-mfl`

Använd dev-branchen!

Ändra fulimporten i `backend.py` (i början av filen, ~ rad 5) så att pathen till pextract läggs till i `sys.path`

Starta på `localhost:5000`: `python3 backend.py`

`curl localhost:5000` ska vi dokumentation.

