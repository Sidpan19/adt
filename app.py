from flask import Flask, render_template, g
from py2neo import Graph
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

def get_db():
    if not hasattr(g, 'Graph DBMS'):
        g.neo4j_db = Graph(
            os.getenv('ADT'),
            auth=(os.getenv('neo4j'), os.getenv('password'))
        )
    return g.neo4j_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'Graph DBMS'):
        g.neo4j_db = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/demographics')
def demographics():
    db = get_db()
    query = """
    MATCH (p:Person)<-[:INVOLVES]-(a:Arrest)-[:HAS_CHARGE]->(c:Charge)
    WHERE p.age_group = '25-44'
    RETURN p.age_group AS age, p.sex AS gender, p.race AS race, 
           COUNT(a) AS count
    ORDER BY count DESC
    LIMIT 25
    """
    results = db.run(query).data()
    return render_template('demographics.html', data=results)


@app.route('/recent')
def recent_arrests():
    db = get_db()
    query = """
    CALL { MATCH (a:Arrest) RETURN max(a.arrest_date) AS latest }
    MATCH (a:Arrest)-[:INVOLVES]->(p:Person)
    WHERE a.arrest_date >= latest - duration({days: 30})
    RETURN p.age_group AS age_group,  
           p.sex AS sex,              
           p.race AS race, 
           COUNT(*) AS count
    ORDER BY count DESC
    """
    results = db.run(query).data()
    return render_template('recent.html', data=results)


@app.route('/trends')
def arrest_trends():
    db = get_db()
    query = """
    CALL { MATCH (a:Arrest) RETURN max(a.arrest_date) AS latest }
    MATCH (a:Arrest)
    WHERE a.arrest_date >= latest - duration({days: 14})
    RETURN a.arrest_date AS date, COUNT(*) AS arrests
    ORDER BY date
    """
    results = db.run(query).data()
    return render_template('trends.html', data=results)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

