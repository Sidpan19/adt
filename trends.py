from flask import Blueprint, render_template
from connection import *

trends_bp = Blueprint('trends', __name__, url_prefix='/trends')

def fetch_arrest_data():
    """
    Returns list of {"date": "YYYY-MM-DD", "arrests": int}
    """
    db = get_db()
    query = """
    CALL {
      MATCH (a:Arrest)
      RETURN max(a.arrest_date) AS latest
    }
    MATCH (a:Arrest)
    WHERE a.arrest_date >= latest - duration({days: 14})
    RETURN a.arrest_date AS date, COUNT(*) AS arrests
    ORDER BY date
    """
    raw = db.run(query).data()
    # convert Python dates to ISO strings
    return [
        {
          "date": record["date"].isoformat(), 
          "arrests": record["arrests"]
        }
        for record in raw
    ]

def fetch_arrests_by_race():
    """
    Returns list of { race: <string>, count: <int> }, ordered by count desc.
    """
    db = get_db()
    query = """
    MATCH (a:Arrest)-[:INVOLVES]->(p:Person)
WHERE p.race IS NOT NULL
RETURN p.race   AS race,
       COUNT(a) AS count
ORDER BY count DESC;
    """
    return [
        {"race": record["race"], "count": record["count"]}
        for record in db.run(query)
    ]

def fetch_top_charges():
    """
    Returns a list of the top 5 charges plus an 'Other' bucket,
    based on the ofns_desc property on Charge nodes.
    """
    db = get_db()

    # 1) Fetch top 5 charges
    top5 = db.run("""
      MATCH (a:Arrest)-[:HAS_CHARGE]->(c:Charge)
      WHERE c.ofns_desc IS NOT NULL
      WITH c.ofns_desc AS charge, COUNT(a) AS cnt
      RETURN charge, cnt
      ORDER BY cnt DESC
      LIMIT 5
    """).data()

    total_row = db.run("""
      MATCH (a:Arrest)-[:CHARGED]->(c:Charge)
      WHERE c.ofns_desc IS NOT NULL
      RETURN COUNT(a) AS total
    """).data()[0]   # first (and only) row as a dict

    total       = total_row["total"]
    top5_sum    = sum(rec["cnt"] for rec in top5)
    other_count = total - top5_sum

    charges = [{"charge": rec["charge"], "count": rec["cnt"]} for rec in top5]
    charges.append({"charge": "Other", "count": other_count})
    return charges

def fetch_arrests_by_age_group():
    """
    Returns list of {"age_group": str, "count": int} based on p.age_group.
    """
    db = get_db()
    query = """
    MATCH (a:Arrest)-[:INVOLVES]->(p:Person)
    WHERE p.age_group IS NOT NULL
    WITH p.age_group AS age_group, COUNT(a) AS count
    RETURN age_group, count
    ORDER BY
      CASE age_group
        WHEN '<18' THEN 1
        WHEN '18-24' THEN 2
        WHEN '25-44' THEN 3
        WHEN '45-64' THEN 4
        WHEN '65+' THEN 5
        ELSE 6 END
    """
    return [
        {"age_group": record["age_group"], "count": record["count"]}
        for record in db.run(query).data()
    ]

def fetch_arrest_locations():
    """
    Returns a list of {"lat": float, "lon": float} for every Arrest node
    linked via OCCURRED_AT → Location (where both coords are non-null).
    """
    db = get_db()
    query = """
    MATCH (a:Arrest)-[:OCCURRED_AT]->(loc:Location)
    WHERE loc.latitude IS NOT NULL AND loc.longitude IS NOT NULL
    RETURN loc.latitude AS lat, loc.longitude AS lon limit 2000
    """
    # db.run(query).data() gives list of dicts: [{'lat': ..., 'lon': ...}, …]
    return db.run(query).data()

@trends_bp.route('')
def show_trends():
    # compose all the data
    data = fetch_arrest_data()
    race_data = fetch_arrests_by_race()
    age_data     = fetch_arrests_by_age_group()   # now uses the stored property
    charges_data = fetch_top_charges()
    locations=fetch_arrest_locations()
    return render_template(
        'trends.html',
        data=data,
        race_data=race_data,
        age_data=age_data,
        charges_data=charges_data,
        locations=locations
    )