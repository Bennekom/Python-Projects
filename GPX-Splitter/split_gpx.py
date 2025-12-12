
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPX Splitter Script

Splits een GPX-bestand met meerdere deelroutes (tracks) in afzonderlijke GPX-bestanden.
- Bestandsnamen zijn gebaseerd op de tracknaam (<name>), veilig gemaakt voor het OS.
- Elke deelroute krijgt een unieke kleur (8 onderscheidende, zonleesbare kleuren; vermijd geel, groen, lichtblauw).
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
"""

import os
import re
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
import colorsys

# Namespaces en prefix-registratie
GPX_NS = "http://www.topografix.com/GPX/1/1"                  # gpx
GARMIN_GPXX_NS = "http://www.garmin.com/xmlschemas/GpxExtensions/v3"  # gpxt
ET.register_namespace('gpx', GPX_NS)
ET.register_namespace('gpxt', GARMIN_GPXX_NS)

def generate_safe_colors(n=8):
    """Genereer n goed onderscheidende kleuren, vermijd geel, groen, lichtblauw (zonleesbaar: S=1.0, V=0.85)."""
    colors = []
    step = 360.0 / n
    hue_deg = 0.0
    while len(colors) < n:
        banned = (
            50.0 <= hue_deg <= 70.0 or      # geel
            100.0 <= hue_deg <= 140.0 or    # groen
            180.0 <= hue_deg <= 210.0       # lichtblauw
        )
        if not banned:
            r, g, b = colorsys.hsv_to_rgb(hue_deg / 360.0, 1.0, 0.85)
            hex_color = '#{:02X}{:02X}{:02X}'.format(int(r * 255), int(g * 255), int(b * 255))
            colors.append(hex_color)
        hue_deg += step
        if hue_deg >= 360.0:
            hue_deg -= 360.0
    return colors

COLORS = generate_safe_colors(8)

def sanitize_filename(name: str) -> str:
    """Maak een veilige bestandsnaam uit de tracknaam."""
    if not name:
        return "deelroute"
    sanitized = re.sub(r'[^A-Za-z0-9 _-]', '_', name)
    sanitized = sanitized.replace(' ', '_').strip('_')
    return sanitized or "deelroute"

def add_standard_display_color(track_elem: ET.Element, hex_color: str):
    """Voeg/werk bij: <extensions><display_color>#HEX</display_color></extensions> (ongeprefixte extensions)."""
    std_ext = track_elem.find('extensions')
    if std_ext is None:
        std_ext = ET.Element('extensions')
        track_elem.append(std_ext)
    disp = std_ext.find('display_color')
    if disp is None:
        disp = ET.Element('display_color')
        std_ext.append(disp)
    disp.text = hex_color

def add_or_update_gpxt_display_color(track_elem: ET.Element, hex_color: str):
    """
    Update bestaande gpxt:DisplayColor waar mogelijk; anders voeg namespaced blok toe:
    <gpx:extensions>
      <gpxt:TrackExtension>
        <gpxt:DisplayColor>#HEX</gpxt:DisplayColor>
      </gpxt:TrackExtension>
    </gpx:extensions>
    """
    ns = {'gpx': GPX_NS, 'gpxt': GARMIN_GPXX_NS}

    existing_disp = track_elem.find('.//gpxt:DisplayColor', ns)
    if existing_disp is not None:
        existing_disp.text = hex_color
        return

    gpx_ext = ET.Element(f'{{{GPX_NS}}}extensions')
    gpxt_track_ext = ET.SubElement(gpx_ext, f'{{{GARMIN_GPXX_NS}}}TrackExtension')
    gpxt_disp = ET.SubElement(gpxt_track_ext, f'{{{GARMIN_GPXX_NS}}}DisplayColor')
    gpxt_disp.text = hex_color
    track_elem.append(gpx_ext)

def calculate_bounds(track_elem: ET.Element):
    """Bereken min/max lat/lon van alle <trkpt> in de track."""
    ns = {'gpx': GPX_NS}
    trkpts = track_elem.findall('.//gpx:trkpt', ns)
    lats, lons = [], []
    for pt in trkpts:
        lat = pt.get('lat')
        lon = pt.get('lon')
        if lat and lon:
            try:
                lats.append(float(lat))
                lons.append(float(lon))
            except ValueError:
                pass
    if lats and lons:
        return min(lats), min(lons), max(lats), max(lons)
    return None

def add_bounds(track_elem: ET.Element, bounds):
    """Voeg <bounds minlat=... minlon=... maxlat=... maxlon=.../> toe als eerste child van <trk>."""
    if bounds:
        minlat, minlon, maxlat, maxlon = bounds
        bounds_elem = ET.Element('bounds', attrib={
            'minlat': f"{minlat}",
            'minlon': f"{minlon}",
            'maxlat': f"{maxlat}",
            'maxlon': f"{maxlon}"
        })
        track_elem.insert(0, bounds_elem)

