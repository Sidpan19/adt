from connection import *
from trends import trends_bp
from dotenv import load_dotenv

load_dotenv
app = Flask(__name__)

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

app.register_blueprint(trends_bp)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

