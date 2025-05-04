from flask import Flask, render_template, Blueprint
from connection import get_db
import pandas as pd
import plotly.express as px

locations_bp = Blueprint('locations', __name__, url_prefix='/locations')

def fetch_arrest_locations():
    db = get_db()
    query = """
     MATCH (a:Arrest)-[:OCCURRED_AT]->(loc:Location)
    WHERE loc.latitude IS NOT NULL AND loc.longitude IS NOT NULL
    RETURN DISTINCT loc.latitude AS lat, loc.longitude AS lon
    """
    return db.run(query).data()

@locations_bp.route('')
def show_locations():
    # 1) get list of points
    pts = fetch_arrest_locations()
    df  = pd.DataFrame(pts)  # columns ['lat','lon']

    # 2) build a Mapbox scatter with open-street-map style
    fig = px.scatter_mapbox(
        df,
        lat='lat',
        lon='lon',
        hover_data=['lat','lon'],
        zoom=10,
        center={'lat': 40.7128, 'lon': -74.0060},
        height=600
    )
    fig.update_traces(
        marker=dict(size=8, color='blue', opacity=0.7)
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0)
    )

    # 3) get embeddable HTML
    map_html = fig.to_html(full_html=False, include_plotlyjs='cdn')

    # 4) render
    return render_template('locations.html', map_html=map_html)