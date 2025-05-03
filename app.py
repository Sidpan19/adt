from flask import Flask, render_template, g, request,redirect, url_for
from py2neo import Graph
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

def get_db():
    if not hasattr(g, 'Graph DBMS'):
        g.neo4j_db = Graph(
            os.getenv('ADT'),
            auth=(os.getenv('neo4j'), os.getenv('password')),
            name=os.getenv('DATABASE')  # ✅ explicitly set database

        )  
    print('yasssssssssss')
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


# LIST ARRESTS
@app.route('/arrests')
def list_arrests():
    db = get_db()
    query = """
    MATCH (a:Arrest)-[:INVOLVES]->(p:Person)
    RETURN a.arrest_key AS id, toString(a.arrest_date) AS date, 
           p.age_group + ' ' + p.sex + ' ' + p.race AS person
    ORDER BY a.arrest_date DESC
    LIMIT 50
    """
    arrests = db.run(query).data()
    return render_template('arrests.html', arrests=arrests)

@app.route('/arrests/new', methods=['GET', 'POST'])
def new_arrest():
    if request.method == 'POST':
        arrest_key = request.form['arrest_key']
        arrest_date = request.form['arrest_date']
        age_group = request.form['age_group']
        sex = request.form['sex']
        race = request.form['race']
        
        db = get_db()
        db.run("""
        MERGE (p:Person {age_group: $age_group, sex: $sex, race: $race})
        CREATE (a:Arrest {arrest_key: toInteger($arrest_key), arrest_date: date($arrest_date)})
        CREATE (a)-[:INVOLVES]->(p)
        """, arrest_key=arrest_key, arrest_date=arrest_date,
             age_group=age_group, sex=sex, race=race)
        
        return redirect(url_for('list_arrests'))
    return render_template('new_arrest.html')

@app.route('/arrests/edit/<arrest_key>', methods=['GET', 'POST'])
def edit_arrest(arrest_key):
    db = get_db()
    if request.method == 'POST':
        new_date = request.form['arrest_date']
        db.run("""
        MATCH (a:Arrest {arrest_key: toInteger($arrest_key)})
        SET a.arrest_date = date($new_date)
        """, arrest_key=arrest_key, new_date=new_date)
        return redirect(url_for('list_arrests'))
    
    result = db.run("""
    MATCH (a:Arrest {arrest_key: toInteger($arrest_key)})
    RETURN a.arrest_key AS id, toString(a.arrest_date) AS date
    """, arrest_key=arrest_key).data()
    
    if not result:
        return f"Arrest {arrest_key} not found", 404
    
    return render_template('edit_arrest.html', arrest=result[0])

@app.route('/arrests/delete/<arrest_key>', methods=['POST'])
def delete_arrest(arrest_key):
    db = get_db()
    db.run("""
    MATCH (a:Arrest {arrest_key: toInteger($arrest_key)})
    DETACH DELETE a
    """, arrest_key=arrest_key)
    return redirect(url_for('list_arrests'))

@app.route('/arrests/edit', methods=['POST'])
def edit_arrest_input():
    arrest_key = request.form['arrest_key']
    return redirect(url_for('edit_arrest', arrest_key=arrest_key))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

