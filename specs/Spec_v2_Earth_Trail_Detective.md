# Spec v2 (Vorschlag): Earth Trail Detective

NASA Space Apps Challenge 2026 · Challenge „Be An Earth System Trend Detective!“ · Team aus zwei Personen · Vorschlag vom 14.11.2026, ersetzt nach Freigabe *Spec_Natural_Experiment_Detective.pdf* (v1)

> Name der App (englisch): **Earth Trail Detective**.

---

## 0. Was sich gegenüber v1 ändert

| Thema | v1 | v2 (dieser Vorschlag) | Grund |
|---|---|---|---|
| Hauptfall | IMO 2020: Schiffsschwefel und Wolken (Ereignisanalyse) | **Schadstoffspur**: Abgase und Partikel auf dem Weg Luft → Wolke → Niederschlag/Schnee → Gletscher → Boden → Fluss/Meer, zwei Regionen mit gegenläufigem Trend | Die Challenge betont gegenläufige Trends desselben Prozesses, lange Reihen und Hydrologie; „komplexere Analysen sind außerhalb des Scopes“ |
| IMO 2020 | Must, Hauptfall | **Should**, kurzer Demo-Fall B „Ships and clouds“ als Zwei-Regionen-Trendvergleich; Ereignisanalyse wird **Could** | Kurze Reihe nach 2020, kleiner und umstrittener Effekt, MODIS-Bahndrift |
| Stoffe | Sulfat, Wolken | Schwefel, Ruß, Stickstoff, Staub, Rauch/organischer Kohlenstoff, Mikroplastik (nur Meer), natürliche Kontrollen, CO als Transportmarker | Ursprüngliche Projektidee; alle mit NASA-Variablen belegt |
| Nutzer | ein Modus mit Detektiv-Fragen | **Schülermodus** (geführtes Formular) und **Forschungsmodus** (Expertenformular) | Interview-Entscheidung |
| Daten | nur zwischengespeichert | Demos zwischengespeichert; Forschungsmodus optional live (Giovanni-API/OPeNDAP mit eigenem Earthdata-Token) | Interview-Entscheidung |
| Sprache | deutsch | App, Erklärtexte und Pitch **englisch**, Spec deutsch | internationale Jury |
| Flussbegradigung | optionaler Fall 2 | entfällt; Boden und Fluss sind Schritte der Spur | Fokus |

---

## 1. Problem

Es gibt Tausende Erdbeobachtungs-Variablen. Für Schüler, Studierende und interessierte Laien ist kaum erkennbar, welche davon eine Veränderung anzeigen, und noch weniger, ob ein Trend statistisch belastbar ist. Bestehende Werkzeuge decken jeweils nur einen Ausschnitt ab:

- Giovanni erzeugt Zeitreihen, testet aber nicht auf Signifikanz und erklärt die Variablen kaum.
- Spezialwerkzeuge wie EPA Critical Loads Mapper (Deposition), NADP-Trendkarten (Niederschlagschemie) und USGS-Flusstrendstudien (WRTDS/EGRET) behandeln jeweils nur einen Teilbereich.
- Nach unserer Recherche gibt es kein Werkzeug, das **einen Stoff durch mehrere Teile des Wasserkreislaufs verfolgt** und dabei für jeden Schritt Trend und Signifikanz zeigt.

Ein Lernender, der heute fragen will, ob Ruß auf Himalaya-Gletschern zunimmt und ob das überhaupt messbar ist, muss Produkte, Variablennamen, Einheiten und Statistik selbst zusammensuchen.

## 2. Was das Tool macht

Ein Web-Tool, das Variablen aus NASA-Missionen und -Modellen über ein Formular auswählt, für eine oder zwei Regionen als monatliche Zeitreihe zeigt, die Saisonalität entfernt und Änderungsrate und Signifikanz berechnet. Das Besondere ist die **Spuransicht**: Für einen Stoff zeigt das Tool nebeneinander, was in Luft, Wolke, Niederschlag/Schnee, Gletscher, Boden und Fluss passiert. Jeder Schritt erscheint als Trendkarte, und wo es keine Daten gibt, steht ehrlich eine Karte „Spur endet hier“.

Kernfähigkeiten:

- Variablenkatalog mit Kurzdefinition, Einheit, Quelle, Schritt in der Spur und Datenart (gemessen / Modell / Schätzung)
- Geführtes Formular (Schülermodus) und Expertenformular (Forschungsmodus)
- Zeitreihe, Anomalien, Sen's Slope, Mann-Kendall mit Autokorrelationskorrektur, OLS mit Konfidenzintervall
- Zwei-Regionen-Vergleich für gegenläufige Trends
- Spuransicht pro Stoff mit Trendkarten und „Spur endet hier“-Karten
- Klartext-Ergebnis: Was, Wo, Wie stark, Signifikant? Dazu der Hinweis „Korrelation ist keine Ursache“
- Vorbereitete Demos, die offline laufen; Export als CSV, PNG und Methodenbericht

