import re
from flask import Flask, current_app, jsonify, request
import joblib
import FiltersBuilder
import pandas as pd
import pymongo
import http.client
from datetime import datetime
from urllib.parse import quote
import json
import JsonBuild
from pymongo import MongoClient
from urllib.parse import quote_plus
from collections import OrderedDict
import requests
from bson import ObjectId
import os
import joblib
import re
import json
import numpy as np
import pandas as pd
from flask import request, jsonify
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer



app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
MODEL_PATH = os.path.join(BASE_DIR, "..", "Linear_Regression_Model", "linear_model.pkl")

pipe = joblib.load(MODEL_PATH)

conn = http.client.HTTPSConnection("zillow-com4.p.rapidapi.com")

headers = {
    'x-rapidapi-key': "d4f09fc61amshfb23248ceac5aa3p1cd52bjsn32ca45ff7c5a",

    'x-rapidapi-host': "zillow-com4.p.rapidapi.com"
}

db_password = quote_plus("Canada003$")
clusterUrl = f"mongodb+srv://gecchiussi:{db_password}@androidapp.1vwrpac.mongodb.net/?retryWrites=true&w=majority&appName=AndroidApp"

client = MongoClient(clusterUrl)
db = client["RealEstate"]
collectionUser = db["users"]
collectionListing = db["HouseListing"]
collectionFavourites = db["Favourites"]
collectionAddListings = db["AddListings"]

@app.route('/')
def index():
    return jsonify({"message": "Server attivo. Usa POST /login per autenticarti."})


@app.route('/login', methods=['POST'])
def login():
    try:
        print("Richiesta ricevuta:", request.data)
        data = request.get_json(force=True)

        if not data:
            return jsonify({"success": False, "message": "Nessun JSON ricevuto"}), 400

        email = data.get("username")
        password = data.get("password")

        if not email or not password:
            return jsonify({"success": False, "message": "Dati incompleti"}), 400

        user = collectionUser.find_one({"username": email})


        if not user:
            return jsonify({"success": False, "message": "Utente non trovato"}), 404

        if user["password"] != password:
            return jsonify({"success": False, "message": "Password errata"}), 401
        
        userId = str(user["_id"])


        return jsonify({"success": True, "message": "Login effettuato con successo", "userId": userId}), 200

    except Exception as e:
        print("Errore:", str(e))
        return jsonify({"success": False, "message": "Errore interno"}), 500
    

@app.route('/register', methods=['POST'])
def createAccount():
        data = request.get_json(force=True)

        if not data:
            return jsonify({"success": False, "message": "Nessun JSON ricevuto"}), 400

        email = data.get("username")
        password = data.get("password")

        if not email or not password:
            return jsonify({"success": False, "message": "Dati incompleti"}), 400
        

        new_user = {
        "username": email,
        "password": password  
        }

        new_username = new_user.get("username")

        if collectionUser.find_one({"username": new_username }):
            return jsonify({"success": False, "message": "Esiste già un account con questo username, procedere con il login"}), 400

        collectionUser.insert_one(new_user)

        return jsonify({"success": True, "message": "Registrazione effettuata con successo"}), 200



