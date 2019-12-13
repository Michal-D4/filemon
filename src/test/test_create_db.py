import sqlite3
import src.core.create_db as db


def test_create_connection(start_db):
    con = start_db
    assert isinstance(con, sqlite3.Connection)


def test_create_all_objects(start_db, schema_db):
    con = start_db
    db.create_all_objects(con)
    schema = list(con.execute('select sql from sqlite_master;').fetchall())

    ex_schema = schema_db
    assert schema == ex_schema
