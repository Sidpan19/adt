import os
from flask import Flask, render_template, g
from py2neo import Graph
from dotenv import load_dotenv

load_dotenv()

def get_db():
    """
    Lazily create (and cache) a Graph instance on g.neo4j_db.
    """
    if 'neo4j_db' not in g:
        uri      = os.getenv("NEO4J_URI")
        user     = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        database = os.getenv("NEO4J_DATABASE", "neo4j")
        g.neo4j_db = Graph(uri, auth=(user, password), name=database)
    return g.neo4j_db

def close_db(error=None):
    """
    Teardown handler to close and remove the Graph instance.
    """
    graph = g.pop('neo4j_db', None)
    if graph is not None:
        try:
            graph.close()
        except Exception:
            pass