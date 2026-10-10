# Systemperspektiv på trafiksystemet: Luleå och Luleå FA-region

Inventering 2026-10-10. **Planeringsunderlag – inga nya indikatorer har beräknats här.**

## Geografisk avgränsning

Tillväxtverkets FA25 Luleå: Luleå (2580), Boden (2582), Piteå (2581), Älvsbyn (2560), Kalix (2514).
Referens: https://tillvaxtverket.se/download/18.19d85e0e1961e0c5e2e72647/1744712015525/Tillv%C3%A4xtverket%20FA-regioner%202025.pdf

Redovisa Luleå kommun och FA-regionen som två nivåer. Redovisa även gränsöverskridande flöden och relationer till övriga Norrbotten. Använd inte femkommunerssummor som nationellt fastställda pendlingsflöden.

## Prioriterade indikatorer

| Prioritet | Tema | Föreslagen indikator | Källa | Kvalitetskrav |
|---|---|---|---|---|
| 1 | Nätstruktur | Väglängd per funktionell vägklass och väghållare, km och andel | NVDB | Avdubbla länkgeometri; begränsa till körbara nät |
| 1 | Nätstruktur | Vägbredd och antal körfält per vägklass | NVDB | Redovisa andel okänd; sträckvikta |
| 1 | Regional arbetsmarknad | Riktningsberoende pendlingsflöde och kommunernas externa pendlingsberoende | SCB ArRegPend2 | Sysselsatta är personer, inte dagliga bilresor |
| 1 | Regional arbetsmarknad | Flöde per huvudkorridor (hypotes) | SCB + nätanalys | Kommunpar är inte faktisk körd rutt |
| 1 | Kollektivtrafik | Antal planerade avgångar per hållplats/stråk och dagtyp | GTFS Regional | Avgränsa giltiga trafikdagar, datum och båda riktningar |
| 1 | Kollektivtrafik | Restid mellan FA-orter, restidskvot jämfört med bil | GTFS + nätverksberäkning | Avgångstid, byten, gångtid; bilrestid är modell |
| 1 | Sårbarhet | Alternativa vägar och omvägsfaktor när en bro/länk tas bort | NVDB nätgeometri | Körbar och riktad topologi; ingen stängningssimulering före QA |
| 1 | Cykel | Andel sammanhängande cykelnät, största komponent och isolerade delar | NVDB GCM | Kontrollerad sammanfogning i korsningar och passager |
| 2 | Trafikbelastning | ÅDT och tung trafik per funktionell vägklass | NVDB ÅDT | Trafikintensitet är inte totaltrafik; känd begränsad täckning |
| 2 | Godstransport | Bärighetsklass, höjdhinder och tillgängliga godskorridorer | NVDB | Verifiera kodade begränsningar innan routing |
| 2 | Service | Invånare/arbetsplatser inom 15/30/45 min till viktig service | SCB rutnät/arbetsplatser + vägnät | Befolkningsrutnätets sekretess och aktuella nätdata |
| 2 | Vinterrobusthet | Exponering för snö, is, stark vind per vägkorridor | SMHI + NVDB | Klimatmått är proxy, inte direkt uppmätt avstängning |
| 2 | Omställning | Fordonsbestånd och drivmedel per kommun, per invånare | Trafikanalys/SCB | Ägarens kommun är inte nödvändigtvis körd trafik |
| 3 | Säkerhet | Personskador i relation till trafikarbetet, där data stödjer | Trafikanalys/STRADA | Ta hänsyn till täckning och små tal |

## Kända uppgifter i detta repo

- SCB pendlingsmatris för samtliga 14 norrbottniska kommuner med fokusurval för fem FA-kommuner.
- Kommunvis fordonsstatistik, vägtrafikskador, färdtjänst, årsaggregerade NVDB-längder.
- Detaljerade Lastkajen-uttag för fem kommuner: hastighet, väghållare, GCM-passager och trafiksträckor.
- Trafikflödeslagret som hittills använts innehåller registrerad ÅDT på statliga vägar: **saknade kommunala/enskilda trafikuppgifter får inte bli noll**.
- GTFS och hållplats-/linjeanalys finns som utvecklingsspår; tidtabellsbaserade tillgänglighetsmått är inte färdigberäknade.

## Externa källor att verifiera

- NVDB öppna datamängder: https://www.nvdb.se/sv/kund/hamta-aktuella-data/
- Trafiklab GTFS Regional: https://trafiklab.se/api/gtfs-datasets/gtfs-regional
- Trafikanalys: https://www.trafa.se/sidor/oppen-data-api/
- Tillväxtverkets FA25-indelning: se länk ovan.

## Rekommenderad analysordning

1. **Vägnätets struktur**: validera tillgängliga fält, vägklasser, väghållare, bredd och körfält. Publicera km och datatäckning per kommun och FA-region.
2. **Regional pendling och nätets betydelse**: kombinera SCB:s kommunparflöden med nätstrukturen, men märk uppskattade korridorer som modellerade.
3. **Kollektivtrafikens möjligheter**: GTFS-baserad turtäthet, direktförbindelser och restid mellan kommunerna.
4. **Sårbarhet och cykelnät**: endast efter topologisk kvalitetssäkring av vägnäten.
5. **Sammanvägd kommunikation**: separata indikatorer för tillgång, belastning, robusthet och hållbar mobilitet; undvik en subjektiv samlad riskpoäng.

## Särskilda metodregler

- Separera **geografisk täckning**, **datakvalitet** och **faktiskt trafikutfall**.
- Beräkna **unika** väglängder; summera inte överlappande NVDB-objekt.
- Redovisa källa, år, definition, enhet, bortfall och antaganden för varje indikator.
- Nätverksmått kräver validerade topologiska noder och riktningar; närmaste geometri räcker inte.
- Kalla inte registrerade arbetspendlare för dagliga resor eller bilpendlare.
- Ingen ny körning av befintliga stora NVDB-analyser krävs för denna inventering.
