"""pip install xgboost scikit-learn pandas
Expects CSV with feature columns + binary column `event`."""
import pandas as pd, joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

df = pd.read_csv("data/hazard.csv")
X, y = df.drop(columns=["event"]), df["event"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
model = XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05).fit(Xtr, ytr)
print(classification_report(yte, model.predict(Xte)))
joblib.dump(model, "models/early_warning.joblib")
