# Metodspår: SMHI/SMED som stöd för trafikarbete och drivmedelsanalys

Status: **metodgranskning, inte kalibrerad skattning**. Gäller sidan *Godstransporter & logistik*. Ingen klimat- eller miljöstatistik ska visas i dashboarden.

## Verifierade metodpunkter (SMHI/SMED)

1. Nationella emissionsdatabasen bygger i huvudsak på geografisk fördelning av nationella totaler, där bland annat väg- och trafikdata används. Detta är inte lokalt uppmätt bränsletankning.
2. SMED:s metod- och kvalitetsbeskrivning, submission 2026, anger att SIMAIR-vägnät använder trafikarbete, fordonsflottans sammansättning och bränslefördelning på statliga och större kommunala vägar.
3. Samma metodrapport (s. 47) beskriver fördelning av trafikarbete från SAMS-ytor till mindre vägar med **relativa vikter**: funktionell vägklass 7 = 100, klass 8 = 10, klass 9 = 1. Dessa är **inte direkt uppmätta flöden** och **inte särskilt validerade lastbilsvikter**.
4. I SMHI:s NatMod är ÅDT, tungtrafikandel och hastighet indata till beräknade luftföroreningshalter. Halterna är därför inte en oberoende kontroll av tungtrafikandel när samma indata används.

## Föreslagen beräkningskedja (vår metod, inte SMHI-resultat)

A. **Registreringsbaserat scenario:** För varje kommun och fordonsslag registrerade lastbilar × genomsnittlig körsträcka × dieselandel × liter per kilometer. Detta beräknar ett scenario för fordonsbeståndets bränslebehov, oberoende av tankningsort. Använd inte antalet alla lastbilar som antalet dieselbilar utan en verifierad bränslefördelning.

B. **Territoriellt vägscenario:** För väglänkar med dokumenterad ÅDT tunga fordon kan lastbilskm/år approximeras av ÅDT × väglängd × 365, efter att väglänkar och dubbelgeometrier granskats. Trafikflödet kan även inkludera utländsk/icke-lokalt registrerad trafik. **Fordon utan data får aldrig ÅDT = 0.**

C. **Täckningsluckor:** Redovisa hur mycket väg som har uppmätt tunga ÅDT. Uppskatta omatchade vägar separat och endast med verifierade indikatorer och osäkerhetsintervall. SMED:s vägklassvikter 100/10/1 får inte överföras till lastbilar utan särskild validering. Då vi hittills framför allt har ÅDT *samtliga fordon* för statliga länkar kan inga verkliga lastbilskm beräknas från dessa data ännu.

D. **Drivmedelsmarknad:** SCB EN0109 leveranser diesel till återförsäljare i kommunen 2024–2025. Omfattar mer än lastbilar; kan missa direktleveranser; beräknar inte faktisk tankning av genomfartslastbilar.

E. **Jämför perspektiven utan att likställa dem:** registrerat fordonsbehov, territoriellt trafikarbete och försäljningsledets drivmedelsleveranser. Från skillnaden mellan dem följer ingen säker slutsats om transittrafikens tankning.

## Databehov före ytterligare slutsatser

- Kontrollerad kommunvis fördelning av lätta/tunga lastbilar efter drivmedel och helst ägarkategori; privatägda personbilar ingår inte i lastbilsmodellen.
- Kontrollerad ÅDT *tunga* (alternativt tungtrafikandel plus totalt ÅDT för exakt samma väg och period), med källa, observationsår, väglängd och täckningsandel.
- Fordons- och användningsspecifika bränsleförbrukningar (liter per 100 km), gärna flera scenarier.
- Om andra dieselanvändare ska dras bort från leveransvolymen behövs oberoende uppgifter för personbilar (både privat- och företagsägda), bussar, arbetsmaskiner och andra användningsområden. Gissa inte fram "överskott".
- Kontrollera redovisning av biodiesel/HVO, olika leveranskanaler, bränslelager och årsgränser.

## Källor

- SMHI Nationella emissionsdatabasen: https://www.smhi.se/data/luftkvalitet/nationella-emissionsdatabasen
- SMED, Metod- och kvalitetsbeskrivning, submission 2026 (bland annat sid 47): https://www.smhi.se/download/18.66465e7819dddf637731231/1777988087193/SMED%20Rapport%20nr%203%202026%20Metod-%20och%20kvalitetsbeskrivning%20f%C3%B6r%20geografiskt%20f%C3%B6rdelade%20emissioner%20till%20luft%20%28submission%202026%29.pdf
- SMHI, metodik för NatMod: https://www.smhi.se/data/luftkvalitet/nationell-modellering-av-luftkvalitet/metodik-for-berakning
- SMHI, kvalitetskontroll av trafikindata: https://www.smhi.se/referenslaboratorium/kvalitetssakring/kvalitetskontroll-av-indata-i-luftkvalitetsberakning
- SCB, oljeleveranser till återförsäljare: https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__EN__EN0109__EN0109A/LevBrTypKom/
- Trafikanalys, körsträckor: https://www.trafa.se/vagtrafik/korstrackor/