**Leitidee:** Das Tool ist die Plattform, die Fälle sind Voreinstellungen (Stoff + Variablen + Regionen + Erklärtext). Statistik und Oberfläche sind für alle Fälle gleich.

## 3. Für wen

| Modus | Nutzer | Kontext |
|---|---|---|
| **Schülermodus** | Schüler der Oberstufe, Studierende, interessierte Laien mit naturwissenschaftlichem Hintergrund (Challenge-Zielgruppe) | Geführtes Formular mit 3 bis 4 Fragen, einfache Sprache, Demos zum Zuschauen |
| **Forschungsmodus** | Forschende und fortgeschrittene Studierende, die eine Hypothese schnell prüfen wollen | Freie Wahl von Variable, Bounding Box und Zeitraum, Optionen für die Statistik, optional Live-Abruf mit eigenem Earthdata-Token |

## 4. Für wen nicht

- Nicht für publikationsreife Analysen. Das Tool ist ein Screening- und Lernwerkzeug, keine Begutachtung.
- Nicht für Echtzeit-Luftqualität, Gesundheitswarnungen oder Behördenentscheidungen.
- Nicht für die Belastung eines einzelnen Sees, Brunnens, Feldes oder Gletschers. Die Rasterzellen sind 0,25° bis 1° groß, also etwa 25 bis 100 km.
- Nicht für die Chemie in Wolkentropfen, Gletschereis oder Boden als Messwert. Dafür gibt es keine Zeitreihen, und das Tool behauptet sie nicht.
- Nicht für Prognosen.

## 5. Abgleich mit der Challenge

| Challenge-Anforderung | Umsetzung |
|---|---|
| Variablen identifizieren (MODIS, OMI, AIRS, GPM, MERRA-2, GLDAS) | Kuratierter Katalog mit allen sechs: OMI (SO₂, NO₂, Aerosolindex), MODIS (Wolken, Schneealbedo), AIRS (CO, CO₂), GPM IMERG (Niederschlag), MERRA-2 (Aerosole, Deposition, Niederschlag), GLDAS (Schnee, Bodenwasser, Abfluss) |
| Daten für eine Region holen | Regionsvorauswahl, Bounding Box im Expertenformular, zwischengespeicherte Demo-Daten, optional Live-Abruf |
| Zeitreihe lang genug für Statistik | Monatlich; MERRA-2 ab 1980, OMI ab 2004, GLDAS 2.1 ab 2000. Warnung bei weniger als 10 Jahren |
| Änderungsrate und Signifikanz (t-Test, Mann-Kendall, Konfidenzintervall) | Sen's Slope, Mann-Kendall (Hamed-Rao), OLS mit 95-%-Konfidenzintervall, Klartext-Ergebnis |
| „Gleicher Prozess, gegenläufiger Trend in anderer Region“ | Zwei-Regionen-Vergleich als **Must**; Demo A1 Ost-Nordamerika gegen Indien |
| Wo ändert es sich | Zwei Regionen nebeneinander (Must), räumliche Trendkarte (Could) |
| Einfache Definitionen, Datendetektive, kurze Fragenfolge, Demos | Schülermodus mit geführtem Formular, Erklärtexte, drei Demos |
| Saisonzyklus entfernen; lineare Trends genügen | Anomalien als Must; nur lineare Trends im Must-Umfang |
| „Ein nicht signifikanter Trend ist auch interessant“ | Label „Kein Nachweis“ genauso prominent; Hinweis „mit mehr Jahren könnte er signifikant werden“ |
| Ressourcen-Tab (Hydrology Time Series, CUAHSI, KNMI, Statistik-Leitfaden) | Wasserseite der Spur aus den Hydrology-Time-Series-Datensätzen; Validierung gegen KNMI Climate Explorer |
| KI (optional) | Nicht im Must; Freitextsuche als Could (C8) |

## 6. Erfolgskriterien

1. Eine Testperson ohne Vorwissen kommt im Schülermodus in **unter 3 Minuten** vom Start zu einer Ergebniskarte mit Trend und Signifikanz.
2. **Demo A1** zeigt für Schwefel (SO₂ oder Sulfat) in Ost-Nordamerika und Indien Trends mit Richtung, Änderungsrate pro Dekade, p-Wert und Konfidenzintervall. Ob sie gegenläufig sind, entscheiden die Daten; das Tool zeigt es ehrlich.
3. Die **Spuransicht** zeigt für Schwefel, Ruß und Staub je Region mindestens 4 Schritte als Trendkarten und die übrigen als „Spur endet hier“-Karten mit Begründung.
4. Der **Validierungsfall** (CO₂) und die synthetischen Tests bestehen alle Abnahmekriterien aus Abschnitt 13.
5. Jede Karte nennt Produkt, Version, Variable, Einheit und Datenart (gemessen / Modell / Schätzung).
6. Alle Demos laufen ohne Internet in unter 5 Sekunden pro Analyse.
7. Das Repository ist öffentlich, hat eine OSI-Lizenz und eine README mit Datenquellen und Grenzen.

