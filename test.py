from connection import get_db
from app import app       # import your Flask app
import pandas as pd
with app.app_context():
    db = get_db()
    query = """
    MATCH (a:Arrest)-[:OCCURRED_AT]->(loc:Location)
    WHERE loc.latitude IS NOT NULL AND loc.longitude IS NOT NULL
    RETURN loc.latitude AS lat, loc.longitude AS lon limit 2000
    """
    # db.run(query).data() gives list of dicts: [{'lat': ..., 'lon': ...}, …]
    result=db.run(query).data()
    df=pd.DataFrame(result)
    print(df.head())
