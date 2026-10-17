#!/usr/bin/env python3
"""Book maps: one general map per book, so every place named anywhere in the book can be tapped
in the text, even in chapters that have no map of their own.

    python3 tools/build_book_maps.py && python3 tools/check_maps.py

A book map has a button at the book's first verse and `"bookwide": true` in its index entry, so
the reader links its place names in every chapter of the book (a chapter's own map keeps the names
it links). The Gospels share one map of the land in the first century: the places are sorted into
"named in this book", "named elsewhere in the Gospels", Herod's building works, and other sites of
the period, and the book's own names are found in its BSB text. Add a Gospel to BOOKS to give it
the same map.
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')
NAMES = {'MAT': 'Matthew', 'MRK': 'Mark', 'LUK': 'Luke', 'JHN': 'John'}

# ── Regions of the land in the first century (label points; r = label rank) ──
# `hide`: not labelled on the map (the map already shows it), but tappable in the text.
REGIONS = [
    {'n': 'Galilee', 'll': [35.33, 32.86], 'r': 1, 'aka': ['Galilean'],
     'note': 'Ruled by Herod Antipas, son of Herod the Great, as tetrarch from 4 BC to AD 39: first from Sepphoris, then from his new capital Tiberias. '
             'A thickly settled Jewish region of farming villages and fishing towns. Most of Jesus\' ministry in Matthew takes place here (4:12–18:35).'},
    {'n': 'Samaria', 'll': [35.2, 32.3], 'r': 1, 'aka': ['Samaritans'],
     'note': 'Between Galilee and Judea, the land of the Samaritans, who worshipped on Mount Gerizim. Governed with Judea, first by Archelaus, then by Roman prefects. '
             'Jesus sends the Twelve "not into any town of the Samaritans" (Matthew 10:5); in John 4 He speaks with a Samaritan woman at Sychar.'},
    {'n': 'Judea', 'll': [34.98, 31.6], 'r': 1,
     'note': 'The heartland around Jerusalem. On Herod the Great\'s death (4 BC) it passed to his son Archelaus (Matthew 2:22); from AD 6 it was a Roman prefecture, '
             'governed by Pontius Pilate from AD 26 to 36, while the high priest and the council ran the Temple and much of daily life.'},
    {'n': 'Idumea', 'll': [34.92, 31.27], 'r': 1,
     'note': 'The southern hill country around Hebron and Marisa, settled by Edomites after the Exile and brought into Judaism by John Hyrcanus (about 125 BC). '
             'Herod the Great\'s family came from here. People came from Idumea to hear Jesus (Mark 3:8).'},
    {'n': 'Perea', 'll': [35.7, 31.95], 'r': 1,
     'note': '"Beyond the Jordan" (Matthew 4:25; 19:1): the Jewish land east of the river, ruled together with Galilee by Herod Antipas. '
             'Its southern fortress was Machaerus, where Josephus says John the Baptist was put to death.'},
    {'n': 'Decapolis', 'll': [35.98, 32.47], 'r': 1,
     'note': '"The Ten Cities" (Matthew 4:25): Greek cities such as Scythopolis, Gadara, Hippos, Pella and Gerasa, self-governing under the Roman province of Syria. '
             'Mostly Gentile, with temples, theatres and coinage of their own.'},
    {'n': 'Gaulanitis', 'll': [35.76, 33.0], 'r': 2,
     'note': 'The Golan. Part of the tetrarchy of Philip, Herod\'s son (4 BC–AD 34), who rebuilt Bethsaida as Julias and Paneas as Caesarea Philippi. '
             'Jewish towns such as Gamla stood beside Gentile ones.'},
    {'n': 'Batanea', 'll': [36.12, 32.74], 'r': 2,
     'note': 'Biblical Bashan. Part of Philip\'s tetrarchy; Herod the Great settled Babylonian Jews here to guard the road to Babylon.'},
    {'n': 'Trachonitis', 'll': [36.45, 33.08], 'r': 2,
     'note': 'The rough lava country south of Damascus, once a haunt of bandits. Luke 3:1 names it as part of Philip\'s tetrarchy.'},
    {'n': 'Auranitis', 'll': [36.52, 32.58], 'r': 2,
     'note': 'The Hauran, the fertile volcanic plateau east of Batanea; part of Philip\'s tetrarchy.'},
    {'n': 'Iturea', 'll': [35.88, 33.55], 'r': 2,
     'note': 'Land of the Itureans, an Arab people of the Lebanon and Mount Hermon. Luke 3:1 lists it with Trachonitis under Philip.'},
    {'n': 'Phoenicia', 'll': [35.33, 33.4], 'r': 2,
     'note': 'The coastal cities of Tyre and Sidon (Matthew 11:21; 15:21): wealthy, Gentile, and part of the province of Syria. '
             'Galilee sold them food (compare Acts 12:20), and the Temple tax was paid in Tyrian silver shekels.'},
    {'n': 'Syria', 'll': [36.5, 33.92], 'r': 2,
     'note': 'The Roman province, governed from Antioch by a legate with legions; the prefect of Judea answered to him. "News about Him spread all over Syria" (Matthew 4:24).'},
    {'n': 'Nabatea', 'll': [35.85, 30.95], 'r': 2,
     'note': 'The Arab kingdom of Aretas IV (9 BC–AD 40), with its capital at Petra. Herod Antipas divorced Aretas\' daughter to marry Herodias (Matthew 14:3–4), '
             'and Aretas later defeated him in battle (Josephus, Antiquities 18.109–119).'},
    {'n': 'Wilderness of Judea', 'label': 'Wilderness\nof Judea', 'll': [35.33, 31.5], 'r': 3,
     'note': 'The dry hills dropping east from Jerusalem to the Dead Sea, where John the Baptist preached (Matthew 3:1).'},
    # tappable but not labelled
    {'n': 'Sea of Galilee', 'll': [35.59, 32.82], 'hide': True, 'z': 10.4, 'aka': ['Lake of Gennesaret', 'Sea of Tiberias'],
     'note': 'Also "the lake of Gennesaret" (Luke 5:1) and "the Sea of Tiberias" (John 6:1); Hebrew Kinneret. About 21 km long and 12 km wide, 210 m below sea level, '
             'ringed by fishing towns: Capernaum, Bethsaida, Magdala, Tiberias.'},
    {'n': 'Jordan', 'll': [35.56, 32.15], 'hide': True, 'z': 8.6,
     'note': 'The river from the Sea of Galilee down to the Dead Sea, about 105 km as the crow flies. John baptized in it (Matthew 3:6), probably near Jericho, '
             'where tradition places Jesus\' baptism (Qasr al-Yahud and al-Maghtas).'},
    {'n': 'Zebulun', 'll': [35.27, 32.75], 'hide': True, 'z': 9.2,
     'note': 'The tribal land of Zebulun in Lower Galilee, around Nazareth. Matthew 4:15 quotes Isaiah 9:1: "Land of Zebulun and land of Naphtali… Galilee of the Gentiles."'},
    {'n': 'Naphtali', 'll': [35.5, 33.02], 'hide': True, 'z': 9.2,
     'note': 'The tribal land of Naphtali, west of the Sea of Galilee and north into Upper Galilee; Capernaum lay within it (Matthew 4:13).'},
    {'n': 'Egypt', 'll': [32.4, 30.85], 'hide': True, 'z': 7,
     'note': 'The Nile Delta lay about ten days\' walk from Bethlehem by the coast road. Large Jewish communities lived in Alexandria and Leontopolis, '
             'which made Egypt the natural refuge for Joseph, Mary and the child (Matthew 2:13–15).'},
]

# ── Places (OpenBible.info coordinates where it has the site; otherwise standard identifications) ──
# g: 'gospels' (named in another Gospel; `ref` gives where), 'herod' (Herod's cities, palaces and
# fortresses), 'other'. Places named in the map's own book move to the first group automatically.
PLACES = [
    # named in Matthew (and often elsewhere)
    dict(n='Bethlehem', ll=[35.20764, 31.70431], c=2, m='Bethlehem', u='a112427/bethlehem-1', ref='Luke 2:4',
         note='The town of David, about 9 km south of Jerusalem, where Jesus was born (Matthew 2:1; Micah 5:2). The Church of the Nativity stands over the cave venerated since the 2nd century.'),
    dict(n='Jerusalem', ll=[35.23417, 31.77667], c=2, m='Jerusalem', u='a15257a/jerusalem', ref='Luke 2:22',
         note='The holy city and its Temple, rebuilt on a vast scale by Herod the Great from about 20 BC. Pilgrims came up for Passover, Shavuot and Sukkot.'),
    dict(n='Ramah', ll=[35.23161, 31.85434], c=2, m='er-Ram', u='a6d57ed/ramah-1',
         note='"A voice is heard in Ramah… Rachel weeping for her children" (Matthew 2:18; Jeremiah 31:15). Ramah of Benjamin, north of Jerusalem, near where Jeremiah\'s exiles were gathered.'),
    dict(n='Nazareth', ll=[35.29769, 32.70214], c=2, m='Nazareth', u='af5884f/nazareth', aka=['Nazarene'], ref='Luke 1:26',
         note='A small Jewish village in the hills of Lower Galilee, about 6 km from Sepphoris. Jesus grew up here (Matthew 2:23).'),
    dict(n='Capernaum', ll=[35.575, 32.88111], c=2, m='Tell Hum', u='af2161c/capernaum', ref='Mark 1:21',
         note='A fishing town on the north shore, by the border of Antipas\' and Philip\'s lands (hence a tax office, 9:9). Jesus made it His base, "His own town" (4:13; 9:1). '
              'The white synagogue seen today is later, built on the black basalt foundations of an earlier one.'),
    dict(n='Chorazin', ll=[35.56389, 32.91139], c=2, m='Khirbet Karraza', u='a593a48/chorazin', ref='Luke 10:13',
         note='A town in the basalt hills above Capernaum, reproached with Bethsaida for not repenting (Matthew 11:21).'),
    dict(n='Bethsaida', ll=[35.63096, 32.91038], c=1, m='et-Tell (or el-Araj)', u='a91b732/bethsaida-1', ref='John 1:44',
         note='"House of fishing," home of Peter, Andrew and Philip (John 1:44), rebuilt by Philip as Julias. Its site is debated: et-Tell or el-Araj, on the shore below.'),
    dict(n='Gennesaret', ll=[35.53, 32.862], c=2, m='the plain of Ginosar',
         note='"The land of Gennesaret" (Matthew 14:34): the fertile plain on the north-west shore, praised by Josephus for its fruit.'),
    dict(n='Magadan', ll=[35.5166, 32.8247], c=1, m='Migdal (Magdala)?',
         note='Jesus went "to the region of Magadan" (Matthew 15:39); some manuscripts read Magdala. Magdala (Migdal Nunya, Greek Tarichaea), the fish-salting town of Mary Magdalene, '
              'is the usual identification; a synagogue of Jesus\' time was found there in 2009.'),
    dict(n='Gadara', ll=[35.67935, 32.656], c=2, m='Umm Qais', u='afed46a/gadara', aka=['Gadarenes'],
         note='A city of the Decapolis on the heights south-east of the lake. "The region of the Gadarenes" (Matthew 8:28) was Gadara\'s territory, which reached the shore; '
              'Mark and Luke say Gerasenes, and tradition places the event at Kursi on the east shore.'),
    dict(n='Tyre', ll=[35.19611, 33.27083], c=2, m='Sur, Lebanon', u='a160272/tyre', ref='Mark 7:24',
         note='The great Phoenician port on its former island. Jesus withdrew "to the region of Tyre and Sidon" (Matthew 15:21).'),
    dict(n='Sidon', ll=[35.37194, 33.56099], c=2, m='Saida, Lebanon', u='a98e4d7/sidon', ref='Mark 7:31',
         note='The older Phoenician port, 35 km north of Tyre.'),
    dict(n='Caesarea Philippi', ll=[35.69333, 33.24611], c=2, m='Banias', u='ab7bf48/caesarea-philippi', ref='Mark 8:27',
         note='Philip\'s capital at the springs of the Jordan below Hermon, by the cave shrine of Pan. Here Peter confesses Jesus as the Messiah (Matthew 16:13–20).'),
    dict(n='Jericho', ll=[35.43624, 31.85187], c=2, m='Tulul Abu el-Alayiq', u='aaf03fa/jericho-2', ref='Luke 19:1',
         note='New Testament Jericho, south of the old mound, with Herod\'s winter palaces by Wadi Qelt. Pilgrims from Galilee passed through on the way up to Jerusalem (Matthew 20:29).'),
    dict(n='Bethphage', ll=[35.25084, 31.77762], c=1, m='et-Tur', u='abff59d/bethphage', ref='Mark 11:1',
         note='A village on the Mount of Olives, where the disciples fetched the donkey (Matthew 21:1).'),
    dict(n='Bethany', ll=[35.2559, 31.77166], c=2, m='al-Eizariya', u='a4f35bc/bethany-1', ref='John 11:1',
         note='Village on the east slope of the Mount of Olives, home of Mary, Martha and Lazarus. Jesus stayed here during the last week (Matthew 21:17; 26:6).'),
    dict(n='Mount of Olives', ll=[35.24569, 31.77795], c=2, m='', u='ac2c4c5/mount-of-olives', ref='Luke 19:29',
         note='The ridge east of the Temple, across the Kidron. The triumphal entry begins here (21:1); here Jesus speaks of the end of the age (24:3).'),
    dict(n='Gethsemane', ll=[35.2398, 31.7795], c=1, m='by the Church of All Nations', ref='Mark 14:32',
         note='"Oil press": an olive grove at the foot of the Mount of Olives, where Jesus prayed and was arrested (Matthew 26:36–56).'),
    dict(n='Golgotha', ll=[35.22975, 31.77844], c=1, m='Church of the Holy Sepulchre', u='a631d35/golgotha', ref='John 19:17',
         note='"The place of the skull" (Matthew 27:33), outside the city wall of that time. The Church of the Holy Sepulchre marks the site venerated since at least the 4th century.'),
    dict(n='Field of Blood', ll=[35.2316, 31.7683], c=1, m='Akeldama, Hinnom Valley',
         note='The potter\'s field bought with Judas\' thirty pieces of silver as a burial ground for foreigners (Matthew 27:7–8; Acts 1:19). Tradition places it in the Hinnom Valley, where rock-cut tombs of the period survive.'),
    dict(n='Arimathea', ll=[35.01944, 32.02806], c=1, m='Rantis?', u='af3d9fc/arimathea', ref='John 19:38',
         note='Home town of Joseph, the rich disciple who buried Jesus in his own new tomb (Matthew 27:57–60). Often identified with Ramathaim, Samuel\'s town.'),
    dict(n='Sodom', ll=[35.535, 31.252], c=0, m='Bab edh-Dhra? (site disputed)', u='a0aa664/sodom',
         note='Named by Jesus as a byword for judgment (Matthew 10:15; 11:23–24). The site is debated: Bab edh-Dhra by the south of the Dead Sea, or Tall el-Hammam north of it.'),
    dict(n='Gomorrah', ll=[35.565, 31.135], c=0, m='Numeira? (site disputed)', u='aa572e2/gomorrah',
         note='Paired with Sodom (Matthew 10:15). Numeira, south of Bab edh-Dhra, is one proposal.'),
    # named in the other Gospels
    dict(n='Cana', ll=[35.30269, 32.8222], c=2, m='Khirbet Qana', u='a031bda/cana', g='gospels', ref='John 2:1',
         note='Where Jesus turned water into wine at a wedding (John 2:1–11). Khirbet Qana, excavated since 1998, is the likeliest site; Kafr Kanna is the traditional one.'),
    dict(n='Nain', ll=[35.35014, 32.63069], c=2, m='Nein', u='aee679c/nain', g='gospels', ref='Luke 7:11',
         note='Where Jesus raised a widow\'s son (Luke 7:11–17), on the slope of the Hill of Moreh.'),
    dict(n='Tiberias', ll=[35.54417, 32.77361], c=2, m='Tiberias', u='ac9adc9/tiberias', g='gospels', ref='John 6:23',
         note='Herod Antipas\' new capital, founded about AD 20 and named for the emperor Tiberius. Built over tombs, it was shunned at first by observant Jews; the Gospels never show Jesus there.'),
    dict(n='Sychar', ll=[35.28897, 32.21776], c=1, m='Askar, by Jacob\'s Well', u='a27b472/sychar', g='gospels', ref='John 4:5',
         note='A Samaritan town by Jacob\'s Well, below Mount Gerizim, where Jesus spoke with the Samaritan woman (John 4).'),
    dict(n='Mount Gerizim', ll=[35.27278, 32.19944], c=2, m='Har Brakha, Nablus', u='a30e967/mount-gerizim', g='gospels', ref='John 4:20 ("this mountain")',
         note='The Samaritans\' holy mountain. Their temple there was destroyed by John Hyrcanus (about 111 BC), but they still worshipped on it (John 4:20).'),
    dict(n='Aenon', ll=[35.52821, 32.38152], c=1, m='near Salim?', u='a112fe3/aenon', g='gospels', ref='John 3:23',
         note='"Springs": John baptized at Aenon near Salim "because there was plenty of water there" (John 3:23).'),
    dict(n='Bethany beyond the Jordan', ll=[35.5536, 31.8375], c=1, m='al-Maghtas (Wadi al-Kharrar)', g='gospels', ref='John 1:28',
         note='Where John was baptizing (John 1:28). The traditional baptism site is at al-Maghtas on the east bank and Qasr al-Yahud opposite, near Jericho.'),
    dict(n='Gerasa', ll=[35.8914, 32.27228], c=2, m='Jerash', u='ada6b64/gerasa', g='gospels', ref='Mark 5:1 ("Gerasenes")',
         note='A great Decapolis city, 55 km from the lake; Mark and Luke name the swine episode for "the region of the Gerasenes." Its colonnaded streets are among the best preserved Roman ruins.'),
    dict(n='Emmaus', ll=[35.16419, 31.79289], c=1, m='Motza (Qalunya)?', u='ae7274b/emmaus', g='gospels', ref='Luke 24:13',
         note='The village the two disciples were walking to when the risen Jesus joined them (Luke 24:13). Several sites are proposed: Motza, Emmaus Nicopolis, el-Qubeibeh, Abu Ghosh.'),
    # Herod's cities, palaces and fortresses
    dict(n='Sepphoris', ll=[35.2795, 32.7529], c=2, m='Tzippori', g='herod',
         note='The capital of Galilee, rebuilt by Herod Antipas as "the ornament of all Galilee" (Josephus) after the Romans burned it in 4 BC. Only 6 km from Nazareth; it is never named in the New Testament.'),
    dict(n='Caesarea', ll=[34.89167, 32.5], c=2, m='Caesarea Maritima', u='a58735e/caesarea', g='herod',
         note='Herod\'s great harbour city (22–10 BC), seat of the Roman governors of Judea. A stone found in its theatre in 1961 names "Pontius Pilate, prefect of Judea." Peter and Paul came here (Acts 10; 23).'),
    dict(n='Sebaste', ll=[35.1925, 32.2764], c=2, m='Sebastia', g='herod',
         note='Old Samaria, refounded by Herod as Sebaste in honour of Augustus (Greek Sebastos), with a temple to the emperor.'),
    dict(n='Herodium', ll=[35.2414, 31.6659], c=2, m='Herodion', g='herod',
         note='Herod\'s palace-fortress on an artificial cone, visible from Bethlehem 5 km away. His tomb was found on its slope in 2007.'),
    dict(n='Masada', ll=[35.3536, 31.3156], c=2, m='Masada', g='herod',
         note='Herod\'s desert fortress-palace above the Dead Sea; the last Jewish stronghold against Rome, taken in AD 73 or 74.'),
    dict(n='Machaerus', ll=[35.6264, 31.5603], c=2, m='Mukawir, Jordan', g='herod',
         note='Herod\'s fortress in Perea, held by Antipas. Josephus says John the Baptist was imprisoned and executed here (Antiquities 18.119; compare Matthew 14:3–12).'),
    # other sites of the period
    dict(n='Magdala', ll=[35.5166, 32.8247], c=2, m='Migdal', g='other', skip_if='Magadan',
         note='The fish-salting town of Mary Magdalene. A synagogue of Jesus\' time was found here in 2009.'),
    dict(n='Mount Tabor', ll=[35.3906, 32.6869], c=1, m='Har Tavor', g='other',
         note='Traditional Mount of the Transfiguration ("a high mountain," Matthew 17:1) since the 4th century. Mount Hermon, nearer Caesarea Philippi, is the other main proposal.'),
    dict(n='Mount Hermon', ll=[35.857, 33.416], c=2, m='', g='other',
         note='The great snow mountain above Caesarea Philippi, about 2,800 m. Many scholars place the Transfiguration on its slopes (Matthew 17:1).'),
    dict(n='Mount of Beatitudes', ll=[35.5569, 32.8811], c=0, m='above Tabgha (traditional)', g='other',
         note='The hillside above Capernaum where tradition places the Sermon on the Mount ("He went up on the mountain," Matthew 5:1).'),
    dict(n='Tabgha', ll=[35.5487, 32.8734], c=0, m='Heptapegon (traditional)', g='other',
         note='"Seven springs," near Capernaum: the traditional site of the feeding of the five thousand (Matthew 14:13–21), with a Byzantine mosaic of loaves and fishes.'),
    dict(n='Kursi', ll=[35.6506, 32.8256], c=0, m='Kursi (traditional)', g='other',
         note='On the east shore, below steep slopes: the traditional site of the swine rushing into the lake (Matthew 8:28–34), with a Byzantine monastery.'),
    dict(n='Gamla', ll=[35.7392, 32.9028], c=2, m='Gamla', g='other',
         note='A Jewish town on a camel-shaped ridge in the Golan, with one of the oldest synagogues known. It fell to Vespasian in AD 67.'),
    dict(n='Hippos', ll=[35.6593, 32.7783], c=2, m='Sussita', g='other',
         note='A Decapolis city on a hill facing Tiberias across the lake; perhaps "a city set on a hill" (Matthew 5:14).'),
    dict(n='Scythopolis', ll=[35.5025, 32.5045], c=2, m='Beit She\'an', g='other',
         note='Old Beth-shan, the leading city of the Decapolis and the only one west of the Jordan.'),
    dict(n='Pella', ll=[35.6167, 32.45], c=2, m='Tabaqat Fahl', g='other',
         note='A Decapolis city where, according to Eusebius, the Jerusalem church took refuge before the Romans besieged the city in AD 70.'),
    dict(n='Qumran', ll=[35.4589, 31.7411], c=2, m='Khirbet Qumran', g='other',
         note='The settlement by the caves where the Dead Sea Scrolls were found (1947–56), usually linked with the Essenes.'),
    dict(n='Joppa', ll=[34.75304, 32.05448], c=2, m='Jaffa', u='ae023a9/joppa', g='other',
         note='Jerusalem\'s old port, where Peter raised Tabitha and saw the vision of the sheet (Acts 9–10).'),
    dict(n='Lydda', ll=[34.9, 31.95], c=2, m='Lod', u='a2c5cc7/lod', g='other', note='Where Peter healed Aeneas (Acts 9:32–35).'),
    dict(n='Ptolemais', ll=[35.0692, 32.9214], c=2, m='Acre', u='abc2af0/ptolemais', g='other', note='Old Acco, a Gentile port city; Paul stayed a day here (Acts 21:7).'),
    dict(n='Gaza', ll=[34.4644, 31.504], c=2, m='Gaza', u='aa8edd2/gaza', g='other', note='On the road to Egypt, where Philip met the Ethiopian official (Acts 8:26).'),
    dict(n='Damascus', ll=[36.30639, 33.51111], c=2, m='Damascus', u='a69c1d4/damascus', g='other',
         note='The great city of Syria, with many synagogues; Paul was on his way here when he met the risen Jesus (Acts 9).'),
]

GROUPS = [
    ('book', 'Named in {book}', '#a0443a'),
    ('gospels', 'Named elsewhere in the Gospels', 'var(--dbm-city)'),
    ('herod', 'Herod\'s cities, palaces and fortresses', 'var(--dbm-city)'),
    ('other', 'Other places of the time', 'var(--dbm-city)'),
]

WATER = [  # the map's own water labels (the Old Testament maps say "Sea of Kinnereth")
    {'n': 'The Great Sea', 's': '(Mediterranean)', 'll': [34.25, 32.45]},
    {'n': 'Sea of Galilee', 's': '(Kinneret)', 'll': [35.59, 32.83]},
    {'n': 'Salt Sea', 's': '(Dead Sea)', 'll': [35.49, 31.5]},
    {'n': 'Jordan', 's': '', 'll': [35.555, 32.2]},
]


def book_verses(b):
    data = json.load(open(os.path.join(ROOT, 'data', 'bsb', b + '.json'), encoding='utf-8'))
    out = []
    for ci, ch in enumerate(data['chapters'], 1):
        v = 0
        for bl in ch['b']:
            if bl['k'] in ('s1', 's2', 'r', 'd'):
                continue
            for it in bl.get('c', []):
                if isinstance(it, int):
                    v = it
                elif isinstance(it, str):
                    out.append((ci, v, re.sub('<[^>]+>', '', it)))
    return out


ALL_NAMES = sorted({x for r in REGIONS + PLACES for x in [r['n']] + r.get('aka', [])}, key=len, reverse=True)


def first(verses, forms):
    for c, v, t in verses:
        for f in forms:
            for longer in ALL_NAMES:          # "Caesarea" is not named where the text says "Caesarea Philippi"
                if len(longer) > len(f) and f in longer:
                    t = t.replace(longer, '')
            if re.search(r'(?<![A-Za-z\-])' + re.escape(f) + r'(?![A-Za-z]|-[a-z])', t):
                return '%d:%d' % (c, v), f
    return None, None


def build(b):
    name = NAMES[b]
    verses = book_verses(b)
    links, aliases, in_book = [], {}, set()

    def found(n, aka):
        hit = False
        for f in [n] + (aka or []):
            ref, _ = first(verses, [f])
            if ref:
                hit = True
                links.append(f) if f not in links else None
                if f != n:
                    aliases[f] = n
        return hit

    regions = []
    for r in REGIONS:
        d = {k: r[k] for k in ('n', 'label', 'll', 'r', 'hide', 'z', 'note') if k in r}
        found(r['n'], r.get('aka'))
        regions.append(d)
    groups = {g: [] for g, _, _ in GROUPS}
    taken = set()
    for p in PLACES:
        if p.get('skip_if') and p['skip_if'] in taken:
            continue
        ref, _ = first(verses, [p['n']] + p.get('aka', []))
        q = {'n': p['n'], 'll': p['ll'], 'c': p['c'], 'm': p.get('m', '')}
        if p['n'].startswith('Mount') or p['n'] in ('Golgotha',):
            q['k'] = 'mount'                  # drawn as a triangle
        if p.get('u'):
            q['u'] = p['u']
        q['note'] = p['note']
        if ref:
            found(p['n'], p.get('aka'))
            q['f'] = ref
            groups['book'].append(q)
            taken.add(p['n'])
            in_book.add(p['n'])
        else:
            g = p.get('g') or 'gospels'
            if g == 'gospels' and p.get('ref'):
                q['f'] = p['ref']
            groups[g].append(q)
    out_groups = []
    for gid, label, color in GROUPS:
        if groups[gid]:
            g = {'id': gid, 'name': label.format(book=name), 'color': color, 'places': groups[gid]}
            if gid == 'book':
                g['firstNamed'] = True      # popups say "First named in Matthew at 2:1"
            out_groups.append(g)
    mid = b.lower() + '-land'
    title = 'The Land of Israel in the First Century'
    m = {
        'id': mid, 'title': title, 'ref': name,
        'anchor': {'book': b, 'c': 1, 'v': 1}, 'bookwide': True,
        'placesName': name, 'siteLabel': 'Site',
        'bounds': [[34.3, 30.85], [36.75, 33.7]],
        'groupLabelZoom': 7.2, 'groupsLabel': 'Places',
        'regions': regions, 'waterNames': WATER,
        'links': links, 'aliases': aliases,
        'groups': out_groups,
        'alternates': {'for': 'Bethsaida', 'bounds': [[35.6, 32.875], [35.66, 32.925]], 'sites': [{'name': 'el-Araj', 'll': [35.6272, 32.8938]}]},
        'notes': [
            {'h': 'The land in Jesus\' day', 'p': [
                'When Herod the Great died in 4 BC, Augustus divided his kingdom among three sons. Archelaus received Judea, Samaria and Idumea, but was deposed in AD 6, '
                'and Roman prefects governed there from then on (Pontius Pilate, AD 26–36). Herod Antipas ruled Galilee and Perea until AD 39; Philip ruled the lands north-east of the lake '
                '(Gaulanitis, Batanea, Trachonitis, Auranitis) until AD 34. The Greek cities of the Decapolis and the Phoenician coast belonged to the province of Syria.',
                'So a walk from Capernaum to Bethsaida crossed a border, and a journey from Galilee to Jerusalem passed from Antipas\' land into Roman-governed Judea, '
                'through Samaria or down the Jordan valley through Perea.']},
            {'h': 'How to use this map', 'p': [
                'This map opens from any place name in ' + name + ' that has no map of its own in that chapter. The coloured dots show places named in ' + name + ', '
                'places named only in the other Gospels, Herod\'s building works, and other sites of the time; tap a group in the key to show or hide it. '
                'Region names give the political map of about AD 30.']},
        ],
        'sources': 'Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard identifications, as noted for each place. '
                   'Regions after Josephus and the standard historical atlases; boundaries in this period are approximate and shifted over time. '
                   'Sea of Galilee shoreline © OpenStreetMap contributors; ancient Dead Sea outline from OpenBible.info (CC BY 4.0). Ancient roads are approximations. '
                   'Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap contributors. Imagery © Esri. Map engine: MapLibre GL.',
    }
    return m


BOOKS = ['MAT']


def main():
    idx_path = os.path.join(MAPS, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    for b in BOOKS:
        m = build(b)
        with open(os.path.join(MAPS, m['id'] + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(m, fh, ensure_ascii=False, indent=1)
        idx['maps'] = [e for e in idx['maps'] if e['id'] != m['id']]
        idx['maps'].append({'id': m['id'], 'title': m['title'], 'ref': m['ref'], 'book': b, 'c': 1, 'v': 1, 'bookwide': True,
                            'links': m['links'], 'aliases': m['aliases']})
        n = sum(len(g['places']) for g in m['groups'])
        print('%s: %d places, %d regions, %d tappable names' % (m['id'], n, len(m['regions']), len(m['links'])))
    order = ['GEN', 'EXO', 'JOS', 'JDG', 'MAT']
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
