Till varje lexikon kan ett stort antal paradigm vara kopplat.
Dessa finns lagrade i Elasticsearch i det json-format som arbetats fram
tillsammans med Kristian Kankainen. Därifrån kan de exporteras och tanken är
att även möjliggöra export till ett mer standardiserat LMF-format.

För att svara på hur ett ord av en viss ordklass böjs behöver mfl-backenden ge
alla relevanta (dvs. ofta alla) paradigm till sitt orakel (dvs. pardigmextract).
Oraklet genererar det givna ordets tabell för varje paradigm, samt sorterar dem
i sannolikhetsordning.  När paradigmen används i paradigmextract representeras
de i paradigmsextracts egna format, motsvarande klassen Paradigm i filen
src/paradigm.py (i paradigmextracts kod).

För att undvika att hämta alla paradigm från Karp (dvs. ES-klustret) vid varje
anrop till mfl-backend sparas paradigmen som python-objekt i minnet hos
mfl-backenden. Dessa läses in vid start, vilket kan ta flera minuter. För att
snabba på processen kan man först dumpa alla paradigm från ES till en lokal
fil, som sedan läses in vid omstart av mfl-backend.

`python src/backend.py --dump` dumpar paradigmen.
`python src/backend.py --offline` startar backenden och läser paradigmen från filen.


`python src/backend.py` startar backenden och läser paradigmen Karp.
`python src/backend.py --snabb` startar backenden utan att läsa några paradigm alls,
    och kan användas för att testning.


Vilken tmp-fil som används för att dumpa paradigmen ställs in via
`config/config.json`, under `tmpfile`.
Vilka paradigm som ska läsas in sköts via filen `config/lexicons.json`.
De paradigm som tillhör en ordklass som listats under ett lexikon i filen
kommer att läsas in vid start av backenden.