@app.route('/getListing', methods=['GET'])
def getListing():
    location = request.args.get("location")
    trending = request.args.get("trending", "false").lower() == "true"
    if not location:
        return jsonify({"success": False, "error": "Missing 'location' parameter"}), 400

    filters_raw = request.args.getlist("filters") or request.args.getlist("filters[]")


    ALIASES = {
        "singlefamily": "singleFamily",
        "multifamily":  "multiFamily",
        "multyfamily":  "multiFamily",  
        "condo":        "condo",
        "townhome":     "townhome",
    }
    allowed = {ALIASES.get(FiltersBuilder.norm(f), FiltersBuilder._to_str(f)) for f in filters_raw} if filters_raw else set()

    # ---- Filtri numerici ----
    priceMin      = request.args.get("priceMin",      type=float)
    priceMax      = request.args.get("priceMax",      type=float)
    livingAreaMin = request.args.get("livingAreaMin", type=float)
    livingAreaMax = request.args.get("livingAreaMax", type=float)
    lotSizeMin    = request.args.get("lotSizeMin",    type=float)
    lotSizeMax    = request.args.get("lotSizeMax",    type=float)



    # ---- Cache DB ----
    cached = collectionListing.find_one({"inputLocation": location})
    if cached:
        doc = JsonBuild.convert_objectid(cached)
        if trending:
            results = doc.get("results", []) 
            result_trend = JsonBuild.trendingBuilder(results)
            return jsonify({"success": True, "TrendingList": result_trend}), 200
        else:
            doc = JsonBuild.convert_objectid(cached)
            doc["results"] = FiltersBuilder.apply_all_filters(doc.get("results", []), allowed,priceMin, priceMax, livingAreaMin, livingAreaMax, lotSizeMin, lotSizeMax, ALIASES)
            return jsonify({"success": True, "data": doc}), 200

    # ---- Fetch esterna ----
    encoded_location = quote(location)
    url = f"https://zillow-com4.p.rapidapi.com/properties/search?location={encoded_location}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        parsed = resp.json()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    if not (parsed.get("status") and parsed.get("data")):
        return jsonify({"success": False, "error": "Nessun dato trovato"}), 404

    data = parsed["data"]
    if isinstance(data, list):
        raw_list = data
    elif isinstance(data, dict):
        raw_list = data.get("results") or data.get("list") or []
        if not isinstance(raw_list, list):
            raw_list = [data] if data else []
    else:
        raw_list = []

    if not raw_list:
        return jsonify({"success": False, "error": "Nessun dato trovato"}), 404

    converted_results = [JsonBuild.convert_json({"data": it}) for it in raw_list]

    document = OrderedDict([
        ("inputLocation", location),
        ("timestamp", datetime.utcnow()),
        ("type", "location"),
        ("results", converted_results),
    ])
    ins = collectionListing.insert_one(document)

    if trending:
        result_trend = JsonBuild.trendingBuilder(converted_results)
        return jsonify({"success": True, "TrendingList": result_trend}), 200

    filtered_results = FiltersBuilder.apply_all_filters(converted_results, priceMax, livingAreaMin, livingAreaMax, lotSizeMin, lotSizeMax, ALIASES)

    saved_doc = collectionListing.find_one({"_id": ins.inserted_id})
    saved_doc = JsonBuild.convert_objectid(saved_doc)
    saved_doc["results"] = filtered_results

    return jsonify({"success": True, "data": saved_doc}), 200



@app.route('/getListingAddress', methods=['GET'])
def getListingAddress():
    address = request.args.get("address")
    details = request.args.get("details", "false").lower() == "true"

    if not address:
        return jsonify({"success": False, "error": "Missing 'address' parameter"}), 400

    address_type = "detailedAddress" if details else "basicAddress"

    # Provo prima a cercare nel DB
    item = collectionListing.find_one({"inputAddress": address, "type": address_type})
    if item:
        item = JsonBuild.convert_objectid(item)
        return jsonify({"success": True, "data": item})

    # Altrimenti, faccio la richiesta esterna
    encoded_address = quote(address)
    endpoint = f"/properties/search-address?address={encoded_address}"

    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        data = res.read()
        parsed_data_addr = json.loads(data)

        if details:
            json_result = JsonBuild.convert_detailed_json(parsed_data_addr)
        else:
            json_result = JsonBuild.normalize_addr_to_json(parsed_data_addr)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    print(data.decode())

    if parsed_data_addr.get("status") and parsed_data_addr.get("data"):
        document = {
            "inputAddress": address,
            "type": address_type,
            "timestamp": datetime.utcnow(),
            "success": True,
            "results": json_result
        }

        result = collectionListing.insert_one(document)
        saved_doc = collectionListing.find_one({"_id": result.inserted_id})
        saved_doc = JsonBuild.convert_objectid(saved_doc)

        return jsonify({"success": True, "data": saved_doc})
    else:
        return jsonify({"success": False, "error": "Nessun dato trovato"}), 404
    
    
@app.route('/getUsername', methods=['GET'])
def getUsername():
    userId = request.args.get("userId")

    if not userId:
        return jsonify({"success": False, "error": "Missing parameter"}), 400

    try:
        result = collectionUser.find_one({"_id": ObjectId(userId)}, {"password": 0})
        if result:
            username = result.get("username")
        else:
            username = None
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    if not username:
        return jsonify({"success": False, "error": "Nothing found"}), 404
    else:
        return jsonify({
            "success": True,
            "username": username  
        })

    

@app.route('/addFavourites', methods=['POST'])
def addFavourite():
    try:
        data = request.get_json(force=True)

        if not data:
            return jsonify({"success": False, "message": "Nessun JSON ricevuto"}), 400
        


        userId = data.get("userId")
        listingId = data.get("listingId")

        if not userId or not listingId:
            return jsonify({"success": False, "message": "Dati incompleti"}), 400
        
        if collectionFavourites.find_one({"userId": userId, "listingId": listingId}):
            return jsonify ({"success": False, "message": "Annuncio già salvato"}), 409
        
        collectionFavourites.insert_one({"userId": userId, "listingId": listingId})
        return jsonify({"success": True, "message": "Operazione eseguita correttamente"}), 200
    except Exception as e:
     return jsonify({"success": False, "error": str(e)}), 500
    

