from flask import Flask, render_template, g, request, redirect, url_for
from py2neo import Graph
import os
from dotenv import load_dotenv

from connection import *
from trends import trends_bp
from locations import locations_bp

load_dotenv()

app = Flask(__name__)
app.register_blueprint(trends_bp)
app.register_blueprint(locations_bp)

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
    RETURN p.age_group AS age_group, p.sex AS sex, p.race AS race, COUNT(*) AS count
    ORDER BY count DESC
    """
    results = db.run(query).data()
    return render_template('recent.html', data=results)


@app.route('/arrests')
def list_arrests():
    db = get_db()
    query = """
    MATCH (a:Arrest)-[:INVOLVES]->(p:Person),
          (a)-[:HAS_CHARGE]->(c:Charge),
          (a)-[:OCCURRED_AT]->(l:Location)
    RETURN a.arrest_key AS id,
           toString(a.arrest_date) AS date,
           p.age_group AS age_group, p.sex AS sex, p.race AS race,
           c.pd_desc AS pd_desc, c.ofns_desc AS ofns_desc, c.law_cat_cd AS law_cat_cd,
           l.boro AS boro, l.precinct AS precinct
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
        pd_desc = request.form['pd_desc']
        ofns_desc = request.form['ofns_desc']
        law_cat_cd = request.form['law_cat_cd']
        boro = request.form['boro']
        precinct = request.form['precinct']
        latitude = request.form['latitude']
        longitude = request.form['longitude']

        db = get_db()
        db.run("""
        MERGE (p:Person {age_group: $age_group, sex: $sex, race: $race})
        MERGE (c:Charge {pd_desc: $pd_desc, ofns_desc: $ofns_desc, law_cat_cd: $law_cat_cd})
        MERGE (l:Location {boro: $boro, precinct: toInteger($precinct)})
        SET l.latitude = toFloat($latitude), l.longitude = toFloat($longitude)
        CREATE (a:Arrest {
            arrest_key: toInteger($arrest_key),
            arrest_date: date({
                year: toInteger(split($arrest_date, "-")[0]),
                month: toInteger(split($arrest_date, "-")[1]),
                day: toInteger(split($arrest_date, "-")[2])
            })
        })
        CREATE (a)-[:INVOLVES]->(p)
        CREATE (a)-[:HAS_CHARGE]->(c)
        CREATE (a)-[:OCCURRED_AT]->(l)
        """, arrest_key=arrest_key, arrest_date=arrest_date,
            age_group=age_group, sex=sex, race=race,
            pd_desc=pd_desc, ofns_desc=ofns_desc, law_cat_cd=law_cat_cd,
            boro=boro, precinct=precinct, latitude=latitude, longitude=longitude)
        return redirect(url_for('list_arrests'))
    return render_template('new_arrest.html')

@app.route('/arrests/edit/<arrest_key>', methods=['GET', 'POST'])
def edit_arrest(arrest_key):
    db = get_db()

    if request.method == 'POST':
        arrest_date = request.form['arrest_date']
        age_group = request.form['age_group']
        sex = request.form['sex']
        race = request.form['race']
        pd_desc = request.form['pd_desc']
        ofns_desc = request.form['ofns_desc']
        law_cat_cd = request.form['law_cat_cd']
        boro = request.form['boro']
        precinct = request.form['precinct']
        latitude = request.form['latitude']
        longitude = request.form['longitude']

        # UPDATE using relationship re-linking (important for node keys)
        db.run("""
        MATCH (a:Arrest {arrest_key: toInteger($arrest_key)})-[old_inv:INVOLVES]->(old_p:Person),
            (a)-[old_ch:HAS_CHARGE]->(old_c:Charge),
            (a)-[old_loc:OCCURRED_AT]->(old_l:Location)
        MERGE (new_p:Person {age_group: $age_group, sex: $sex, race: $race})
        MERGE (new_c:Charge {pd_desc: $pd_desc, ofns_desc: $ofns_desc, law_cat_cd: $law_cat_cd})
        MERGE (new_l:Location {boro: $boro, precinct: toInteger($precinct)})
        SET new_l.latitude = toFloat($latitude), new_l.longitude = toFloat($longitude),
            a.arrest_date = date({
                year: toInteger(split($arrest_date, "-")[0]),
                month: toInteger(split($arrest_date, "-")[1]),
                day: toInteger(split($arrest_date, "-")[2])
            })
        DELETE old_inv, old_ch, old_loc
        MERGE (a)-[:INVOLVES]->(new_p)
        MERGE (a)-[:HAS_CHARGE]->(new_c)
        MERGE (a)-[:OCCURRED_AT]->(new_l)
        """, arrest_key=arrest_key, arrest_date=arrest_date,
     age_group=age_group, sex=sex, race=race,
     pd_desc=pd_desc, ofns_desc=ofns_desc, law_cat_cd=law_cat_cd,
     boro=boro, precinct=precinct, latitude=latitude, longitude=longitude)
        return redirect(url_for('list_arrests'))

    result = db.run("""
    MATCH (a:Arrest {arrest_key: toInteger($arrest_key)})-[:INVOLVES]->(p:Person),
          (a)-[:HAS_CHARGE]->(c:Charge),
          (a)-[:OCCURRED_AT]->(l:Location)
    RETURN a.arrest_key AS id, toString(a.arrest_date) AS date,
           p.age_group AS age_group, p.sex AS sex, p.race AS race,
           c.pd_desc AS pd_desc, c.ofns_desc AS ofns_desc, c.law_cat_cd AS law_cat_cd,
           l.boro AS boro, l.precinct AS precinct
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

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