## 7. Nutzerfluss

**Schülermodus (geführtes Formular)**

1. *What do you want to follow?* Stoffauswahl mit Bild und einem Satz Erklärung: Sulfur, Soot, Nitrogen, Dust, Smoke, Microplastics, Natural sources, CO.
2. *Where?* Demo-Regionspaare oder eine Region aus einer Liste: Stadt, Wüste, Regenwald, Gebirge/Gletscher, Küste/Flussmündung, Ozean.
3. *Which part of the water's journey?* Air, Cloud, Rain & snow, Glacier, Soil, River & sea, oder „the whole trail“.
4. *Which period?* Vorgabe ist der längste verfügbare Zeitraum.
5. **Ergebnis:** Spuransicht oder Einzelkarte, Plot, Klartext, Evidenzlabel, Export.

**Forschungsmodus (Expertenformular)**

1. Beliebige Variable aus dem Katalog oder, wenn ein Token vorhanden ist, per Giovanni-Data-ID.
2. Eine oder zwei Bounding Boxes, Zeitraum, Aggregation (monatlich), Klimatologie-Zeitraum.
3. Statistikoptionen: Mann-Kendall-Variante, Signifikanzniveau, mit oder ohne Anomalien, Benjamini-Hochberg bei mehreren Karten.
4. Ergebnis wie oben, zusätzlich Methodenbericht mit allen Parametern und Abruf-URLs.

## 8. Funktionale Anforderungen

### Must have

| ID | Anforderung |
|---|---|
| M1 | Variablenkatalog (Datei `catalog/variables.yaml`): Name, englische Kurzdefinition, Einheit, Produkt, Version, Variable, Stoff, Spurschritt, Datenart, Zeitraum, Abdeckung |
| M2 | Geführtes Formular (Schülermodus) nach Abschnitt 7 |
| M3 | Expertenformular (Forschungsmodus) mit Variable, Bounding Box(es) und Zeitraum aus dem Cache |
| M4 | Monatliche Gebietsmittel mit cos(Breite)-Gewichtung |
| M5 | Saisonbereinigung: Anomalien gegen die Monatsklimatologie |
| M6 | Trend: Sen's Slope und OLS mit 95-%-Konfidenzintervall, angegeben pro Jahr, pro Dekade und in % des Mittelwerts |
| M7 | Signifikanz: Mann-Kendall mit Hamed-Rao-Korrektur, p-Wert, Evidenzlabel (Abschnitt 9), Hinweis bei zu kurzer Reihe |
| M8 | Zwei-Regionen-Vergleich nebeneinander, mit Klartext bei gegenläufigem Trend |
| M9 | Spuransicht: Trendkarten pro Schritt für einen Stoff und eine Region; „Spur endet hier“-Karten mit Begründung und Literaturlink |
| M10 | Demo A1 „Follow the trail“: Schwefel, Ruß und Staub in Ost-Nordamerika gegen Indien, zwischengespeichert |
| M11 | Klartext-Ergebnis (Was, Wo, Wie stark, Signifikant?), Hinweis „Korrelation ist keine Ursache“, Kennzeichnung der Datenart |
| M12 | Validierungsfall CO₂ und synthetische Tests (Abschnitt 13) |

### Should have

| ID | Anforderung |
|---|---|
| S1 | Demo A2 „Glaciers“: Alpen gegen Himalaya mit Ruß- und Staubdeposition, MODIS-Schneealbedo, Schnee und Abfluss |
| S2 | Rauch/organischer Kohlenstoff (MERRA-2 OC, OMI-Aerosolindex) |
| S3 | Stickstoff: OMI NO₂ troposphärisch |
| S4 | Demo B „Ships and clouds“: Schifffahrtsroute gegen benachbarte Meeresfläche, SO₂/Sulfat und MODIS-Tropfenradius, als Zwei-Regionen-Trendvergleich |
| S5 | Live-Abruf im Forschungsmodus über die Giovanni-Time-Series-API oder OPeNDAP mit dem Earthdata-Token des Nutzers |
| S6 | Export: CSV, PNG, Methodenbericht (Markdown oder PDF) |
| S7 | Abgeleitete Größe „Konzentration im Niederschlag (Modellschätzung)“ = nasse Deposition / Niederschlag |
| S8 | Optionaler Abgleich mit offenen Bodendaten (eine Reihe NADP oder CAPMoN für Niederschlag, WQP oder ECCC für Fluss-Sulfat), standardmäßig aus |
| S9 | Konfidenzband der Steigung im Plot |

