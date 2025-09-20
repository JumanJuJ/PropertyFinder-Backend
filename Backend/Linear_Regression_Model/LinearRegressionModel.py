import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
import joblib


INPUT_CSV = "dataset.csv"
CITY_MIN_COUNT = 15  # città con meno di 15 righe vengono escluse

# === 1) Carico dati ===
use_cols = ["city", "price", "livingArea", "lotSizeUnit", "lotSize", "propertyType", "yearBuilt"]
df = pd.read_csv(INPUT_CSV, usecols=use_cols)

# Conversione numerica robusta
for c in ["price", "livingArea", "lotSize", "yearBuilt"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# Drop righe con valori mancanti
df = df.dropna(subset=["price", "livingArea", "lotSize", "yearBuilt", "city", "propertyType"])

# Conversione acres → square feet
mask_acres = df["lotSizeUnit"].str.lower().str.strip() == "acres"
df.loc[mask_acres & df["lotSize"].notna(), "lotSize"] *= 43560

# Rimuovo colonna unità
df = df.drop(columns=["lotSizeUnit"])

# Filtro città con abbastanza dati
city_counts = df["city"].value_counts()
valid_cities = city_counts[city_counts >= CITY_MIN_COUNT].index
df = df[df["city"].isin(valid_cities)]

# elimino estremi della distribuzione per evitare sbilanciamenti
low, high = df["price"].quantile([0.01, 0.99])
df = df[(df["price"] >= low) & (df["price"] <= high)]

# === 2) Definizione X e y ===
y = np.log1p(df["price"])  #normlaizzo il prezzo visto che ha una distribuzione molto sbilanciata
X = df.drop(columns=["price"])

# === 3) Preprocessing ===
num_cols = ["livingArea", "lotSize", "yearBuilt"]
cat_cols = ["propertyType", "city"]

pre = ColumnTransformer(
    transformers=[
        ("num", RobustScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
    ]
)

# === 4) Modello ===
model = Ridge(alpha=5.0, random_state=42) #utilizzo linear regression ridge con alpha medio
pipe = Pipeline(steps=[("pre", pre), ("model", model)])  #converto le stringhe in valori numerici riconoscibili per il modello 

# === 5) Train/test split ===
X_train, X_test, y_train, y_test = train_test_split(  # 80% per addestare, 20% per test
    X, y, test_size=0.2, random_state=42
)

# === 6) Fit ===
pipe.fit(X_train, y_train)

# === 7) Predizioni ===
# riportiamo ai prezzi reali dopo il fit usando exp (inverso di log)
y_pred = np.expm1(pipe.predict(X_test))
y_true = np.expm1(y_test)
y_pred = np.clip(y_pred, 0, None)  # no negativi

# === 8) Metriche ===
mse = mean_squared_error(y_true, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_true, y_pred)
print(f"MSE:  {mse:,.0f}")
print(f"RMSE: {rmse:,.0f}")
print(f"R²:   {r2:0.3f}")

# === 9) Salvataggio confronto ===
pred_df = pd.DataFrame({
    "city": X_test["city"].values,
    "propertyType": X_test["propertyType"].values,
    "livingArea": X_test["livingArea"].values,
    "lotSize": X_test["lotSize"].values,
    "yearBuilt": X_test["yearBuilt"].values,
    "Prezzo Reale": y_true.round(0).astype(int),
    "Prezzo Predetto": y_pred.round(0).astype(int),
})
pred_df.to_csv("predizioni_prezzi.csv", index=False)
print("✅ Predizioni salvate in predizioni_prezzi.csv")

# Calcoliamo errore percentuale medio assoluto (MAPE)
mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
print(f"MAPE: {mape:.2f}%")


# === 10) Salvo il modello ===
joblib.dump(pipe, "linear_model.pkl")


