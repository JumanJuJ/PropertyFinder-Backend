import pandas as pd
import requests
import time
import csv
import os

df = pd.read_csv("cities_clean.csv")
cities = df["City"].tolist()

file_path = "dataset.csv"
file_exists = os.path.isfile(file_path)

# Apri in append
with open(file_path, "a", newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        "city", "price", "livingArea", "lotSizeUnit", "lotSize", 
        "propertyType", "yearBuilt"
    ])

    # Scrivi l’header solo se il file non esiste
    if not file_exists:
        writer.writeheader()

    for city in cities:
        try:
            response = requests.get("http://localhost:5000/getListing", params={"location": city})
            if response.status_code == 200:
                json_data = response.json()
                results = json_data.get("data", {}).get("results", [])

                for item in results:
                    try:
                        row = {
                            "city": city,
                            "price": item.get("price", {}).get("value"),
                            "livingArea": item.get("livingArea"),
                            "lotSize": item.get("lotSizeUnit", {}).get("lotSize"),
                            "lotSizeUnit": item.get("lotSizeUnit", {}).get("lotSizeUnit"),
                            "propertyType": item.get("propertyType"),
                            "yearBuilt": item.get("yearBuilt")
                        }
                        writer.writerow(row)
                        print(f"[OK] {city}")
                    except Exception as e:
                        print(f"[SKIP ITEM] {city}: {e}")
            else:
                print(f"[ERRORE {response.status_code}] {city}: {response.text}")
        except Exception as e:
            print(f"[ECCEZIONE] {city}: {e}")

        time.sleep(3)

print("✅ Nuovi dati aggiunti in 'dataset.csv'")