### Could have

| ID | Anforderung |
|---|---|
| C1 | Mikroplastik im Meer (CYGNSS) vor Flussmündungen, z. B. Mississippi und Ganges |
| C2 | Natürliche Kontrollen: DMS (Meeresschwefel), Seesalz, Vulkan-SO₂ |
| C3 | CO als Transportmarker; Pfeilkarte aus den MERRA-2-Transportflüssen (`SUFLUXU/V`, `BCFLUXU/V`, `DUFLUXU/V`) |
| C4 | Ereignisanalyse (unterbrochene Zeitreihe, Differenz-von-Differenzen) für IMO 2020 |
| C5 | Räumliche Trendkarte (Trend pro Gitterzelle) |
| C6 | Benjamini-Hochberg-Korrektur über alle Karten einer Spur |
| C7 | Zeitverzögerte Korrelation zwischen benachbarten Spurschritten |
| C8 | KI-Freitext („soot on Himalayan glaciers“) → Katalogeinträge, nur mit eigenem Schlüssel, Stichwort-Fallback |
| C9 | Docker-Image |

### Won't have (diesmal)

- Phosphor und Eisen (keine NASA-Variable)
- Messwerte für Schadstoffe in Wolkentropfen, Gletschereis oder Boden; Mikroplastik in Wolken, Gletschern oder Boden (keine Zeitreihen vorhanden, nur „Spur endet hier“-Karten)
- Eigene Datenbank, Grafana, Java-Backend
- Prognosen, Echtzeit- oder Stundendaten
- Gesundheits- oder Behördenbewertungen

## 9. Statistik-Spezifikation

**Vorverarbeitung**

- Monatliche Gebietsmittel pro Variable und Region, gewichtet mit cos(Breite)
- Einheiten werden beim Laden vereinheitlicht, z. B. Deposition von kg m⁻² s⁻¹ in mg m⁻² Monat⁻¹
- Anomalien: Wert minus Klimatologie des Kalendermonats; Klimatologie standardmäßig über den ganzen verfügbaren Zeitraum, im Forschungsmodus wählbar
- Fehlende Werte werden markiert, nicht interpoliert; Warnung ab mehr als 10 % Lücken

**Trend**

- Sen's Slope (robust) und OLS mit 95-%-Konfidenzintervall (statsmodels)
- Mann-Kendall mit Hamed-Rao-Korrektur als Standard (pymannkendall); klassischer Mann-Kendall zum Vergleich und Hinweis, wenn beide abweichen
- Signifikanzniveau 5 %; immer angezeigt: p-Wert, Steigung pro Dekade, Konfidenzintervall, Änderung in % des Mittelwerts
- Länge: Warnung unter 10 Jahren, Empfehlung ab 15 Jahren

**Evidenzlabel**

| Label | Bedingung |
|---|---|
| **Strong** | Mann-Kendall (Hamed-Rao) p < 0,05, OLS-Konfidenzintervall schließt 0 aus, Reihe ≥ 15 Jahre |
| **Weak** | nur eines der beiden Kriterien erfüllt oder Reihe 10 bis 15 Jahre |
| **No evidence** | nicht signifikant; wird genauso prominent gezeigt, mit dem Satz „a longer record might make it significant“ |

**Zwei-Regionen-Vergleich und Spur**

- Jede Region und jeder Schritt wird einzeln getestet. Der Klartext sagt „opposite trends“ nur, wenn beide Richtungen mindestens *Weak* sind.
- Trends in benachbarten Spurschritten werden **nebeneinander** gezeigt, nicht kausal verknüpft.
- Im Forschungsmodus optional Benjamini-Hochberg über alle Karten einer Spur (C6).

**Ereignisanalyse (Could, C4):** wie v1 Abschnitt 6 (unterbrochene Zeitreihe, Differenz-von-Differenzen, Mindestlänge 36 Monate vor und nach dem Ereignis).

## 10. Variablen, Spur und Daten

### 10.1 Das Spurmodell

```text
Quelle (Verkehr, Industrie, Schiffe, Feuer, Wüste, Meer)
  → Luft (Säule, Oberfläche, Transport)
  → Wolke (Bildung, Auswaschung, Eiskeime)
  → Niederschlag / Schnee (nasse und trockene Deposition)
  → Gletscher / Schneedecke (Ablagerung, Verdunkelung, Schmelze)
  → Boden (nur Wasser als Träger: Bodenfeuchte je Tiefe, Versickerung)
  → Fluss / See / Meer (Abfluss, Mikroplastik)
```

Jeder Pfeil ist eine Hypothese, die das Tool nicht beweist. Es zeigt die Trends der einzelnen Schritte, damit der Nutzer selbst zum Detektiv wird.

