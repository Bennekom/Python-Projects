
GPX Splitter Script

Splits een GPX-bestand met meerdere deelroutes (tracks) in afzonderlijke GPX-bestanden.
- Bestandsnamen zijn gebaseerd op de tracknaam (<name>), veilig gemaakt voor het OS.
- Elke deelroute krijgt een unieke kleur (8 onderscheidende, zon onleesbare kleuren; vermijd geel, groen, lichtblauw).
- Voegt een <bounds> element toe met min/max lat/lon van alle punten in de deelroute.
- Schrijft de gekozen kleur op twee plekken per deelroute:
    1) <extensions><display_color>#HEX</display_color></extensions>
    2) <gpx:extensions><gpxt:TrackExtension><gpxt:DisplayColor>#HEX</gpxt:DisplayColor></gpxt:TrackExtension></gpx:extensions>
- Outputfolder wordt automatisch aangemaakt in dezelfde map als het inputbestand:
  <input_bestandsnaam_zonder_extensie>_<YYYYMMDD_HHMMSS>
- Alle waypoints (<wpt>) uit het inputbestand worden weggeschreven naar:
  All-Waypoints.gpx (in outputmap)

Gebruik:
  python split_gpx.py --input /pad/naar/input.gpx
  python split_gpx.py -i /pad/naar/input.gpx
