# Generellt
- Visa alla lexikon
  '/lexicon'  output/lexicon
- Visa lexikonconfig
  '/lexicon?lexicon=saldomp'
  '/lexicon/saldomp' output/lexiconsaldomp


# Generellt - för ett lexikon
- Ge alla pos output/pos
    '/pos/'
    '/partofspeech'
- Ge alla deklinationer / deklinationslista
   '/compile?s=bklass' # beror på vad som finns
    otuput/compilebklass
- Ge alla paradigm / paradigmlista
    otuput/compilefmparadigms
   '/compile?s=paradigm'
    otuput/compileparadigm
- Ge alla ord / ordlista
   '/compile?s=wf'
    otuput/compilewf
- För ett pardaigm - visa tabell+info
    '/paradigminfo' output/paradigminfo
- För en ordklass - ge defaulttabell **TODO**
- Ge alla ord i kandidatlista **?**
- Autocomplete på ord (som vi vet hur de böjs?)
    anropa karp, med bra conf (mflkarpens)
    '/autocompleteq=sig&mode=mflsaldom' output/autocompletew

(- Autocomplete på paradigm (frontend hämtar alla))
(- Autocomplete på deklination (frontend hämtar alla)
   Börja med: skicka alla)


# Böj
'inflect?table=apa|sg+indef+nom,apan|sg+def+nom&pos=nn'
output/inflecttable
'inflect?table=apa&pos=nn'
output/inflect
'/inflectlike?word=katta&like=flicka..nn.1&pos=nn'
output/inflectlike
'inflectclass?word=apa&bklass=3&pos=nn'
output/inflectclass



## Ger tillbaka:
**TODO**

- böjning
- lemgram
- paradigm
- deklination
- variabler
- poäng


## Input
1. ord+pos+lexikon
2. ord+lemgram+lexikon
3. ord+deklination+lexikon
4. ord+paradigm+lexikon
5. tabell+lexikon

**TODO** lexicon, pos

### 1
inflect?table=apa,apan

### 2
inflectlike?word=oste&like=pojke..nn.1

### 3
 inflectclass?word=apa&class=3

### 5
inflect?table=apa,apan
inflect?table=apa,apan|pl indef nom
inflect?table=apa,apan|pl indef nom,apor


# Annat
 - Generalisera så att det inte är saldospecifikt
