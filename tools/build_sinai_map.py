#!/usr/bin/env python3
"""Exodus 19: the main places proposed for Mount Sinai (Horeb).

    python3 tools/build_sinai_map.py && python3 tools/check_maps.py

Writes data/maps/exo-19-sinai.json and its entry in data/maps/index.json.
Coordinates: OpenBible.info Bible Geocoding Data (CC BY 4.0), its candidates for Mount Sinai;
Jebel al-Madhbah and Hala-'l Badr from Wikipedia.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')
OB = 'abfba2a/mount-sinai'


def mt(n, ll, c, m, note, u=OB):
    d = {'n': n, 'll': ll, 'c': c, 'm': m, 'k': 'mount', 'note': note}
    if u:
        d['u'] = u
    return d


SOUTH = [
    mt('Jebel Musa', [33.97333, 28.53972], 2, '"Mountain of Moses," southern Sinai, Egypt · 2,285 m',
       'The traditional Mount Sinai. Christian monks lived here by the 4th century; Egeria visited in about 383, and Justinian built '
       'the fortified Monastery of St Catherine at its foot in the 6th century. Bedouin and Muslim tradition also call it the mountain of Moses. '
       'Its supporters point to the wide plain of er-Raha below and to the oasis water nearby.'),
    mt('Ras es-Safsafa', [33.96722, 28.55556], 1, '"Willow Peak," the northern end of the Jebel Musa massif',
       'Edward Robinson (1838) and others preferred this northern peak of the same massif, because it rises straight above the plain of er-Raha, '
       'where a great camp could see the mountain and "stand at the foot of the mountain" (19:17).'),
    mt('Jebel Katherina', [33.95528, 28.51083], 1, 'Mount St Catherine, beside Jebel Musa · 2,629 m',
       'The highest mountain in Egypt, just south-west of Jebel Musa. Some have preferred it because Josephus calls Sinai the highest mountain '
       'of the region (Antiquities 3.76).'),
    mt('Jebel Serbal', [33.65167, 28.64639], 1, 'above the Feiran oasis, southern Sinai · 2,070 m',
       'An early Christian candidate: the monks of the Feiran oasis below (traditionally Rephidim) venerated it in the 4th–5th centuries, before '
       'Jebel Musa prevailed. Richard Lepsius argued for it in 1845.'),
]
NORTH = [
    mt('Jebel Sin Bishar', [32.961, 29.671], 1, 'Wadi Sudr, west-central Sinai · 618 m',
       'Proposed by Menashe Har-El of Tel Aviv University (1983): about three days\' journey from Egypt (3:18; 5:3), with water and pasture nearby, '
       'and a name he read as preserving "Sinai."'),
    mt('Jebel Helal', [34.02889, 30.65306], 0, 'Gebel Halal, northern Sinai · 910 m',
       'A northern proposal, close to Kadesh-barnea and the road from Egypt to Edom, favoured by those who place the whole wilderness journey in the north.'),
    mt('Jebel Yeleq', [33.52306, 30.35111], 0, 'north-central Sinai', 'Another northern proposal, on the way from Egypt toward Kadesh.'),
    mt('Jebel Hashem el-Tarif', [34.63341, 29.66922], 0, 'about 30 km west of Eilat, Sinai',
       'Proposed for its position on the road from Egypt to the head of the Gulf of Aqaba, near Midian.'),
]
NEGEV = [
    mt('Har Karkom', [34.75, 30.28333], 1, 'Jebel Ideid, southern Negev, Israel · 847 m',
       'Proposed by the archaeologist Emmanuel Anati, who recorded some 40,000 rock engravings and many cult sites on the mountain. '
       'Most of the sites date to the 3rd millennium BC, which would require a much earlier date for the Exodus; most scholars have not followed him.',
       u='m0cc900/har-karkom'),
    mt('Jebel al-Madhbah', [35.4469, 30.3218], 0, '"Mountain of the Altar," Petra, Jordan',
       'Ditlef Nielsen (1927) proposed this mountain of the high place at Petra, in Edom, linking it with the songs that bring God "from Seir" '
       'and "from Mount Paran" (Deuteronomy 33:2; Judges 5:4).', u=None),
]
ARABIA = [
    mt('Jabal al-Lawz', [35.30583, 28.65417], 1, 'north-western Saudi Arabia (ancient Midian) · 2,580 m',
       'Promoted since the 1980s by Ron Wyatt, Bob Cornuke and Lennart Möller, often with Jabal Maqla, the dark-topped peak 7 km south. '
       'They point to Moses\' flight to Midian (2:15; 3:1) and Paul\'s "Mount Sinai in Arabia" (Galatians 4:25). Critics such as James Hoffmeier '
       'note that the stone structures there are common Arabian cairns and enclosures of uncertain date.'),
    mt('Hala-\'l Badr', [37.235, 27.25], 1, 'Hallat al-Badr, a volcano on Jabal Thadra, Saudi Arabia',
       'The volcano theory: fire, smoke and quaking (19:16–18) read as an eruption. Alois Musil argued for this volcano in Midian in the 1920s, '
       'and Colin Humphreys (2003) followed him. There is no archaeological evidence either way.', u=None),
]
OTHER = [
    {'n': 'Rameses', 'll': [31.83422, 30.79937], 'c': 2, 'm': 'Qantir, the eastern Delta', 'note': 'Where the Exodus began (12:37).', 'u': 'a079b21/rameses'},
    {'n': 'Rephidim', 'll': [33.62, 28.70], 'c': 0, 'm': 'Wadi Feiran? (traditional)', 'note': 'The last camp before Sinai, where Moses struck the rock and Israel fought Amalek (17; 19:2). Tradition places it at the Feiran oasis.'},
    {'n': 'Serabit el-Khadim', 'll': [33.4597, 29.0378], 'c': 2, 'm': 'Serabit el-Khadim, Sinai', 'note': 'Egyptian turquoise mines and a temple of Hathor, where the earliest alphabetic inscriptions (Proto-Sinaitic, about 1800 BC) were found. Its road is one reason some keep the Israelites away from western Sinai.'},
    {'n': 'Kadesh-barnea', 'll': [34.42222, 30.64833], 'c': 2, 'm': 'Ain el-Qudeirat', 'note': 'Israel\'s base in the wilderness after Sinai (Numbers 13–14; 20), "eleven days\' journey from Horeb by the way of Mount Seir" (Deuteronomy 1:2).', 'u': 'ac2cef0/kadesh-barnea'},
    {'n': 'Ezion-geber', 'll': [35.0, 29.53], 'c': 1, 'm': 'near Aqaba and Eilat', 'note': 'On the Gulf of Aqaba (Numbers 33:35; 1 Kings 9:26). The gulf separates Sinai from Midian.'},
]

COLORS = {'south': '#a0443a', 'north': '#3f6aa8', 'negev': '#7a6a2e', 'arabia': '#7a4f8c'}

MAP = {
    'id': 'exo-19-sinai', 'title': 'Where Was Mount Sinai?', 'ref': 'Exodus 19',
    'anchor': {'book': 'EXO', 'c': 19, 'v': 1}, 'range': [1, 25],
    'also': [{'c': 3, 'v': 1, 'range': [1, 12]}, {'c': 24, 'v': 1, 'range': [1, 18]}],
    'siteLabel': 'Today', 'placesName': 'Exodus', 'groupsLabel': 'Proposed sites',
    'bounds': [[31.8, 26.9], [37.9, 31.2]], 'groupLabelZoom': 7.0,
    'links': ['Mount Sinai', 'Wilderness of Sinai', 'Sinai', 'Horeb', 'Midian'],
    'aliases': {'Mount Sinai': 'Sinai', 'Wilderness of Sinai': 'Sinai', 'Horeb': 'Sinai'},
    'regions': [
        {'n': 'Sinai', 'label': 'Sinai', 'll': [33.75, 29.35], 'r': 1,
         'note': 'Mount Sinai, also called Horeb, "the mountain of God" (3:1). The Bible gives its place only through the journey: '
                 'about three days\' journey into the wilderness from Egypt (3:18), three months after leaving Egypt (19:1), and eleven days from '
                 'Kadesh-barnea (Deuteronomy 1:2). Where it stood is debated; the marks on this map are the main proposals. '
                 'The peninsula itself was named after the traditional site.'},
        {'n': 'Midian', 'll': [36.0, 28.0], 'r': 1,
         'note': 'The land east of the Gulf of Aqaba, where Moses fled and kept Jethro\'s flocks (2:15; 3:1). Some place Sinai here because of the '
                 'flight to Midian and Paul\'s words, "Mount Sinai in Arabia" (Galatians 4:25).'},
        {'n': 'Egypt', 'll': [31.95, 29.6], 'r': 1, 'note': 'The land Israel left (12:37–41).'},
        {'n': 'Edom', 'll': [35.55, 30.5], 'r': 2, 'note': 'Mount Seir. Deuteronomy 33:2 and Judges 5:4 say the LORD came "from Seir."'},
        {'n': 'Wilderness of Paran', 'label': 'Wilderness\nof Paran', 'll': [34.4, 30.1], 'r': 2, 'note': 'The wilderness of the north and centre of Sinai (Numbers 10:12).'},
        {'n': 'Negev', 'll': [34.85, 30.9], 'r': 2, 'note': 'The dry south of the land of Canaan.'},
    ],
    'waterNames': [
        {'n': 'Red Sea', 's': '', 'll': [35.2, 27.2]},
        {'n': 'Gulf of Suez', 's': '', 'll': [32.95, 29.0]},
        {'n': 'Gulf of Aqaba', 's': '', 'll': [34.72, 28.85]},
        {'n': 'The Great Sea', 's': '(Mediterranean)', 'll': [33.0, 31.45]},
    ],
    'groups': [
        {'id': 'south', 'name': 'Southern Sinai (the traditional region)', 'short': 'Southern Sinai', 'color': COLORS['south'], 'places': SOUTH},
        {'id': 'north', 'name': 'Central and northern Sinai', 'short': 'Northern Sinai', 'color': COLORS['north'], 'places': NORTH},
        {'id': 'negev', 'name': 'The Negev and Edom', 'short': 'Negev and Edom', 'color': COLORS['negev'], 'places': NEGEV},
        {'id': 'arabia', 'name': 'Arabia (Midian)', 'short': 'Arabia', 'color': COLORS['arabia'], 'places': ARABIA},
        {'id': 'other', 'name': 'Other places', 'color': 'var(--dbm-city)', 'places': OTHER},
    ],
    'notes': [
        {'h': 'Where was the mountain?', 'p': [
            'The Bible never says where Mount Sinai is in terms of later places. The mountain, also called Horeb, is reached by a journey '
            'from Egypt through the wilderness, and every proposal rests on how that journey (Exodus 13–19; Numbers 33) and the land of Midian are read.',
            'The traditional site, Jebel Musa in southern Sinai, has been honoured since at least the 4th century. Scholars who place the crossing '
            'and the wilderness in the north prefer peaks such as Jebel Sin Bishar or Jebel Helal; Har Karkom in the Negev rests on its ancient cult sites; '
            'and those who stress Midian and Paul\'s "Mount Sinai in Arabia" (Galatians 4:25) look east of the Gulf of Aqaba, to Jabal al-Lawz or a volcano '
            'such as Hala-\'l Badr. Israel Knohl has even proposed Mount Hermon. None of the sites has evidence that settles the question.']},
        {'h': 'How to read this map', 'p': [
            'The marks are grouped by region; tap one for who proposed it and why. Faint marks are proposals with little support. '
            'The black dots are other places of the Exodus for orientation.']},
    ],
    'sources': 'Scripture: Berean Standard Bible (public domain). Places and candidates: OpenBible.info Bible Geocoding Data (CC BY 4.0); '
               'Jebel al-Madhbah and Hala-\'l Badr from Wikipedia. Sea and Red Sea coasts: Natural Earth (public domain). '
               'Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap contributors. Imagery © Esri. Map engine: MapLibre GL.',
}


def main():
    with open(os.path.join(MAPS, MAP['id'] + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(MAP, fh, ensure_ascii=False, indent=1)
    idx_path = os.path.join(MAPS, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    idx['maps'] = [e for e in idx['maps'] if e['id'] != MAP['id']]
    idx['maps'].append({'id': MAP['id'], 'title': MAP['title'], 'ref': MAP['ref'], 'book': 'EXO', 'c': 19, 'v': 1,
                        'links': MAP['links'], 'aliases': MAP['aliases'], 'range': MAP['range'], 'also': MAP['also']})
    order = ['GEN', 'EXO', 'JOS', 'JDG', 'MAT']
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(MAP['id'], 'written')


if __name__ == '__main__':
    main()