def write_all_waypoints(root: ET.Element, target_folder: str):
    """Schrijf alle <wpt> uit de input naar All-Waypoints.gpx in de outputmap."""
    ns = {'gpx': GPX_NS}
    wpts = root.findall('gpx:wpt', ns)
    if not wpts:
        print("Geen <wpt> waypoints gevonden; All-Waypoints.gpx niet aangemaakt.")
        return

    new_gpx_root = ET.Element('gpx', attrib={
        'version': '1.1',
        'creator': 'GPX Splitter Script',
        'xmlns': GPX_NS,
        'xmlns:gpx': GPX_NS,
        'xmlns:gpxt': GARMIN_GPXX_NS
    })
    for w in wpts:
        w_copy = ET.fromstring(ET.tostring(w, encoding='utf-8'))
        new_gpx_root.append(w_copy)

    output_path = os.path.join(target_folder, "All-Waypoints.gpx")
    ET.ElementTree(new_gpx_root).write(output_path, encoding='utf-8', xml_declaration=True)
    print(f"{len(wpts)} waypoints opgeslagen in: {output_path}")

def split_gpx(input_gpx_path: str):
    """Splits het GPX-bestand per <trk>, schrijft elke track en alle waypoints weg naar de outputmap."""
    base_name = os.path.splitext(os.path.basename(input_gpx_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_folder = os.path.join(os.path.dirname(input_gpx_path), f"{base_name}_{timestamp}")
    os.makedirs(target_folder, exist_ok=True)

    try:
        tree = ET.parse(input_gpx_path)
    except ET.ParseError as e:
        print(f"Fout: Het GPX-bestand kon niet worden geparsed: {e}")
        return
    except Exception as e:
        print(f"Onverwachte fout bij het lezen van het GPX-bestand: {e}")
        return

    root = tree.getroot()
    ns = {'gpx': GPX_NS}
    tracks = root.findall('gpx:trk', ns)
    if not tracks:
        print("Geen <trk> deelroutes gevonden in het GPX-bestand.")
    else:
        for idx, track in enumerate(tracks, start=1):
            # Naam ophalen en veilig maken
            name_elem = track.find('gpx:name', ns)
            track_name = name_elem.text.strip() if (name_elem is not None and name_elem.text) else f"deelroute_{idx}"
            safe_name = sanitize_filename(track_name)

            # Kleur toekennen
            chosen_color_hex = COLORS[(idx - 1) % len(COLORS)]

            # Kleur-tag op twee plekken
            add_standard_display_color(track, chosen_color_hex)
            add_or_update_gpxt_display_color(track, chosen_color_hex)

            # Bounds berekenen en toevoegen
            bounds = calculate_bounds(track)
            add_bounds(track, bounds)

            # Nieuw GPX-document + wegschrijven
            new_gpx_root = ET.Element('gpx', attrib={
                'version': '1.1',
                'creator': 'GPX Splitter Script',
                'xmlns': GPX_NS,
                'xmlns:gpx': GPX_NS,
                'xmlns:gpxt': GARMIN_GPXX_NS
            })
            track_copy = ET.fromstring(ET.tostring(track, encoding='utf-8'))
            new_gpx_root.append(track_copy)

            output_path = os.path.join(target_folder, f"{safe_name}.gpx")
            ET.ElementTree(new_gpx_root).write(output_path, encoding='utf-8', xml_declaration=True)

        if tracks:
            print(f"{len(tracks)} deelroutes zijn succesvol gesplitst en opgeslagen in: {target_folder}")

    # Waypoints wegschrijven als apart bestand
    write_all_waypoints(root, target_folder)

def build_help_text() -> str:
    return (
        "\nSplits een GPX-bestand met meerdere deelroutes in afzonderlijke GPX-bestanden, voegt kleur toe (hex) en berekent bounds."
        "\nSchrijft daarnaast alle waypoints naar All-Waypoints.gpx.\n\n"
        "Voorbeeld gebruik:\n"
        "  python split_gpx.py --input /pad/naar/input.gpx\n"
        "  python split_gpx.py -i /pad/naar/input.gpx\n\n"
        "Output wordt automatisch aangemaakt in dezelfde map als het inputbestand:\n"
        "  <inputnaam>_<YYYYMMDD_HHMMSS>\n"
        "  ├─ <deelroute_1>.gpx\n"
        "  ├─ <deelroute_2>.gpx\n"
        "  └─ All-Waypoints.gpx\n"
    )

def main():
    help_text = build_help_text()
    parser = argparse.ArgumentParser(description=help_text, formatter_class=argparse.RawTextHelpFormatter)
    # Ondersteun zowel --input als -i
    parser.add_argument('--input', '-i', required=False, dest='input',
                        help='Pad naar het GPX-bestand dat gesplitst moet worden')

    args = parser.parse_args()
    if not args.input:
        print(help_text)
        parser.print_help()
        return

    if not os.path.isfile(args.input):
        print("Fout: Het opgegeven GPX-bestand bestaat niet.\n")
        print(help_text)
        return

    split_gpx(args.input)

if __name__ == "__main__":
    main()
