
## Wikidata place types and related OSM Tags

Wikidata does not have any official ontologies, however the [DBpedia project](https://wiki.dbpedia.org/) has created an [ontology](https://wiki.dbpedia.org/services-resources/ontology) that covered [place types](http://mappings.dbpedia.org/server/ontology/classes/#Place). The table below used the DBpedia place ontology as a starting point, and is provided as a cross-reference to the relevant OSM tags.

The Wikidata place types listed in the table below can be used in conjunction with the [Wikidata Query Service](https://query.wikidata.org/) to retrieve instances of those place types from the Wikidata knowledgebase. 

```
SELECT ?item ?lat ?lon
WHERE {
  ?item wdt:P31*/wdt:P279*wd:Q9430; wdt:P625 ?pt.
  ?item p:P625?loc.
  ?loc psv:P625?cnode.
  ?cnode wikibase:geoLatitude?lat.
  ?cnode wikibase:geoLongitude?lon.
}
```

An example json return for all instances of the Wikidata item "Q9430" (Ocean) can be seen at [json](https://query.wikidata.org/bigdata/namespace/wdq/sparql?format=json&query=SELECT?item?lat?lon%20WHERE{?item%20wdt:P31*/wdt:P279*wd:Q9430;wdt:P625?pt.?item%20p:P625?loc.?loc%20psv:P625?cnode.?cnode%20wikibase:geoLatitude?lat.?cnode%20wikibase:geoLongitude?lon.})

**NOTE** the OSM tags listed are those listed in the wikidata entries, and not all the possible matches for tags within OSM.


   title   |             concept                   |       OSM Tag     | 
-----------|---------------------------------------|------------------|
[Q17334923](https://www.wikidata.org/entity/Q17334923)  | Location | | 
[Q811979](https://www.wikidata.org/entity/Q811979)           | Architectural Structure | | 
[Q194195](https://www.wikidata.org/entity/Q194195)   | Amusement park | 
[Q204832](https://www.wikidata.org/entity/Q204832)   | Roller coaster | [attraction=roller_coaster](https://wiki.openstreetmap.org/wiki/Tag:attraction=roller_coaster) | 
[Q2870166](https://www.wikidata.org/entity/Q2870166)   | Water ride | |
[Q641226](https://www.wikidata.org/entity/Q641226)    | Arena | [amenity=events_centre](https://wiki.openstreetmap.org/wiki/Tag:amenity=events_centre) | 
[Q41176](https://www.wikidata.org/entity/Q41176)     | Building | [building=yes](https://wiki.openstreetmap.org/wiki/Key:building) |
[Q1303167](https://www.wikidata.org/entity/Q1303167)   | Barn | [building=barn](https://wiki.openstreetmap.org/wiki/Tag:building=barn) |
[Q655686](https://www.wikidata.org/entity/Q655686)   | Commercial building | [building=commercial](https://wiki.openstreetmap.org/wiki/Tag:building=commercial) | 
[Q4830453](https://www.wikidata.org/entity/Q4830453)   | Business | |
[Q7075](https://www.wikidata.org/entity/Q7075)     | Library | [amenity=library](https://wiki.openstreetmap.org/wiki/Tag:amenity=library) |
[Q133215](https://www.wikidata.org/entity/Q133215)   | Casino | [amenity=casino](https://wiki.openstreetmap.org/wiki/Tag:amenity=casino) | 
[Q23413](https://www.wikidata.org/entity/Q23413)     | Castle | [historic=castle](https://wiki.openstreetmap.org/wiki/Tag:historic=castle) |
[Q83405](https://www.wikidata.org/entity/Q83405)     | Factory | | 
[Q53060](https://www.wikidata.org/entity/Q53060)     | Gate  | [barrier=gate](https://wiki.openstreetmap.org/wiki/Tag:barrier=gate) |cnode%20wikibase:geoLatitude?lat.?cnode%20wikibase:geoLongitude?lon.})
[Q11755880](https://www.wikidata.org/entity/Q11755880)           | Residential Building  | [building=residential](https://wiki.openstreetmap.org/wiki/Tag:building=residential) | 
[Q3947](https://www.wikidata.org/entity/Q3947)      | House  | [building=house](https://wiki.openstreetmap.org/wiki/Tag:building=house) |
[Q35112127](https://www.wikidata.org/entity/Q35112127)           | Historic Building  | |
[Q5773747](https://www.wikidata.org/entity/Q5773747)   | Historic house  | | 
[Q38723](https://www.wikidata.org/entity/Q38723)           | Higher Education Institution  | 
[Q3914](https://www.wikidata.org/entity/Q3914)      | School  | [amenity=school](https://wiki.openstreetmap.org/wiki/Tag:amenity=school) | 
[Q9842](https://www.wikidata.org/entity/Q9842)      | Primary school  | | 
[Q159334](https://www.wikidata.org/entity/Q159334)    | Secondary school  | | 
[Q16917](https://www.wikidata.org/entity/Q16917)     | Hospital  | [amenity=hospital](https://wiki.openstreetmap.org/wiki/Tag:amenity=hospital), [healthcare=hospital](https://wiki.openstreetmap.org/wiki/Tag:healthcare=hospital), [building=hospital](https://wiki.openstreetmap.org/wiki/Tag:building=hospital) |
[Q27686](https://www.wikidata.org/entity/Q27686)     | Hotel  | [tourism=hotel](https://wiki.openstreetmap.org/wiki/Tag:tourism=hotel), [building=hotel](https://wiki.openstreetmap.org/wiki/Tag:building=hotel) |
[Q33506](https://www.wikidata.org/entity/Q33506)     | Museum  | [tourism=museum](https://wiki.openstreetmap.org/wiki/Tag:tourism=museum) |
[Q40357](https://www.wikidata.org/entity/Q40357)     | Prison  | [amenity=prison](https://wiki.openstreetmap.org/wiki/Tag:amenity=prison) |
[Q24398318](https://www.wikidata.org/entity/Q24398318)           | Religious Building  | |
[Q160742](https://www.wikidata.org/entity/Q160742)    | Abbey  | |
[Q16970](https://www.wikidata.org/entity/Q16970)     | Church (building)  | [building=church](https://wiki.openstreetmap.org/wiki/Tag:building=church) |
[Q44613](https://www.wikidata.org/entity/Q44613)     | Monastery  | [amenity=monastery](https://wiki.openstreetmap.org/wiki/Tag:amenity=monastery) | 
[Q32815](https://www.wikidata.org/entity/Q32815)     | Mosque  | [building=mosque](https://wiki.openstreetmap.org/wiki/Tag:building=mosque) | 
[Q697295](https://www.wikidata.org/entity/Q697295)    | Shrine  | [building=shrine](https://wiki.openstreetmap.org/wiki/Tag:building=shrine) |
[Q34627](https://www.wikidata.org/entity/Q34627)     | Synagogue  | [building=synagogue](https://wiki.openstreetmap.org/wiki/Tag:building=synagogue) |
[Q44539](https://www.wikidata.org/entity/Q44539)     | Temple  | [building=temple](https://wiki.openstreetmap.org/wiki/Tag:building=temple) | 
[Q11707](https://www.wikidata.org/entity/Q11707)     | Restaurant  | [amenity=restaurant](https://wiki.openstreetmap.org/wiki/Tag:amenity=restaurant) |
[Q11315](https://www.wikidata.org/entity/Q11315)     | Shopping mall  | [shop=mall](https://wiki.openstreetmap.org/wiki/Tag:shop=mall), [shop=shopping_centre](https://wiki.openstreetmap.org/wiki/Tag:shop=shopping_centre) | 
[Q11303](https://www.wikidata.org/entity/Q11303)     | Skyscraper  | |
[Q17350442](https://www.wikidata.org/entity/Q17350442)           | Venue  | |
[Q41253](https://www.wikidata.org/entity/Q41253)           | Movie Theater  | [amenity=cinema](https://wiki.openstreetmap.org/wiki/Tag:amenity=cinema) | 
[Q483110](https://www.wikidata.org/entity/Q483110)    | Stadium  | [leisure=stadium](https://wiki.openstreetmap.org/wiki/Tag:leisure=stadium), [building=stadium](https://wiki.openstreetmap.org/wiki/Tag:building=stadium) |
[Q24354](https://www.wikidata.org/entity/Q24354)     | Theater (structure)  | [amenity=theatre](https://wiki.openstreetmap.org/wiki/Tag:amenity=theatre) |
[Q121359](https://www.wikidata.org/entity/Q121359)    | Infrastructure  | |
[Q1248784](https://www.wikidata.org/entity/Q1248784)   | Airport  | |
[Q12323](https://www.wikidata.org/entity/Q12323)     | Dam  | [waterway=dam](https://wiki.openstreetmap.org/wiki/Tag:waterway=dam) |
[Q1353183](https://www.wikidata.org/entity/Q1353183)   | Launch pad  | | 
[Q105190](https://www.wikidata.org/entity/Q105190)   | Levee  | [man_made=dyke](https://wiki.openstreetmap.org/wiki/Tag:man_made=dyke) |
[Q105731](https://www.wikidata.org/entity/Q105731)    | Lock (water navigation)   | [lock=yes](https://wiki.openstreetmap.org/wiki/Key:lock) |
[Q44782](https://www.wikidata.org/entity/Q44782)     | Port  | |
[Q159719](https://www.wikidata.org/entity/Q159719)    | Power station  | [power=plant](https://wiki.openstreetmap.org/wiki/Tag:power=plant) |
[Q174814](https://www.wikidata.org/entity/Q174814)    | Electrical substation   |  |
[Q134447](https://www.wikidata.org/entity/Q134447)    | Nuclear power plant  | [plant:source=nuclear](https://wiki.openstreetmap.org/wiki/Tag:plant:source=nuclear) |
[Q786014](https://www.wikidata.org/entity/Q786014)   | Rest area  | [highway=rest_area](https://wiki.openstreetmap.org/wiki/Tag:highway=rest_area), [highway=services](https://wiki.openstreetmap.org/wiki/Tag:highway=services) |
[Q12280](https://www.wikidata.org/entity/Q12280)     | Bridge  | [bridge=* ](https://wiki.openstreetmap.org/wiki/Key:bridge), [man_made=bridge](https://wiki.openstreetmap.org/wiki/Tag:man_made=bridge) |
[Q728937](https://www.wikidata.org/entity/Q728937)           | Railroad Line  | [railway=rail](https://wiki.openstreetmap.org/wiki/Tag:railway=rail) | 
[Q1311958](https://www.wikidata.org/entity/Q1311958)           | Railway Tunnel  | | 
[Q34442](https://www.wikidata.org/entity/Q34442)     | Road  | [highway=* ](https://wiki.openstreetmap.org/wiki/Key:highway), [route=road](https://wiki.openstreetmap.org/wiki/Tag:route=road) |
[Q1788454](https://www.wikidata.org/entity/Q1788454)   | Road junction  |  | 
[Q44377](https://www.wikidata.org/entity/Q44377)     | Tunnel  | [tunnel=* ](https://wiki.openstreetmap.org/wiki/Key:tunnel) |
[Q5031071](https://www.wikidata.org/entity/Q5031071)  | Canal tunnel  | |
[Q719456](https://www.wikidata.org/entity/Q719456)    | Station  | [public_transport=station](https://wiki.openstreetmap.org/wiki/Tag:public_transport=station) |
[Q205495](https://www.wikidata.org/entity/Q205495)    | Filling station  | [amenity=fuel](https://wiki.openstreetmap.org/wiki/Tag:amenity=fuel) |
[Q928830](https://www.wikidata.org/entity/Q928830)    | Metro station  | [station=subway](https://wiki.openstreetmap.org/wiki/Tag:station=subway) |
[Q55488](https://www.wikidata.org/entity/Q55488)     | Train station  | [railway=station](https://wiki.openstreetmap.org/wiki/Tag:railway=station) |
[Q2175765](https://www.wikidata.org/entity/Q2175765)   | Tram stop  | [railway=tram_stop](https://wiki.openstreetmap.org/wiki/Tag:railway=tram_stop), [public_transport=stop_position](https://wiki.openstreetmap.org/wiki/Tag:public_transport=stop_position) |
[Q6852233](https://www.wikidata.org/entity/Q6852233)   | Military building  | |
[Q44494](https://www.wikidata.org/entity/Q44494)     | Mill (grinding)  | |
[Q185187](https://www.wikidata.org/entity/Q185187)    | Watermill  | [man_made=watermill](https://wiki.openstreetmap.org/wiki/Tag:man_made=watermill) |
[Q38720](https://www.wikidata.org/entity/Q38720)     | Windmill  | [man_made=windmill](https://wiki.openstreetmap.org/wiki/Tag:man_made=windmill) | 
[Q4989906](https://www.wikidata.org/entity/Q4989906)   | Monument  | [historic=monument](https://wiki.openstreetmap.org/wiki/Tag:historic=monument) |
[Q5003624](https://www.wikidata.org/entity/Q5003624)   | Memorial  | [historic=memorial](https://wiki.openstreetmap.org/wiki/Tag:historic=memorial) |
[Q271669](https://www.wikidata.org/entity/Q271669)   | Landform  | |
[Q190429](https://www.wikidata.org/entity/Q190429)    | Depression (geology)  | |
[Q17018380](https://www.wikidata.org/entity/Q17018380)  | Bight (geography)  | | 
[Q54050](https://www.wikidata.org/entity/Q54050)     | Hill  | |
[Q1210950](https://www.wikidata.org/entity/Q1210950)   | Channel (geography)  | |
[Q23442](https://www.wikidata.org/entity/Q23442)    | Island  | [place=island](https://wiki.openstreetmap.org/wiki/Tag:place=island) | 
[Q42523](https://www.wikidata.org/entity/Q42523)    | Atoll  | |
[Q34763](https://www.wikidata.org/entity/Q34763)    | Peninsula  | | 
[Q355304](https://www.wikidata.org/entity/Q355304)   | Watercourse  | |
[Q30198](https://www.wikidata.org/entity/Q30198)    | Marsh  | [wetland=marsh](https://wiki.openstreetmap.org/wiki/Tag:wetland=marsh) |
[Q75520](https://www.wikidata.org/entity/Q75520)    | Plateau  | |
[Q2042028](https://www.wikidata.org/entity/Q2042028)  | Ravine  | |
[Q631305](https://www.wikidata.org/entity/Q631305)   | Rock formation  | | 
[Q12516](https://www.wikidata.org/entity/Q12516)    | Pyramid  | |
[Q1076486](https://www.wikidata.org/entity/Q1076486) | Sports venue  |  |
[Q682943](https://www.wikidata.org/entity/Q682943)   | Cricket field  | [sport=cricket](https://wiki.openstreetmap.org/wiki/Tag:sport=cricket) | 
[Q1048525](https://www.wikidata.org/entity/Q1048525)  | Golf course  | [leisure=golf_course](https://wiki.openstreetmap.org/wiki/Tag:leisure=golf_course) |
[Q1777138](https://www.wikidata.org/entity/Q1777138)  | Race track  | [highway=raceway](https://wiki.openstreetmap.org/wiki/Tag:highway=raceway) | 
[Q130003](https://www.wikidata.org/entity/Q130003)   | Ski resort  | |
[Q174782](https://www.wikidata.org/entity/Q174782)   | Town square  | [place=square](https://wiki.openstreetmap.org/wiki/Tag:place=square) |
[Q12518](https://www.wikidata.org/entity/Q12518)    | Tower  | [building=tower](https://wiki.openstreetmap.org/wiki/Tag:building=tower), [man_made=tower](https://wiki.openstreetmap.org/wiki/Tag:man_made=tower) |
[Q39715](https://www.wikidata.org/entity/Q39715)    | Lighthouse  | [man_made=lighthouse](https://wiki.openstreetmap.org/wiki/Tag:man_made=lighthouse) |
[Q274153](https://www.wikidata.org/entity/Q274153)   | Water tower | [building=water_tower](https://wiki.openstreetmap.org/wiki/Tag:building=water_tower), [man_made=water_tower](https://wiki.openstreetmap.org/wiki/Tag:man_made=water_tower) |
[Q43501](https://www.wikidata.org/entity/Q43501)    | Zoo  | [tourism=zoo](https://wiki.openstreetmap.org/wiki/Tag:tourism=zoo) | 
[Q39614](https://www.wikidata.org/entity/Q39614)    | Cemetery  | [amenity=grave_yard](https://wiki.openstreetmap.org/wiki/Tag:amenity=grave_yard), [landuse=cemetery](https://wiki.openstreetmap.org/wiki/Tag:landuse=cemetery) |
[Q152081](https://www.wikidata.org/entity/Q152081)   | Concentration camp  | |
[Q1107656](https://www.wikidata.org/entity/Q1107656)  | Garden  | [leisure=garden](https://wiki.openstreetmap.org/wiki/Tag:leisure=garden) |
[Q820477](https://www.wikidata.org/entity/Q820477)   | Mine |  | 
[Q33837](https://www.wikidata.org/entity/Q33837) | Archipelago  | [place=archipelago](https://wiki.openstreetmap.org/wiki/Tag:place=archipelago) | 
[Q40080](https://www.wikidata.org/entity/Q40080)    | Beach  | [natural=beach](https://wiki.openstreetmap.org/wiki/Tag:natural=beach) |
[Q15324](https://www.wikidata.org/entity/Q15324)    | Body of water | [natural=water](https://wiki.openstreetmap.org/wiki/Tag:natural=water) | 
[Q23397](https://www.wikidata.org/entity/Q23397)    | Lake  | [water=lake](https://wiki.openstreetmap.org/wiki/Tag:water=lake) | 
[Q9430](https://www.wikidata.org/entity/Q9430)     | Ocean  | |
[Q165](https://www.wikidata.org/entity/Q165)    | Sea  | |
[Q47521](https://www.wikidata.org/entity/Q47521)    | Stream  | | 
[Q12284](https://www.wikidata.org/entity/Q12284)    | Canal  | [waterway=canal](https://wiki.openstreetmap.org/wiki/Tag:waterway=canal) |
[Q4022](https://www.wikidata.org/entity/Q4022)     | River  | [waterway=river](https://wiki.openstreetmap.org/wiki/Tag:waterway=river), [type=waterway](https://wiki.openstreetmap.org/wiki/Relation:waterway) |
[Q185113](https://www.wikidata.org/entity/Q185113)   | Cape | [natural=cape](https://wiki.openstreetmap.org/wiki/Tag:natural=cape) | 
[Q35509](https://www.wikidata.org/entity/Q35509)    | Cave  | [natural=cave_entrance](https://wiki.openstreetmap.org/wiki/Tag:natural=cave_entrance) | 
[Q8514](https://www.wikidata.org/entity/Q8514)     | Desert  | | 
[Q4421](https://www.wikidata.org/entity/Q4421)     | Forest  | [natural=wood](https://wiki.openstreetmap.org/wiki/Tag:natural=wood) |
[Q35666](https://www.wikidata.org/entity/Q35666)    | Glacier  | [natural=glacier](https://wiki.openstreetmap.org/wiki/Tag:natural=glacier) |
[Q177380](https://www.wikidata.org/entity/Q177380)   | Hot spring | | 
[Q8502](https://www.wikidata.org/entity/Q8502)     | Mountain  | [natural=peak](https://wiki.openstreetmap.org/wiki/Tag:natural=peak) | 
[Q133056](https://www.wikidata.org/entity/Q133056)   | Mountain pass  | | 
[Q46831](https://www.wikidata.org/entity/Q46831)    | Mountain range  | |
[Q39816](https://www.wikidata.org/entity/Q39816)    | Valley  | [natural=valley](https://wiki.openstreetmap.org/wiki/Tag:natural=valley) |
[Q8072](https://www.wikidata.org/entity/Q8072)     | Volcano  | [natural=volcano](https://wiki.openstreetmap.org/wiki/Tag:natural=volcano) |
[Q43229](https://www.wikidata.org/entity/Q43229)    | Organization  |  | 
[Q327333](https://www.wikidata.org/entity/Q327333)   | Government agency  | [office=government](https://wiki.openstreetmap.org/wiki/Tag:office=government)|
[Q22698](https://www.wikidata.org/entity/Q22698)    | Park | [leisure=park](https://wiki.openstreetmap.org/wiki/Tag:leisure=park) | 
[Q159313](https://www.wikidata.org/entity/Q159313)   | Urban agglomeration | |
[Q177634](https://www.wikidata.org/entity/Q177634)   | Community  | |
[Q5107](https://www.wikidata.org/entity/Q5107)    | Continent | [place=continent](https://wiki.openstreetmap.org/wiki/Tag:place=continent) |
[Q6256](https://www.wikidata.org/entity/Q6256)     | Country  | [place=country](https://wiki.openstreetmap.org/wiki/Tag:place=country) | 
[Q75848](https://www.wikidata.org/entity/Q75848)    | Gated community | | 
[Q3153117](https://www.wikidata.org/entity/Q3153117) | Intercommunality  | |
[Q82794](https://www.wikidata.org/entity/Q82794)    | Region  | | 
[Q56061](https://www.wikidata.org/entity/Q56061)    | Administrative division  | [boundary=administrative](https://wiki.openstreetmap.org/wiki/Tag:boundary=administrative)  | 
[Q665487](https://www.wikidata.org/entity/Q665487)   | Diocese | | 
[Q4976993](https://www.wikidata.org/entity/Q4976993)  | Parish | [boundary=civil_parish](https://wiki.openstreetmap.org/wiki/Tag:boundary=civil_parish) |
[Q194203](https://www.wikidata.org/entity/Q194203)   | Arrondissements of France  | |
[Q91028](https://www.wikidata.org/entity/Q91028)    | Arrondissements of Belgium  | | 
[Q3623867](https://www.wikidata.org/entity/Q3623867)  | Arrondissements of Benin  | | 
[Q2311958](https://www.wikidata.org/entity/Q2311958)  | Canton (country subdivision) | [political_division=canton](https://wiki.openstreetmap.org/wiki/FR:Cantons_in_France) |
[Q643589](https://www.wikidata.org/entity/Q643589)   | Department |  | 
[Q202216](https://www.wikidata.org/entity/Q202216)   | Overseas department and region  | |
[Q149621](https://www.wikidata.org/entity/Q149621)   | District  | [place=district](https://wiki.openstreetmap.org/wiki/Tag:place=district) |
[Q15243209](https://www.wikidata.org/wiki/Q15243209) | Historic district  | |
[Q5144960](https://www.wikidata.org/entity/Q5144960)  | Microregion  | | 
[Q15284](https://www.wikidata.org/entity/Q15284)    | Municipality  | |
[Q515716](https://www.wikidata.org/entity/Q515716)   | Prefecture  | |
[Q34876](https://www.wikidata.org/entity/Q34876)    | Province  | |
[Q3191695](https://www.wikidata.org/entity/Q3191695)  | Regency (Indonesia)  | |
[Q1970725](https://www.wikidata.org/entity/Q1970725)  | Natural region  | |
[Q486972](https://www.wikidata.org/entity/Q486972)   | Human settlement  | | 
[Q515](https://www.wikidata.org/entity/Q515)      | City  | [place=city](https://wiki.openstreetmap.org/wiki/Tag:place=city) |
[Q5119](https://www.wikidata.org/entity/Q5119)     | Capital city | [capital=yes](https://wiki.openstreetmap.org/wiki/Key:capital) |
[Q4286337](https://www.wikidata.org/entity/Q4286337)  | City district  | | 
[Q1394476](https://www.wikidata.org/entity/Q1394476)  | Civil township  | | 
[Q1115575](https://www.wikidata.org/entity/Q1115575)  | Civil parish  | [designation=civil_parish](https://wiki.openstreetmap.org/wiki/Tag:designation=civil_parish) |
[Q5153984](https://www.wikidata.org/entity/Q5153984)  | Commune-level subdivisions  | |
[Q123705](https://www.wikidata.org/entity/Q123705)   | Neighbourhood  | [place=neighbourhood](https://wiki.openstreetmap.org/wiki/Tag:place=neighbourhood) |
[Q1500350](https://www.wikidata.org/entity/Q1500350)  | Townships of China  | |
[Q17343829](https://www.wikidata.org/entity/Q17343829)           | Unincorporated Community  | |
[Q3957](https://www.wikidata.org/entity/Q3957)     | Town  | [place=town](https://wiki.openstreetmap.org/wiki/Tag:place=town) | 
[Q532](https://www.wikidata.org/entity/Q532)      | Village  | [place=village](https://wiki.openstreetmap.org/wiki/Tag:place=village) |
[Q5084](https://www.wikidata.org/entity/Q5084)     | Hamlet   | [place=hamlet](https://wiki.openstreetmap.org/wiki/Tag:place=hamlet) | 
[Q7275](https://www.wikidata.org/entity/Q7275)     | State  | | 
[Q79007](https://www.wikidata.org/entity/Q79007)    | Street  | |
[Q473972](https://www.wikidata.org/entity/Q473972)   | Protected area  | [boundary=protected_area](https://wiki.openstreetmap.org/wiki/Tag:boundary=protected_area) |
[Q1377575](https://www.wikidata.org/entity/Q1377575)  | Wildlife refuge  | | 
[Q1410668](https://www.wikidata.org/entity/Q1410668)  | National Wildlife Refuge  | [protection_title=National Wildlife Refuge](ownership=national), [ownership=national](https://wiki.openstreetmap.org/wiki/Tag:ownership=national)|
[Q9259](https://www.wikidata.org/entity/Q9259)     | World Heritage Site  | |

---

### Future Work

The Wikidata improvements to Nominatim can be further enhanced by:

- continuing to add new Wikidata links to OSM objects
- increasing the number of place types accounted for in the wikipedia_articles table
- working to use place types in the wikipedia_article matching process
