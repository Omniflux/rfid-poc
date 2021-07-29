from csv import reader
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlite3 import connect

BIBMAP = '/var/local/bibmap.csv'
DATABASE = 'file:/var/local/tags.sqlite3?mode=ro'

app = FastAPI()
app.add_middleware (CORSMiddleware, allow_origins=['*'])

con = connect (DATABASE, uri=True)
con.enable_load_extension (True)
con.load_extension ('libsqlite3_mod_csvtable')
con.execute (f'CREATE VIRTUAL TABLE "temp"."bibmap" USING csvtable("{BIBMAP}", NULL, NULL, ",", NULL, "bib", "epc")')

@app.get ("/data")
async def root():
    return con.execute ('SELECT "tagreads"."rowid", "timestamp", "epc", (SELECT "bib" FROM "temp"."bibmap" WHERE "tagreads"."epc" = "temp"."bibmap"."epc") AS "bib" FROM "tagreads" GROUP BY "epc" HAVING MIN("tagreads"."rowid") ORDER BY "tagreads"."rowid"').fetchall()

@app.get ("/data/since/{since}")
async def since_record (since: int):
    return con.execute ('SELECT "tagreads"."rowid", "timestamp", "epc", (SELECT "bib" FROM "temp"."bibmap" WHERE "tagreads"."epc" = "temp"."bibmap"."epc") AS "bib" FROM "tagreads" GROUP BY "epc" HAVING MIN("tagreads"."rowid") AND "tagreads"."rowid" > ? ORDER BY "tagreads"."rowid"', [since]).fetchall()

@app.get ("/data/epc/{epc}")
async def epc_records (epc: str):
    return con.execute ('SELECT "rowid", * FROM "tagreads" WHERE "epc" = ? ORDER BY "rowid"', [epc]).fetchall()
