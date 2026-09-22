import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'model')
MODEL_PATH = os.path.join(MODEL_DIR, 'isolation_forest.pkl')

FEATURE_COLUMNS = [
    'amount',
    'avg_amount',
    'amount_ratio',
    'transactions_10min',
    'new_device',
    'location_change',
    'time_anomaly'
]

_model_cache = None

def get_or_load_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    
    if os.path.exists(MODEL_PATH):
        try:
            _model_cache = joblib.load(MODEL_PATH)
            return _model_cache
        except Exception as e:
            print(f"Error loading model: {e}")
    
    # Train if not found
    return train_model()

def generate_synthetic_training_data(n_samples=2500):
    """
    Generates synthetic financial transaction data to train Isolation Forest.
    Realistic distributions: 92% normal transactions, 8% anomalous transactions.
    """
    np.random.seed(42)
    n_normal = int(n_samples * 0.92)
    n_anomalous = n_samples - n_normal

    # Normal Transactions
    normal_avg_amount = np.random.uniform(1000, 8000, n_normal)
    # normal amount is around 0.3x to 1.8x average
    normal_ratios = np.random.uniform(0.2, 1.8, n_normal)
    normal_amounts = normal_avg_amount * normal_ratios
    normal_freq = np.random.choice([1, 2, 3], size=n_normal, p=[0.75, 0.20, 0.05])
    normal_device = np.random.choice([0, 1], size=n_normal, p=[0.94, 0.06])
    normal_loc = np.random.choice([0, 1], size=n_normal, p=[0.92, 0.08])
    normal_time = np.random.choice([0, 1], size=n_normal, p=[0.90, 0.10])

    normal_df = pd.DataFrame({
        'amount': normal_amounts,
        'avg_amount': normal_avg_amount,
        'amount_ratio': normal_ratios,
        'transactions_10min': normal_freq,
        'new_device': normal_device,
        'location_change': normal_loc,
        'time_anomaly': normal_time
    })

    # Anomalous / Fraud Transactions
    fraud_avg_amount = np.random.uniform(1000, 8000, n_anomalous)
    fraud_ratios = np.random.uniform(3.5, 35.0, n_anomalous)
    fraud_amounts = fraud_avg_amount * fraud_ratios
    fraud_freq = np.random.choice([3, 5, 8, 12], size=n_anomalous, p=[0.15, 0.35, 0.35, 0.15])
    fraud_device = np.random.choice([0, 1], size=n_anomalous, p=[0.15, 0.85])
    fraud_loc = np.random.choice([0, 1], size=n_anomalous, p=[0.10, 0.90])
    fraud_time = np.random.choice([0, 1], size=n_anomalous, p=[0.20, 0.80])

    fraud_df = pd.DataFrame({
        'amount': fraud_amounts,
        'avg_amount': fraud_avg_amount,
        'amount_ratio': fraud_ratios,
        'transactions_10min': fraud_freq,
        'new_device': fraud_device,
        'location_change': fraud_loc,
        'time_anomaly': fraud_time
    })

    full_df = pd.concat([normal_df, fraud_df], ignore_index=True)
    return full_df.sample(frac=1.0, random_state=42).reset_index(drop=True)

def train_model(training_df=None, contamination=0.08):
    global _model_cache
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    if training_df is None or len(training_df) < 50:
        training_df = generate_synthetic_training_data()
        
    X = training_df[FEATURE_COLUMNS]
    
    model = IsolationForest(
        n_estimators=120,
        contamination=contamination,
        max_samples='auto',
        random_state=42
    )
    
    model.fit(X)
    joblib.dump(model, MODEL_PATH)
    _model_cache = model
    print(f"[ML Engine] Isolation Forest trained successfully on {len(X)} records and saved to {MODEL_PATH}")
    return model

def predict_anomaly_score(features_dict):
    """
    Computes anomaly score between 0 and 100 for given features.
    Isolation Forest decision_function: lower (negative) = outlier/anomalous, higher = normal.
    """
    model = get_or_load_model()
    
    amount = float(features_dict.get('amount', 0.0))
    avg_amount = float(features_dict.get('avg_amount', 1.0))
    if avg_amount <= 0:
        avg_amount = 1.0
    amount_ratio = amount / avg_amount
    
    input_data = pd.DataFrame([{
        'amount': amount,
        'avg_amount': avg_amount,
        'amount_ratio': amount_ratio,
        'transactions_10min': int(features_dict.get('transactions_10min', 1)),
        'new_device': 1 if features_dict.get('new_device') in [1, True, '1', 'yes'] else 0,
        'location_change': 1 if features_dict.get('location_change') in [1, True, '1', 'yes'] else 0,
        'time_anomaly': 1 if features_dict.get('time_anomaly') in [1, True, '1', 'yes'] else 0
    }])[FEATURE_COLUMNS]
    
    # decision_function gives values typically in range [-0.5, 0.3]
    raw_score = model.decision_function(input_data)[0]
    
    # Map raw_score to 0 - 100 anomaly scale
    # raw_score ~ 0.25 (very normal) -> 5
    # raw_score ~ 0.0 (borderline)   -> 50
    # raw_score ~ -0.3 (strong anomaly) -> 95
    # Formula: normalized_anomaly = 1.0 / (1.0 + exp(8.0 * raw_score)) * 100
    normalized_anomaly = 1.0 / (1.0 + np.exp(7.5 * raw_score)) * 100.0
    
    # Clamp between 0 and 100
    ml_score = int(np.clip(np.round(normalized_anomaly), 0, 100))
    return ml_score
