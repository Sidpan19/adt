import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user,
    login_required, current_user
)
from connection import get_db
from trends import trends_bp
from locations import locations_bp


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "fallback‑secret")

# --- Flask‑Login setup ---
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, username):
        self.id = username

# Pull credentials from env
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password")

@login_manager.user_loader
def load_user(user_id):
    if user_id == ADMIN_USER:
        return User(user_id)
    return None

app.register_blueprint(trends_bp, url_prefix="/trends")
app.register_blueprint(locations_bp, url_prefix="/locations")

# --- Public routes ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USER and password == ADMIN_PASS:
            user = User(username)
            login_user(user)
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next") or url_for("index")
            return redirect(next_page)
        flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

# --- Protected CRUD routes for Arrests ---

@app.route("/arrests")
@login_required
def list_arrests():
    db = get_db()
    query = """
    MATCH (a:Arrest)-[:INVOLVES]->(p:Person),
          (a)-[:HAS_CHARGE]->(c:Charge),
          (a)-[:OCCURRED_AT]->(l:Location)
    RETURN a.arrest_key            AS id,
           toString(a.arrest_date) AS date,
           p.age_group            AS age_group,
           p.sex                  AS sex,
           p.race                 AS race,
           c.pd_desc              AS pd_desc,
           c.ofns_desc            AS ofns_desc,
           c.law_cat_cd           AS law_cat_cd,
           l.boro                 AS boro,
           l.precinct             AS precinct
    ORDER BY a.arrest_date DESC
    LIMIT 50
    """
    arrests = db.run(query).data()
    return render_template("arrests.html", arrests=arrests)

@app.route("/arrests/new", methods=["GET", "POST"])
@login_required
def new_arrest():
    if request.method == "POST":
        form = request.form
        params = {
            "arrest_key": form["arrest_key"],
            "arrest_date": form["arrest_date"],
            "age_group": form["age_group"],
            "sex": form["sex"],
            "race": form["race"],
            "pd_desc": form["pd_desc"],
            "ofns_desc": form["ofns_desc"],
            "law_cat_cd": form["law_cat_cd"],
            "boro": form["boro"],
            "precinct": form["precinct"],
            "latitude": form["latitude"],
            "longitude": form["longitude"]
        }
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
        """, **params)
        return redirect(url_for("list_arrests"))
    return render_template("new_arrest.html")

@app.route("/arrests/edit/<int:arrest_key>", methods=["GET", "POST"])
@login_required
def edit_arrest(arrest_key):
    db = get_db()
    if request.method == "POST":
        form = request.form
        params = {
            "arrest_key": arrest_key,
            "arrest_date": form["arrest_date"],
            "age_group": form["age_group"],
            "sex": form["sex"],
            "race": form["race"],
            "pd_desc": form["pd_desc"],
            "ofns_desc": form["ofns_desc"],
            "law_cat_cd": form["law_cat_cd"],
            "boro": form["boro"],
            "precinct": form["precinct"],
            "latitude": form["latitude"],
            "longitude": form["longitude"]
        }
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
        """, **params)
        return redirect(url_for("list_arrests"))

    result = db.run("""
    MATCH (a:Arrest {arrest_key: toInteger($arrest_key)})-[:INVOLVES]->(p:Person),
          (a)-[:HAS_CHARGE]->(c:Charge),
          (a)-[:OCCURRED_AT]->(l:Location)
    RETURN a.arrest_key            AS id,
           toString(a.arrest_date) AS date,
           p.age_group            AS age_group,
           p.sex                  AS sex,
           p.race                 AS race,
           c.pd_desc              AS pd_desc,
           c.ofns_desc            AS ofns_desc,
           c.law_cat_cd           AS law_cat_cd,
           l.boro                 AS boro,
           l.precinct             AS precinct
    """, {"arrest_key": arrest_key}).data()

    if not result:
        return f"Arrest {arrest_key} not found", 404

    return render_template("edit_arrest.html", arrest=result[0])

@app.route("/arrests/delete/<int:arrest_key>", methods=["POST"])
@login_required
def delete_arrest(arrest_key):
    db = get_db()
    db.run("""
    MATCH (a:Arrest {arrest_key: toInteger($arrest_key)})
    DETACH DELETE a
    """, {"arrest_key": arrest_key})
    return redirect(url_for("list_arrests"))

# --- Public data pages ---

@app.route('/demographics')
def demographics():
    db = get_db()
    query = """
    // Overall statistics
    MATCH (p:Person)<-[:INVOLVES]-(a:Arrest)
    WITH count(a) as total_arrests
    
    // Race breakdown
    MATCH (p:Person)<-[:INVOLVES]-(a:Arrest)
    WITH total_arrests, p.race as race, count(a) as count
    WHERE race IS NOT NULL
    WITH total_arrests, collect({race: race, count: count, percentage: toFloat(count)/total_arrests*100}) as race_stats
    
    // Gender breakdown
    MATCH (p:Person)<-[:INVOLVES]-(a:Arrest)
    WITH total_arrests, race_stats, p.sex as gender, count(a) as count
    WHERE gender IS NOT NULL
    WITH total_arrests, race_stats, collect({gender: gender, count: count, percentage: toFloat(count)/total_arrests*100}) as gender_stats
    
    // Age group breakdown
    MATCH (p:Person)<-[:INVOLVES]-(a:Arrest)
    WITH total_arrests, race_stats, gender_stats, p.age_group as age, count(a) as count
    WHERE age IS NOT NULL
    WITH total_arrests, race_stats, gender_stats, collect({age: age, count: count, percentage: toFloat(count)/total_arrests*100}) as age_stats
    
    // Top charges
    MATCH (a:Arrest)-[:HAS_CHARGE]->(c:Charge)
    WITH total_arrests, race_stats, gender_stats, age_stats, c.pd_desc as charge, count(a) as count
    ORDER BY count DESC LIMIT 10
    WITH total_arrests, race_stats, gender_stats, age_stats, collect({charge: charge, count: count, percentage: toFloat(count)/total_arrests*100}) as top_charges
    
    // Top boroughs
    MATCH (a:Arrest)-[:OCCURRED_AT]->(l)
    WITH total_arrests, race_stats, gender_stats, age_stats, top_charges, l.boro as borough, count(a) as count
    WHERE borough IS NOT NULL
    ORDER BY count DESC
    WITH total_arrests, race_stats, gender_stats, age_stats, top_charges, collect({borough: borough, count: count, percentage: toFloat(count)/total_arrests*100}) as borough_stats
    
    RETURN total_arrests, race_stats, gender_stats, age_stats, top_charges, borough_stats
    """
    results = db.run(query).data()
    return render_template('demographics.html', stats=results[0])

@app.route("/recent")
def recent_arrests():
    db = get_db()
    results = db.run("""
    CALL { MATCH (a:Arrest) RETURN max(a.arrest_date) AS latest }
    MATCH (a:Arrest)-[:INVOLVES]->(p:Person)
    WHERE a.arrest_date >= latest - duration({days: 30})
    RETURN p.age_group AS age_group, p.sex AS sex, p.race AS race, COUNT(*) AS count
    ORDER BY count DESC
    """).data()
    return render_template("recent.html", data=results)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
