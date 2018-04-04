Kandidatordlistan
=================
### Lägga till data
För att lägga till kandidater konstrueras en inputlista per ordklass
där identiferare listas tillsammans eventuella kända former.
Antagande: man kan utläsa grundform ur identifieraren.

```
kandidat.txt:
   katt..nn.1
   hund..nn.1,hundar|pl indef nom
   mås..nn.2,måsars
```

Denna skickas till mfl:
`/addcandidates?pos=nn&lexicon=saldomp -d @kandidat.txt`

Ett nytt index skapas, `saldompcandidates`, och beräknad information sparas där.

### Läsa kandidatlistan
Kandidaterna nås sedan genom `'/candidatelist?pos=nn&lexicon=saldomp'`:
```json
  [
   {"lemgram": "katt..nn.1",
    "partOfSpeech": "nn",
    "baseform": "katt",
    "candidate_paradigms":
      [
       {"paradigm": "p14_oxe..nn.1",
        "uuid": "XYZ",
        "var_inst": {"1": "katt"},
        "score": 1
       },
       {"paradigm": "p15_spann..nn.1",
        "uuid": "XXZ",
        "var_inst": {"1": "k", "2": "tt"},
        "score": 0.9
       }
      ]
   },
   {"lemgram": "hund..nn.1",
    "partOfSpeech": "nn",
    "baseform": "hund",
    "WrittenForms":
      [{"wordForm": "hundar", "msd": "pl indef nom"}],
    "candidate_paradigms":
      [
       {"paradigm": "p14_oxe..nn.1",
        "uuid": "XYZ",
        "var_inst": {"1": "hund"},
        "score": 0.3
       },
       {"paradigm": "p1_lus..nn.1",
        "uuid": "XXZ",
        "var_inst": {"1": "h", "2": "nd"},
        "score": 0.2
       }
      ]
   },
   {"lemgram": "mås..nn.1",
    "partOfSpeech": "nn",
    "baseform": "mås",
    "WrittenForms":
      [{"wordForm": "måsar"}],
    "candidate_paradigms":
      [
       {"paradigm": "p1_oxe..nn.1",
        "uuid": "XYZ",
        "var_inst": {"1": "mås"},
        "score": 0.3
       }
      ]
   }
  ]
```


###  Generera tabeller
Frontenden konstruerar anrop mha kandidatlistan:

`'/inflectclass?classname=paradigm&classval=p14_oxe..nn.1&lexicon=saldomp' -d '{"var_inst": {"1": "katt"}}'`

Man skulle även kunna tänka sig:

`'/inflectcandidate?identifier=katt..nn.1&paradigm_no=1&lexicon=saldomp'`

men den förstnämnda är nog bättre eftersom det även kan tänkas vara användbart även i andra sammanhang.


### Ta bort ett ord

`'/removecandidate?identifier=katt..nn.1&lexicon=saldomp'`

### Spara
Görs som ett vanligt, `addtable`-anrop. Frontenden skickar även ett ta-bort-anrop när ord från kandidatlistan sparas


### Omberäkna
Antagligen behövs också

`'/recomputecandidates?pos=nn&lexicon=saldomp'`
  men det är ännu oklart hur det ska hanteras
