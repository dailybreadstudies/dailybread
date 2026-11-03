#!/usr/bin/env python3
"""Genesis 8:4: the places proposed for where the ark came to rest.

    python3 tools/build_ararat_map.py && python3 tools/check_maps.py

Writes data/maps/gen-8-ararat.json and its entry in data/maps/index.json.
Summits: Wikipedia and GeoNames (Piramagrun: GeoNames "Shak-i Pira Magrun").
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')


def site(n, ll, c, m, note, k='mount'):
    d = {'n': n, 'll': ll, 'c': c, 'm': m, 'note': note}
    if k:
        d['k'] = k
    return d


SITES = [
    site('Mount Ararat', [44.2983, 39.7019], 1, 'Ağrı Dağı (Armenian Masis), eastern Turkey · 5,137 m',
         'The highest peak in the region, a snow-capped volcano. Genesis says only "the mountains of Ararat"; the name Mount Ararat '
         'was given to this peak by Armenian tradition from about the 11th century, and medieval travellers such as William of Rubruck '
         'and Marco Polo knew it as the ark\'s mountain. It is the traditional site today.'),
    site('Durupınar site', [44.2348, 39.4407], 0, 'near Üzengili, Doğubayazıt, Turkey · about 29 km south of Ağrı Dağı',
         'A boat-shaped formation about 160 m long, exposed after earthquakes in 1948 and noticed in aerial photographs in 1959. '
         'Ron Wyatt promoted it as the ark from 1977, and Turkey opened a visitor centre there. Geologists who have studied it, '
         'including the 1960 expedition, describe it as a natural formation.', k=None),
    site('Mount Judi', [42.3442, 37.3695], 1, 'Cudi Dağı, Şırnak province, south-eastern Turkey · 2,089 m',
         'The oldest named tradition. Berossus (3rd century BC, quoted by Josephus) put the ark in the mountains of the Kordyaeans, '
         'Gordyene; the Aramaic Targum Onkelos and the Syriac Peshitta read "the mountains of Qardu" in Genesis 8:4; and the Quran '
         'says the ark "came to rest on al-Judi" (11:44). Syriac Christians had a monastery on the mountain, and travellers into the '
         'Middle Ages were shown the place of the ark here.'),
    site('Nakhchivan', [45.4125, 39.2089], 0, 'Naxçıvan, Azerbaijan',
         'Josephus says the Armenians showed "the Place of Descent," where Noah came out of the ark (Antiquities 1.92). '
         'Armenian tradition later explained the name Nakhchivan as "the place of first descent," and Noah\'s tomb is still shown in the city.', k=None),
    site('Apamea Kibotos', [30.1653, 38.0742], 0, 'Dinar, western Turkey',
         'A Phrygian tradition: the Sibylline Oracles place the ark\'s mountain near the springs of the Marsyas at Celaenae. '
         'The city was nicknamed Kibotos, "the Ark," and its coins of the 3rd century AD show Noah and his wife in the ark, '
         'with the name NΩE and the dove.', k=None),
    site('Mount Suleiman', [50.9603, 36.3908], 0, 'Takht-e Suleyman, Alborz mountains, Iran · 4,659 m',
         'A modern proposal: in 2006 Bob Cornuke\'s BASE Institute reported a blackened, beam-like rock formation high on this '
         'mountain. Critics showed that the 1894 account the search relied on describes a different Takht-i-Suliman, in Baluchistan, '
         'and the claim has found little support.'),
]
OTHER = [
    site('Mount Nimush', [45.2167, 35.7667], 1, 'Pira Magrun (Pir Omar Gudrun), Iraqi Kurdistan · 2,611 m',
         'In the Babylonian flood story (Gilgamesh, tablet XI), Utnapishtim\'s boat comes to rest on Mount Nimush, once read Nisir, '
         'and after seven days he sends out a dove, a swallow and a raven. The annals of Ashurnasirpal II place Nimush east of the '
         'Lesser Zab, and it is usually identified with Pira Magrun near Sulaymaniyah.'),
]

MAP = {
    'id': 'gen-8-ararat', 'title': 'Where Did the Ark Come to Rest?', 'ref': 'Genesis 8:4',
    'anchor': {'book': 'GEN', 'c': 8, 'v': 4}, 'range': [1, 22],
    'world': True, 'siteLabel': 'Today', 'placesName': 'Genesis', 'groupsLabel': 'Proposed sites',
    'bounds': [[29.0, 34.6], [52.5, 41.6]], 'regionZoom': 5.4,
    'links': ['mountains of Ararat'], 'aliases': {'mountains of Ararat': 'Ararat'},
    'regions': [
        {'n': 'Ararat', 'label': 'Ararat (Urartu)', 'll': [43.6, 39.05], 'r': 1,
         'note': '"The mountains of Ararat" (8:4) is a land, not one peak: Urartu of the Assyrian records, a kingdom of the highlands '
                 'around Lake Van from the 9th to the 6th century BC. Sennacherib\'s sons fled "to the land of Ararat" (2 Kings 19:37), '
                 'and Jeremiah summons "the kingdoms of Ararat, Minni and Ashkenaz" against Babylon (51:27).'},
        {'n': 'Gordyene', 'll': [42.9, 37.6], 'r': 2,
         'note': 'Kardu or Qardu, the mountains south of Lake Van above the Tigris, where the Aramaic and Syriac translations and Berossus put the ark.'},
        {'n': 'Assyria', 'll': [43.4, 36.1], 'r': 2, 'note': 'The Assyrian heartland on the Tigris, whose records name Urartu, Nimush and Kardu.'},
        {'n': 'Media', 'll': [48.6, 35.3], 'r': 2, 'note': 'North-western Iran.'},
        {'n': 'Phrygia', 'll': [30.8, 39.2], 'r': 2, 'note': 'Western Anatolia, home of the Apamea tradition.'},
    ],
    'waterNames': [
        {'n': 'Lake Van', 's': '', 'll': [42.9, 38.62]},
        {'n': 'Lake Urmia', 's': '', 'll': [45.45, 37.65]},
        {'n': 'Black Sea', 's': '', 'll': [36.0, 41.4]},
        {'n': 'Caspian Sea', 's': '', 'll': [51.0, 40.0]},
        {'n': 'The Great Sea', 's': '(Mediterranean)', 'll': [31.6, 35.2]},
        {'n': 'Euphrates', 's': '', 'll': [39.6, 36.0]},
        {'n': 'Tigris', 's': '', 'll': [43.0, 35.2]},
    ],
    'groups': [
        {'id': 'sites', 'name': 'Proposed resting places of the ark', 'color': '#a0443a', 'places': SITES},
        {'id': 'other', 'name': 'In the Babylonian flood story', 'color': 'var(--dbm-city)', 'places': OTHER},
    ],
    'notes': [
        {'h': 'The mountains of Ararat', 'p': [
            'Genesis does not name a mountain. The ark came to rest "on the mountains of Ararat" (8:4), and the tops of the mountains '
            'appeared only two and a half months later (8:5). Ararat is the Hebrew name of Urartu, the highland kingdom around Lake Van, '
            'so the text points to a region rather than a single summit.',
            'Over the centuries Jews, Christians and Muslims have pointed to different peaks within or near that region. '
            'The oldest named tradition is Mount Judi (Qardu) south of Lake Van; Mount Ararat, the great volcano to the north, became the '
            'usual site in the Middle Ages. The Book of Jubilees names "Lubar, one of the mountains of Ararat" (5:28), which has not been identified.']},
        {'h': 'How to read this map', 'p': [
            'Red marks are places proposed for the ark\'s landing, with their names today. Faint marks are later or weakly supported proposals. '
            'The black mark is the landing place in the Babylonian flood story, for comparison. Tap a mark for its history.']},
    ],
    'sources': 'Scripture: Berean Standard Bible (public domain). Traditions: Josephus, Antiquities 1.90–95; Targum Onkelos and the Peshitta on '
               'Genesis 8:4; Quran 11:44; Jubilees 5:28; Sibylline Oracles 1; Gilgamesh XI. Summits: Wikipedia and GeoNames. '
               'Seas, lakes and rivers: Natural Earth (public domain). Terrain: Terrain Tiles on AWS Open Data (Mapzen). Map engine: MapLibre GL.',
}


def main():
    with open(os.path.join(MAPS, MAP['id'] + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(MAP, fh, ensure_ascii=False, indent=1)
    idx_path = os.path.join(MAPS, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    idx['maps'] = [e for e in idx['maps'] if e['id'] != MAP['id']]
    idx['maps'].append({'id': MAP['id'], 'title': MAP['title'], 'ref': MAP['ref'], 'book': 'GEN', 'c': 8, 'v': 4,
                        'links': MAP['links'], 'aliases': MAP['aliases'], 'range': MAP['range']})
    order = ['GEN', 'EXO', 'JOS', 'JDG', 'MAT']
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('gen-8-ararat written')


if __name__ == '__main__':
    main()
