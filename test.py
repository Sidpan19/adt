from connection import get_db
from app import app       # import your Flask app

with app.app_context():
    db = get_db()
    query = """
    MATCH (a:Arrest)
    WHERE a.race IS NOT NULL
    WITH a.race AS race, COUNT(*) AS count
    RETURN race, count
    ORDER BY count DESC
    """
    result = db.run(query).data()
    print(len(result))