**Staub und Eis:** Mineralstaub ist der wichtigste Eiskeim in Wolken und damit der Stoff, der am direktesten an der Eisbildung beteiligt ist. Das Tool verfolgt Staub selbst (Säule, Deposition, Verdunkelung von Schnee).

**Phosphor und Eisen** werden nicht verfolgt (Teamentscheidung vom 14.11.2026): Es gibt keine NASA-Variable dafür, nur grobe Schätzungen aus der Staubdeposition.

### 10.2 Matrix Stoff × Spurschritt

✅ gemessene Zeitreihe · 🟡 Modell oder Schätzung · ⚪ optional offene Bodendaten · ❌ keine Zeitreihe („Spur endet hier“)

| Stoff | Luft | Wolke | Niederschlag/Schnee | Gletscher | Boden | Fluss/See/Meer |
|---|---|---|---|---|---|---|
| Schwefel | ✅ OMI SO₂; 🟡 MERRA-2 Sulfat | 🟡 Sulfatbildung in Wolken, Auswaschung | 🟡 nasse Deposition; ⚪ NADP/CAPMoN | 🟡 Deposition über Gletscherfläche | ❌ | ⚪ Fluss-Sulfat (WQP/ECCC) |
| Ruß | 🟡 MERRA-2 BC | 🟡 Auswaschung | 🟡 Deposition | ✅ Verdunkelung (MODIS-Schneealbedo) | ❌ | ❌ |
| Stickstoff | ✅ OMI NO₂ | ❌ | ⚪ Nitrat NADP/CAPMoN | ❌ | ❌ | ⚪ Fluss-Nitrat |
| Staub | 🟡 MERRA-2; ✅ OMI-Aerosolindex | 🟡 Eiskeim, Auswaschung | 🟡 Deposition | ✅ Verdunkelung | ❌ | ❌ |
| Rauch/OC | 🟡 MERRA-2 OC; ✅ OMI-Aerosolindex | 🟡 Auswaschung | 🟡 Deposition | ✅ Verdunkelung | ❌ | ❌ |
| Mikroplastik | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ CYGNSS, nur Meer 37,4° S bis 37,4° N, ab 08/2018 |
| Natürliche Kontrollen | 🟡 DMS, Seesalz, Vulkan-SO₂ | 🟡 | 🟡 | – | – | – |
| CO (Transport) | ✅ MOPITT, AIRS | – | – | – | – | – |
| **Wasser** (Träger) | ✅ AIRS/MERRA-2 Wasserdampf | ✅ MODIS/MERRA-2 Wolkenwasser | ✅ IMERG, MERRA-2 | 🟡 GLDAS-Schnee, MERRA-2-Gletscherabfluss | 🟡 GLDAS-Bodenfeuchte je Tiefe | 🟡 GLDAS-Abfluss, NLDAS-Streamflow (nur USA) |

### 10.3 Variablenkatalog (Must, Namen im NASA-Katalog geprüft am 14.11.2026)

| Schritt | Stoff | Produkt | Variable(n) | Einheit (Datei) | Art |
|---|---|---|---|---|---|
| Luft | Schwefel | OMI `OMSO2e` (Version 003/004 prüfen) | `ColumnAmountSO2` | DU | gemessen |
| Luft | Schwefel | MERRA-2 `M2TMNXAER` | `SO4CMASS`, `SO4SMASS`, `SO2CMASS` | kg m⁻², kg m⁻³ | Modell |
| Wolke | Schwefel | MERRA-2 `M2TMNXADG` | `SUPSO4AQ` (Sulfatbildung in Wolkenwasser), `SUSV001`–`004` (konvektive Auswaschung) | kg m⁻² s⁻¹ | Modell |
| Niederschlag | Schwefel | MERRA-2 `M2TMNXADG` | `SUWT001`–`004` (nass), `SUDP001`–`004` (trocken) | kg m⁻² s⁻¹ | Modell |
| Luft | Ruß | MERRA-2 `M2TMNXAER` | `BCCMASS`, `BCSMASS` | kg m⁻² | Modell |
| Niederschlag | Ruß | MERRA-2 `M2TMNXADG` | `BCWT001`–`002`, `BCDP001`–`002` | kg m⁻² s⁻¹ | Modell |
| Luft | Staub | MERRA-2 `M2TMNXAER` | `DUCMASS`, `DUSMASS` | kg m⁻² | Modell |
| Niederschlag | Staub | MERRA-2 `M2TMNXADG` | `DUWT001`–`005`, `DUDP001`–`005` | kg m⁻² s⁻¹ | Modell |
| Gletscher | Ruß, Staub, Rauch | MODIS `MOD10A1.061` (AppEEARS) | `Snow_Albedo_Daily_Tile` | % | gemessen |
| Gletscher | Wasser | MERRA-2 `M2TMNXGLC` | `RUNOFF`, `SNOMAS_GL` | kg m⁻² s⁻¹, kg m⁻² | Modell |
| Niederschlag | Wasser | MERRA-2 `M2TMNXFLX`; GPM `GPM_3IMERGM` | `PRECTOTCORR`, `PRECSNO`; `precipitation` | kg m⁻² s⁻¹; mm h⁻¹ | Modell; gemessen |
| Schnee | Wasser | GLDAS `GLDAS_NOAH025_M.2.1` | `SWE_inst`, `Snowf_tavg`, `Qsm_acc` | kg m⁻² | Modell |
| Boden | Wasser | GLDAS `GLDAS_NOAH025_M.2.1` | `SoilMoi0_10cm_inst` bis `SoilMoi100_200cm_inst`, `Qs_acc`, `Qsb_acc` | kg m⁻² | Modell |
| Validierung | CO₂ | OCO-2 L3 oder AIRS (Produkt und Laufzeit prüfen) | CO₂-Säule / Mischungsverhältnis | ppm | gemessen/Modell |