@app.route('/getFavourites', methods=['GET'])
def getFavourite():
    try:
        userId = request.args.get("userId")
        print("userId ricevuto:", userId)

        if not userId:
            return jsonify({"success": False, "message": "Nessun userId ricevuto"}), 400

        result_cursor = collectionFavourites.find({"userId": userId}, {"listingId": 1, "_id": 0})
        listing_ids = [doc["listingId"] for doc in result_cursor if "listingId" in doc]

        return jsonify({"success": True, "data": listing_ids, "message": "Preferiti trovati"}), 200

    except Exception as e:
        print("Errore:", str(e))
        return jsonify({"success": False, "message": "Errore interno"}), 500


@app.route('/getListingLocationFromArray', methods=['GET'])
def get_listing_location_from_array():
    try:
        array_ids = request.args.getlist("ArrayId")
        if not array_ids:
            return jsonify({"success": False, "message": "Nessun ID ricevuto"}), 400

        results = collectionListing.find({"_id": {"$in": [ObjectId(i) for i in array_ids]}})
        result_list = list(results)

        for r in result_list:
            r['_id'] = str(r['_id'])

        return jsonify({"success": True, "data": result_list}), 200
    except Exception as e:
        print("Errore:", str(e))
        return jsonify({"success": False, "message": "Errore interno"}), 500
    


@app.route('/addMyListings', methods=['POST'])
def addMyListings():
    try:
        data = request.get_json(force=True)

        if not data:
            return jsonify({"success": False, "message": "Nessun JSON ricevuto"}), 400
        


        userId = data.get("userId")
        myListing = data.get("result")

        if not userId or not myListing:
            return jsonify({"success": False, "message": "Dati incompleti"}), 400
        
        collectionAddListings.insert_one({"userId": userId, "myListing": myListing})
        return jsonify({"success": True, "message": "Operazione eseguita correttamente"}), 200

    except Exception as e:
     return jsonify({"success": False, "error": str(e)}), 500
    


@app.route('/getMyListings', methods=['GET'])
def getMyListings():
    try:
        userId = request.args.get("userId")
        if not userId:
            return jsonify(success=False, message="userId mancante"), 400

        docs = list(collectionAddListings.find({"userId": userId}))  

        def convert(o):
            if isinstance(o, list):
                return [convert(x) for x in o]
            if isinstance(o, dict):
                return {k: convert(v) for k, v in o.items()}
            if isinstance(o, ObjectId):
                return str(o)
            if isinstance(o, datetime):
                return o.isoformat()
            return o

        clean = convert(docs)
        return jsonify(success=True, data=clean), 200

    except Exception as e:
        return jsonify(success=False, message=str(e)), 500
    

# ===================== LINEAR REGRESSION ==================
# Normalizzo il propertyType in base alle classi del training
TARGET_SCALE = "log"
def normalize_property_type(x: str) -> str:
    if not x:
        return ""
    key = re.sub(r"[\s_-]+", "", x)
    mapping = {
        "singlefamily": "singleFamily",
        "singlefamilyresidence": "singleFamily",
        "condo": "condo",
        "apartment": "condo",       
        "multifamily": "multiFamily",
        "manufactured": "manufactured",
        "townhome": "townhome",
        "townhouse": "townhome",
    }
    return mapping.get(key, x.strip())

def invert_target(y: float) -> float:
    if TARGET_SCALE == "log":
        return float(np.exp(y))
    if TARGET_SCALE == "log1p":
        return float(np.expm1(y))
    if TARGET_SCALE == "k":
        return float(y * 1000.0)
    return float(y)  



@app.route("/predictPrice", methods=["POST"])
def predict_price():
    payload = request.get_json() or {}

    # Lettura e normalizzazione input
    livingArea = float(payload.get("livingArea", 0))
    lotSize = float(payload.get("lotSize", 0))
    lotSizeUnit = (payload.get("lotSizeUnit") or "sqft").lower()
    yearBuilt = int(payload.get("yearBuilt", 0))
    propertyType = normalize_property_type(payload.get("propertyType") or "")
    city = (payload.get("city") or "").strip()

    if lotSizeUnit == "acres":
        lotSize *= 43560

    # Costruisco DataFrame di un singolo record
    df = pd.DataFrame([{
        "livingArea": livingArea,
        "lotSize": lotSize,
        "yearBuilt": yearBuilt,
        "propertyType": propertyType,
        "city": city
    }])

    # Predizione con pipeline
    raw_pred = float(pipe.predict(df)[0])
    price = invert_target(raw_pred)

    return jsonify(success=True, price=round(price, 2)), 200




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
