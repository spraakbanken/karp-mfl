# Den Votiska användarsagan

Detta är ett försök att beskriva arbetsflödet för Votiskan i Morfologilabbet.

## Kandidatlistan
Första listan kommer från en ordbok, andra listan utökar med oanalyserade ordformer
från Korp

## Work-flow

* välj första ordet över huvudtaget
  * behövs inte egentligen, men vi borde tänka på den (hur lägger vi till det första paradigmet)
  
* välj ett ord från kandidatlistan
  * möjlighet att begränsa saker som PoS, MSD och dylikt
  * välj ett paradigm
    1. välj rätt paradigm
      * klicka för att lägga till som ordboksartikkel i Karp lexikonet
      * variabelinstanser uppdateras i Karp paradigmet
      * paradigmprediktionen uppdateras
    2. välj fel paradigm (rätt paradigm saknas)
      * ändra några ordformer i ordformstabellen
      * klicka för att lägga till som ordboksartikkel i Karp lexikonet
      * om pextract verkligen ekstraherar ut ett nytt paradigm
        * läggs det till i Karp
      * variabelinstanser uppdateras i Karp paradigmet
      * paradigmprediktionen uppdateras


## Mer information

Votiskan är väl ett ypperligt exempel på möjligheter att faktiskt länka samman
de få ressurser man faktiskt har tillgång till, genom Karp och Korp.

Dock finns endast det lilla korpuset redan tillgängligt i Korp.


### Tillgängliga ressurser

Ordböcker:
* fem-språkig ordlista (1k ord, skriftspråk)
* dialektordbok (~30k ord, fonetisk skrift)
* ordlista av attesterade ordformer från fältarbete (fonetisk skrift)

Korpus:
* tekster (~10k token, skriftspråk)
* exempeltekster från dialektordboken (~340k token, fonetisk skrift)
  * parallelkorpus: översättningar av exempelteksterna (est, rus)
* transkriberade intervjuer från fältarbete