Should- und Could-Variablen:

- **Stickstoff:** OMI `OMNO2d` `ColumnAmountNO2TropCloudScreened`
- **Rauch:** MERRA-2 `OCCMASS`, `OCWT001`–`002`, `OCDP001`–`002`; OMI `OMAERUVd` `UVAerosolIndex`
- **Schiffe (Demo B):** MODIS `MOD08_M3`/`MYD08_M3` `Cloud_Effective_Radius_Liquid_Mean_Mean`, `Cloud_Water_Path_Liquid_Mean_Mean`, `Cloud_Optical_Thickness_Liquid_Mean_Mean`
- **Mikroplastik:** `CYGNSS_L3_MICROPLASTIC_V3.2` `mp_concentration` (#/km²), `num_mp_samples`
- **Natürliche Kontrollen:** MERRA-2 `DMSCMASS`, `SSCMASS`, `SO2EMVE`/`SO2EMVN` (Vulkan)
- **Transport:** `SUFLUXU/V`, `BCFLUXU/V`, `DUFLUXU/V`; MOPITT `MOP03JM` (CO, ab 2000); AIRS `AIRS3STM` `CO_VMR_A`
- **USA-Flüsse:** NLDAS `Streamflow` (nur USA, bis etwa 53° N)

Weitere Variablennamen, Endpunkte und Authentifizierung stehen in `research/hydrological_data_apis_and_variables.md` (im Wiki: *Datasets and Varsity*).

### 10.4 Gemeinsames Datenformat

Ein DataFrame mit den Spalten `date` (Monatsanfang), `value`, `unit`, `variable`, `product`, `version`, `region`, `substance`, `step`, `kind` (`measured` | `model` | `estimate`), `source_url`.

### 10.5 Datenquellen und Zugriff

| Quelle | Zugriff | Auth | Rolle |
|---|---|---|---|
| Giovanni / GES DISC (MERRA-2, OMI, AIRS, GLDAS, NLDAS, IMERG) | CSV-Export für den Cache; live: `https://api.giovanni.earthdata.nasa.gov/timeseries` oder OPeNDAP/Harmony | Earthdata-Token (kostenlos, je Person) | Hauptquelle |
| Hydrology Time Series (GES DISC) | GLDAS, NLDAS, IMERG, MERRA-2, GRACE-DA, SMERGE | Earthdata | Wasserseite der Spur |
| AppEEARS (MODIS-Schneealbedo) | REST-Aufgaben, vorab für Demo-Regionen | Earthdata | Gletscherschritt |
| PO.DAAC (CYGNSS), LAADS (MOD08) | earthaccess | Earthdata | Should/Could |
| Optional, offen: NADP, CAPMoN (open.canada.ca), Water Quality Portal, ECCC Long-term Water Quality | CSV/REST | keine bzw. frei | nur Abgleich, standardmäßig aus |

Vorab geladene Demo-Daten liegen als Parquet unter `data/`. Während der Präsentation gibt es keinen Live-Abruf. Lizenzen aller Zusatzdaten werden vor der Nutzung geprüft, wie es die Space-Apps-Bedingungen verlangen.

## 11. Demo-Fälle

Die Regionsboxen sind Vorschläge und werden vor dem Datenabruf festgelegt.

| Fall | Zweck | Regionen (Vorschlag) | Stoffe | Priorität |
|---|---|---|---|---|
| **A1 „Follow the trail: same process, opposite trends“** | Hauptdemo; gegenläufige Trends | Ost-Nordamerika: Ohio Valley ca. 37–42° N, 88–80° W (Quelle) und Québec/Adirondacks ca. 44–48° N, 78–70° W (windabwärts). Indien: Indo-Gangetic Plain ca. 22–30° N, 75–88° E | Schwefel, Ruß, Staub | Must |
| **A2 „Glaciers“** | Gletscherschritt mit messbarer Verdunkelung | Alpen ca. 45,5–47,5° N, 6–13° E; Zentral-Himalaya ca. 27–30° N, 82–88° E | Ruß, Staub, Rauch | Should |
| **B „Ships and clouds“** | Brücke zu v1; Schiffsschwefel | Schifffahrtsroute gegen benachbarte Meeresfläche (Boxen aus v1 übernehmen) | Schwefel, Wolkentropfenradius | Should |
| **V „Check a known trend“** | Validierung (Positivkontrolle) | Nordhalbkugel oder global | CO₂ | Must |
| **Freie Wahl** | Forschungs- und Schülermodus | beliebig | alle im Katalog | Must (aus Cache), Should (live) |

**Erwartungen sind Hypothesen, keine Vorgaben.** Die Literatur berichtet in Ost-Nordamerika seit den Luftreinhaltegesetzen um 1990 deutlich sinkende Schwefelwerte in Luft, Niederschlag und vielen Flüssen. Für Indien berichtet sie für weite Teile des OMI-Zeitraums steigende SO₂-Werte. Das Tool prüft das mit den Daten und zeigt jedes Ergebnis, auch „No evidence“.

## 12. Schlüsselentscheidungen

- **Hauptfall:** IMO 2020 / Schadstoffspur / beides. **Gewählt: Spur als Hauptfall, IMO 2020 als kurzer Demo-Fall B**, weil die Spur die Challenge-Schwerpunkte (gegenläufige Trends, Hydrologie, lange Reihen) direkt trifft.
- **Datenzugriff:** nur Cache / Cache + live / nur live. **Gewählt: Demos aus dem Cache, Forschungsmodus optional live**, damit die Demo bei der Jury sicher läuft.
- **Datenquellen:** NASA-only / NASA + Bodendaten. **Gewählt: NASA als Hauptquelle, offene Bodendaten nur optional zum Abgleich**, wegen Challenge-Text, Lizenzbedingungen und Aufwand.
- **Oberfläche:** Streamlit / React + API. **Gewählt: Streamlit mit `st.form`**, wegen eines Python-Teams und 1,5 Tagen Zeit.
- **Modi:** ein Modus / Schüler + Forschung. **Gewählt: zwei Modi auf demselben Kern**, gewählt im Interview.
- **Sprache:** **App englisch, Spec deutsch**, wegen der internationalen Jury.
- **KI:** Must / Could / gar nicht. **Gewählt: Could (C8)**; kein Kernbestandteil und keine Abhängigkeit von kostenpflichtigen Schlüsseln.
- **Phosphor und Eisen:** weglassen / als Schätzung. **Gewählt: beide entfallen**, weil es kein direktes NASA-Produkt gibt und Schätzungen aus Staub zu grob wären.
- **Name:** **Earth Trail Detective** (englisch, wie die App).
- **Lizenz:** **Apache-2.0** (OSI). Ohne eigene Lizenz verteilt NASA den Code ohnehin unter Apache-2.0.

## 13. Bauplan und Verifikation

### 13.1 Bauplan (in Reihenfolge)

| Schritt | Inhalt | Wer | Entscheidung / Vorgabe |
|---|---|---|---|
| 1 | Repository, Lizenz, Datenformat (10.4), `catalog/variables.yaml` mit den Must-Variablen | A | YAML statt Code, damit Erklärtexte ohne Programmieren änderbar sind |
| 2 | Statistikkern: Anomalien, Sen, OLS, Mann-Kendall (Hamed-Rao), Evidenzlabel, mit Tests auf synthetischen Daten | B | pymannkendall + statsmodels |
| 3 | Demo-Daten A1 laden (Giovanni-CSV oder earthaccess), Gebietsmittel, Einheiten, Parquet | A | Monatsdaten, längster Zeitraum |
| 4 | Validierungsfall V durchlaufen lassen; erst wenn er besteht, A1 auswerten | B | Abnahmekriterien 13.2 |
| 5 | Oberfläche: geführtes Formular, Ergebniskarte, Zwei-Regionen-Vergleich | B | `st.form`, Plotly |
| 6 | Spuransicht mit Trendkarten und „Spur endet hier“-Karten | A + B | Karten aus Katalogfeld `step` |
| 7 | Expertenformular (Forschungsmodus) aus dem Cache | B | — |
| 8 | Should nach verbleibender Zeit: A2, B, NO₂, Rauch, Export, Live-Abruf | A + B | A2 vor B (Gletscher sind Teil der Kernidee) |
| 9 | README, Erklärtexte, Pitch, Video, Abgabe | gemeinsam | mindestens ein halber Tag |

**Zeitplan (ab Samstagnachmittag):** Sa Nachmittag Schritte 1–3 parallel; Sa Abend 4–5; So Vormittag 6–7; So Mittag 8; So Nachmittag 9.

### 13.2 Verifikation

| Bereich | Vorgehen | Werkzeuge |
|---|---|---|
| Statistikkern | Unit-Tests: (a) Reihe mit bekanntem Trend + Rauschen → Steigung getroffen; (b) reines Rauschen → in ~95 % von 1000 Läufen „nicht signifikant“; (c) autokorreliertes Rauschen → Hamed-Rao verhindert Scheinsignifikanz; (d) Saisonbereinigung verkleinert das Konfidenzintervall | pytest, numpy |
| Validierung CO₂ | Trend signifikant positiv, Label *Strong*, Konfidenzintervall überlappt Referenzwert (KNMI Climate Explorer oder Literatur), Sen und OLS in gleicher Richtung | gecachte Reihe, Referenzwert notiert |
| Datenlader | Je Variable: Einheit, Zeitraum, Anteil fehlender Werte, Plausibilitätsbereich; Stichprobe gegen Giovanni-Plot derselben Box | pytest + Prüfliste |
| Gebietsmittel | Eine Box manuell gegen Giovanni „Area-Averaged Time Series“ vergleichen (Abweichung < 1 %) | Giovanni |
| Oberfläche | Manuelle Prüfliste: jeder Formularpfad endet in einer Karte; Testperson schafft es in < 3 min; Offline-Test mit ausgeschaltetem WLAN | Checkliste |
| Ehrlichkeit | Jede Karte zeigt Datenart, Quelle und Version; „Spur endet hier“ erscheint für alle ❌-Felder der Matrix 10.2 | Checkliste |

## 14. Nicht-funktionale Anforderungen

- Demos laufen offline aus dem Cache; Analyse unter 5 Sekunden
- App-Texte englisch, einfache Sprache, Fachbegriffe mit Kurzdefinition
- Farbenblind-taugliche Farben; Trendrichtung zusätzlich mit Pfeil und Text, nicht nur mit Farbe
- Earthdata-Token nur aus Umgebungsvariable oder `st.secrets`, nie im Repository und nie im Browser
- Öffentliches Repository, Apache-2.0, README mit Installation, Start, Datenquellen, Lizenzen und Grenzen; jede Quelle zitiert
- Statistikfunktionen mit Tests

## 15. Risiken und offene Fragen

- **MERRA-2-Emissionen:** Die anthropogenen Emissionsinventare in MERRA-2 sind für die letzten Jahre möglicherweise nur eingeschränkt aktualisiert (zu prüfen, Randles et al. 2017). Sulfat- und Ruß-Trends nach etwa 2010 werden deshalb mit gemessenem OMI-SO₂ bzw. dem OMI-Aerosolindex gegengeprüft und im Tool als Modell gekennzeichnet.
- **Modell statt Messung:** Wolken-, Depositions- und Gletscherschritte sind überwiegend Modellwerte. Das muss jede Karte deutlich sagen.
- **Rasterauflösung:** Gletscher und Flüsse sind kleiner als die Rasterzellen; Gletscherwerte sind Gebietsmittel über Gebirgsboxen.
- **Mikroplastik (CYGNSS):** Forschungsprodukt, aus Meeresoberflächenrauigkeit abgeleitet, nur zwischen 37,4° S und 37,4° N, erst ab 2018. Kurze Reihe, also oft „No evidence“.
- **Sensordrift und Lücken:** Bahndrift von MODIS Terra/Aqua, OMI-Row-Anomaly, GLDAS-2.0/2.1-Wechsel im Jahr 2000. Warnungen im Tool.
- **Umfang:** acht Stoffgruppen und drei Demos sind für 1,5 Tage viel. Die Must-Liste ist bewusst schmal; Should wird nur nach Abschluss von Must begonnen.
- **Live-Abruf:** Das genaue Format der Giovanni-Data-IDs für die Time-Series-API ist mit Token zu prüfen.
- **Offen:** Regionsboxen festlegen; Referenzwert für CO₂ nachschlagen; Abgabeformat (Video/Folien) im Participant Guide 2026 prüfen.

## 16. Abgabe-Checkliste (Bewertungskriterien)

Die Kriterien sind Impact, Creativity, Validity, Relevance und Presentation (vor der Abgabe gegen den Leitfaden 2026 prüfen).

- **Relevance:** alle vier Challenge-Ziele plus gegenläufige Trends (Abschnitt 5)
- **Validity:** Saisonbereinigung, Autokorrelationskorrektur, Validierungsfall, synthetische Tests, Kennzeichnung Modell/Messung/Schätzung, ehrliche „No evidence“- und „Spur endet hier“-Karten
- **Creativity:** einen Stoff durch den Wasserkreislauf verfolgen; Staub als Eiskeim; zwei Modi
- **Impact:** Lernwerkzeug für Schüler und Studierende, schneller erster Blick für Forschende, ohne Überversprechen
- **Presentation:** Demo A1 läuft offline, klare Geschichte („Follow the trail“), öffentliches Repository, Video/Folien
