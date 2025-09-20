import re
from flask import Flask, current_app, jsonify, request
import joblib
from matplotlib.pylab import norm
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

def _to_str(x):
        """Estrarre una stringa da string/dict/list; fallback ''."""
        if isinstance(x, str):
            return x
        if isinstance(x, dict):
            for k in ("value", "unit", "type", "name", "label"):
                v = x.get(k)
                if isinstance(v, str):
                    return v
            return ""
        if isinstance(x, (list, tuple)) and x:
            return _to_str(x[0])
        return ""

def norm(s):
        """Normalizza: minuscolo e solo alfanumerico; tollerante a dict/list."""
        s = _to_str(s)
        return "".join(ch for ch in s if ch.isalnum()).lower()

def in_range(v, lo, hi):
        if lo is None and hi is None:
            return True
        if v is None:
            return False
        return (lo is None or v >= lo) and (hi is None or v <= hi)

def price_value(it):
        for key in ("price", "listPrice", "priceValue"):
            v = it.get(key)
            if isinstance(v, dict):
                v = v.get("value")
            try:
                if v is not None:
                    return float(v)
            except Exception:
                pass
        return None

def living_area_sqft(it):
        la = it.get("livingArea") or it.get("livingAreaObj")
        if isinstance(la, dict):
            val, unit = la.get("value"), norm(la.get("unit"))
            try:
                val = float(val)
            except Exception:
                val = None
            if val is not None:
                if unit in ("sqm", "m2", "mq"):
                    return val * 10.7639
                return val
        for key in ("livingArea", "livingAreaSqft", "livingAreaValue"):
            v = it.get(key)
            try:
                if v is not None:
                    return float(v)
            except Exception:
                pass
        return None

def lot_sqft(it):
        la = it.get("lotArea") or it.get("lot") or it.get("lotSizeObj")
        if isinstance(la, dict):
            val, unit = la.get("value"), norm(la.get("unit"))
            try:
                val = float(val)
            except Exception:
                val = None
            if val is not None:
                if unit in ("acre", "acres", "ac"):
                    return val * 43560.0
                if unit in ("sqm", "m2", "mq"):
                    return val * 10.7639
                return val

        val = it.get("lotSize")
        if val is not None:
            try:
                valf = float(val)
            except Exception:
                valf = None
            if valf is not None:
                unit = norm(it.get("lotSizeUnit"))
                if unit in ("acre", "acres", "ac"):
                    return valf * 43560.0
                if unit in ("sqm", "m2", "mq"):
                    return valf * 10.7639
                return valf

        lot_block = it.get("lotSizeUnit")
        if isinstance(lot_block, dict):
            val, unit = lot_block.get("lotSize"), norm(lot_block.get("lotSizeUnit"))
            try:
                valf = float(val) if val is not None else None
            except Exception:
                valf = None
            if valf is not None:
                if unit in ("acre", "acres", "ac"):
                    return valf * 43560.0
                if unit in ("sqm", "m2", "mq"):
                    return valf * 10.7639
                return valf

        return None

def apply_all_filters(items, allowed, priceMin, priceMax, livingAreaMin, livingAreaMax, lotSizeMin, lotSizeMax, ALIASES):
        out = []
        for it in items:
            t_raw = it.get("propertyType")
            t = ALIASES.get(norm(t_raw), _to_str(t_raw))
            if allowed and t not in allowed:
                continue
            if not in_range(price_value(it), priceMin, priceMax):
                continue
            if not in_range(living_area_sqft(it), livingAreaMin, livingAreaMax):
                continue
            if not in_range(lot_sqft(it), lotSizeMin, lotSizeMax):
                continue
            out.append(it)
        return out
