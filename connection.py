from flask import Flask, render_template, g
from py2neo import Graph
import os
from dotenv import load_dotenv
load_dotenv
def get_db():
    if not hasattr(g, 'Graph DBMS'):
        g.neo4j_db = Graph(
            os.getenv('ADT'),
            auth=(os.getenv('neo4j'), os.getenv('password')),
            name=os.getenv('DATABASE')  

        )
    return g.neo4j_db

def close_db(error):
    if hasattr(g, 'Graph DBMS'):
        g.neo4j_db = None