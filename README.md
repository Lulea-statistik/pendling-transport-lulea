# pendling-transport-lulea

Interaktiv pendlingsmatris för Norrbottens kommuner.

## Källa
SCB Statistikdatabasen: Sysselsatta 15–74 år efter bostadskommun, arbetsställekommun och kön. Årligt register.

Tabell: ArRegPend2 (2020–2024 i aktuell SCB-publicering).

## Omfattning
Matrisen innehåller samtliga 14 kommuner i Norrbottens län. Luleå, Boden, Piteå, Älvsbyn och Kalix markeras som fokuskommuner i webbgränssnittet.

Rader = bostadskommun.
Kolumner = arbetsställekommun.
Värde = antal sysselsatta.

## Uppdatering
GitHub Actions kör `scripts/fetch_commuting.py` veckovis och hämtar tillgängliga år från SCB:s API.

Webbsidan ligger i `docs/`.
