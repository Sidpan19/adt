CREATE CONSTRAINT arrest_key_unique IF NOT EXISTS FOR (a:Arrest) 
REQUIRE a.arrest_key IS UNIQUE;

CREATE CONSTRAINT charge_unique IF NOT EXISTS FOR (c:Charge) 
REQUIRE (c.pd_desc, c.ofns_desc, c.law_cat_cd) IS NODE KEY;

CREATE CONSTRAINT location_unique IF NOT EXISTS FOR (l:Location) 
REQUIRE (l.boro, l.precinct) IS NODE KEY;

CREATE CONSTRAINT person_unique IF NOT EXISTS FOR (p:Person) 
REQUIRE (p.age_group, p.sex, p.race) IS NODE KEY;

CALL apoc.periodic.iterate(
  "LOAD CSV WITH HEADERS FROM 'https://drive.google.com/uc?export=download&id=1zOR1WyTckP7ldgPPrLy8gc7MjkcwdkPl' AS row RETURN row",
  "MERGE (a:Arrest {arrest_key: toInteger(row.ARREST_KEY)})
   SET a.arrest_date = date(row.ARREST_DATE)

   MERGE (c:Charge {pd_desc: row.PD_DESC, ofns_desc: row.OFNS_DESC, law_cat_cd: row.LAW_CAT_CD})

   MERGE (l:Location {boro: row.ARREST_BORO, precinct: toInteger(row.ARREST_PRECINCT)})
   SET l.jurisdiction_code = toInteger(row.JURISDICTION_CODE),
       l.latitude = toFloat(row.Latitude),
       l.longitude = toFloat(row.Longitude)

   MERGE (p:Person {age_group: row.AGE_GROUP, sex: row.PERP_SEX, race: row.PERP_RACE})

   MERGE (a)-[:HAS_CHARGE]->(c)
   MERGE (a)-[:OCCURRED_AT]->(l)
   MERGE (a)-[:INVOLVES]->(p)",
  {batchSize:10000, parallel:false}
);

