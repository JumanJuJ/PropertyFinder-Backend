from bson import ObjectId 

def convert_objectid(data):
    """Funzione ricorsiva per convertire tutti gli ObjectId in stringa."""
    if isinstance(data, list):
        return [convert_objectid(item) for item in data]
    elif isinstance(data, dict):
        return {
            key: convert_objectid(value) if isinstance(value, (dict, list)) else (
                str(value) if isinstance(value, ObjectId) else value
            )
            for key, value in data.items()
        }
    else:
        return data


def convert_json(parsed_data):
    raw_data = parsed_data.get("data", {}) if isinstance(parsed_data, dict) else parsed_data

    listing = raw_data.get("hdpView") or {}

    address = raw_data.get("address") if isinstance(raw_data.get("address"), dict) else None

    location = {
        "latitude": raw_data.get("location", {}).get("latitude"),
        "longitude": raw_data.get("location", {}).get("longitude")
    } if isinstance(raw_data.get("location"), dict) else None

    media_data = raw_data.get("media", {})
    all_photos = media_data.get("allPropertyPhotos", {})
    high_res = all_photos.get("highResolution", [])
    media = {
        "allPropertyPhotos": {
            "highResolution": [high_res[0]]
        }
    } if isinstance(high_res, list) and high_res else None

    lot_data = raw_data.get("lotSizeWithUnit", {})
    lot_info = {
     "lotSize": lot_data.get("lotSize"),
     "lotSizeUnit": lot_data.get("lotSizeUnit")
     } if lot_data else None

    if lot_info and lot_info["lotSizeUnit"] == "acres":

     lot_info["lotSize"] = lot_info["lotSize"] * 43560 if lot_info["lotSize"] else None
     lot_info["lotSizeUnit"] = "sqft"

    price_data = raw_data.get("price", {})
    price = {
        "value": price_data.get("value"),
        "pricePerSquareFoot": price_data.get("pricePerSquareFoot")
    } if price_data else None

    return {
        "zpid": raw_data.get("zpid"),
        "address": address,
        "location": location,
        "media": media,
        "bathrooms": raw_data.get("bathrooms"),
        "bedrooms": raw_data.get("bedrooms"),
        "country": raw_data.get("country", "usa"),
        "listingStatus": listing.get("listingStatus") if isinstance(listing, dict) else None,
        "livingArea": raw_data.get("livingArea"),
        "yearBuilt": raw_data.get("yearBuilt"),
        "lotSizeUnit": lot_info,
        "propertyType": raw_data.get("propertyType"),
        "price": price
    }





def normalize_addr_to_json(parsed_data_addr):
    raw_data = parsed_data_addr.get("data", {}) if isinstance(parsed_data_addr.get("data"), dict) else {}

    formatted_chip = raw_data.get("formattedChip")
    if isinstance(formatted_chip, dict):
        result = formatted_chip.get("quickFacts", [])
    else:
        result = []

    photo_urls = raw_data.get("photoUrlsHighRes", [])
    if isinstance(photo_urls, list):
        high_res_photos = [img.get("url") for img in photo_urls if isinstance(img, dict) and "url" in img]
    else:
        high_res_photos = []

    return {
        "zpid": raw_data.get("zpid"),
        "location": {
            "latitude": raw_data.get("latitude"),
            "longitude": raw_data.get("longitude")
        } if "latitude" in raw_data and "longitude" in raw_data else None,

        "media": {
            "allPropertyPhotos": {
                "highResolution": high_res_photos
            }
        } if high_res_photos else None,

        "bathrooms": getBaths(result) if callable(getBaths) else None,
        "bedrooms": getBeds(result) if callable(getBeds) else None,
        "country": "usa",
        "livingStatus": raw_data.get("homeStatus"),
        "livingArea": raw_data.get("livingAreaValue"),
        "yearBuilt": raw_data.get("resoFacts", {}).get("yearBuilt") if isinstance(raw_data.get("resoFacts"), dict) else None,
        "lotSizeUnit": {
            "lotSize": raw_data.get("lotAreaValue"),
            "lotSizeUnit": raw_data.get("lotAreaUnits")
        } if raw_data.get("lotAreaValue") or raw_data.get("lotAreaUnits") else None,
        "propertyType": raw_data.get("homeType"),
        "price": {
            "value": raw_data.get("price"),
            "pricePerSquareFoot": raw_data.get("resoFacts", {}).get("pricePerSquareFoot")
        } if raw_data.get("price") or (isinstance(raw_data.get("resoFacts"), dict) and raw_data["resoFacts"].get("pricePerSquareFoot")) else None,
    }

def getBaths(result):
    baths = "Info not available"
    for item in result:
        if item.get("elementType") == "baths":
            baths = item.get("contentDescription", baths)
    return baths

def getBeds(result):
    beds = "Info not available"
    for item in result:
        if item.get("elementType") == "beds":
            beds = item.get("contentDescription", beds)
    return beds

def convert_detailed_json(detailed_address):
    raw_data = detailed_address.get("data") or {}
    reso_facts = raw_data.get("resoFacts") or {}
    result = raw_data.get("formattedChip", {}).get("quickFacts", [])

    photo_urls = raw_data.get("photoUrlsHighRes")
    high_res_images = [
        img["url"] for img in photo_urls if isinstance(img, dict) and "url" in img
    ] if isinstance(photo_urls, list) else []

    return {
        "zpid": raw_data.get("zpid"),
        "description": raw_data.get("description") or "",
        "location": {
            "latitude": raw_data.get("latitude"),
            "longitude": raw_data.get("longitude")
        },
        "media": {
            "mainImage": raw_data.get("imageLink") or "",
            "streetView": raw_data.get("streetViewImageUrl") or "",
            "allPropertyPhotos": {
                "highResolution": high_res_images
            }
        },
        "bathrooms": getBaths(result),
        "bedrooms": getBeds(result),
        "details": {
            "garageInfo": reso_facts.get("parkingFeatures") or [],
            "coolingInfo": reso_facts.get("cooling") or [],
            "heatingInfo": reso_facts.get("heating") or [],
            "flooring": reso_facts.get("flooring") or [],
            "appliances": reso_facts.get("appliances") or []
        },
        "country": "usa",
        "livingStatus": raw_data.get("homeStatus") or "",
        "livingArea": raw_data.get("livingAreaValue"),
        "yearBuilt": reso_facts.get("yearBuilt"),
        "lotSizeUnit": {
            "lotSize": raw_data.get("lotAreaValue"),
            "lotSizeUnit": raw_data.get("lotAreaUnits") or "squareFeet"
        },
        "propertyType": raw_data.get("homeType") or "",
        "price": {
            "value": raw_data.get("price"),
            "pricePerSquareFoot": reso_facts.get("pricePerSquareFoot")
        },
        "zestimate": raw_data.get("zestimate"),
        "hoaFee": raw_data.get("hoaFee"),
        "hoaFeeFrequency": raw_data.get("hoaFeeFrequency") or ""
    }

def trendingBuilder(converted_results):
    trending_list = []

    for item in converted_results:
        address = item.get("address", {}).get("streetAddress", "N/A")
        images = item.get("media", {}).get("allPropertyPhotos", {}).get("highResolution", [])
        first_image = images[0] if images else None

        trending_list.append({
            "address": address,
            "imageUrl": first_image
        })

    return trending_list


