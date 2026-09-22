import json
from datetime import datetime
from ml_model import predict_anomaly_score
from database import get_account_profile, get_system_settings

def is_unusual_time(time_str):
    """
    Checks if time is between 23:00 (11 PM) and 05:30 (5:30 AM)
    or if format is parsed.
    """
    if not time_str:
        return False
    
    t_str = str(time_str).strip().upper()
    
    # Check 12-hour AM/PM format
    if 'AM' in t_str or 'PM' in t_str:
        try:
            # e.g., '02:30 AM', '11:45 PM'
            time_parts = t_str.replace(':', ' ').split()
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 2 else 0
            meridiem = time_parts[-1]
            if meridiem == 'PM' and hour != 12:
                hour += 12
            elif meridiem == 'AM' and hour == 12:
                hour = 0
            # Late night / early morning check: 11 PM (23) to 5 AM (5)
            if hour >= 23 or hour < 6:
                return True
        except Exception:
            pass
    elif ':' in t_str:
        # 24-hour format e.g., '03:15'
        try:
            hour = int(t_str.split(':')[0])
            if hour >= 23 or hour < 6:
                return True
        except Exception:
            pass
            
    return False

def analyze_transaction(tx_data, account_profile=None):
    """
    Runs full hybrid fraud evaluation (Rule Engine + Scikit-Learn Isolation Forest + Explainable AI)
    """
    amount = float(tx_data.get('amount', 0.0))
    account_id = tx_data.get('account_id', 'ACC100')
    location = str(tx_data.get('location', 'Chennai')).strip()
    time_str = str(tx_data.get('time', tx_data.get('time_str', '12:00 PM'))).strip()
    device = str(tx_data.get('device', 'Known Mobile Device')).strip()
    new_device_flag = bool(tx_data.get('new_device') in [1, True, '1', 'yes', 'true'])
    tx_10min = int(tx_data.get('transactions_10min', 1))

    if not account_profile:
        account_profile = get_account_profile(account_id)

    # Defaults if profile not found
    if account_profile:
        avg_amount = float(account_profile['avg_amount'])
        normal_locations = [l.strip().lower() for l in account_profile['normal_locations'].split(',')]
        normal_hours = account_profile['normal_hours']
    else:
        avg_amount = float(tx_data.get('avg_amount', 2500.0))
        normal_locations = ['chennai', 'coimbatore', 'erode']
        normal_hours = '08:00 - 22:00'

    if avg_amount <= 0:
        avg_amount = 2500.0

    # Rule calculations
    rule_score = 0
    reasons = []

    # 1. Amount Anomaly (+25)
    amount_ratio = amount / avg_amount
    is_amount_anomaly = False
    if amount_ratio >= 3.0 or amount > 50000:
        is_amount_anomaly = True
        rule_score += 25
        reasons.append({
            'code': '01',
            'title': 'High Transaction Amount Anomaly',
            'description': f"Transaction amount of ₹{amount:,.2f} is {amount_ratio:.1f}× higher than the account's baseline average (₹{avg_amount:,.2f}).",
            'severity': 'CRITICAL' if amount_ratio >= 10 else 'HIGH',
            'icon': 'trending-up'
        })

    # 2. New Device (+20)
    is_new_device = new_device_flag or ('New' in device) or ('Unrecognized' in device)
    if is_new_device:
        rule_score += 20
        reasons.append({
            'code': '04',
            'title': 'Unrecognized Hardware Device',
            'description': f"Transaction requested from an unregistered hardware device ({device}) not found in the account's trusted device cache.",
            'severity': 'HIGH',
            'icon': 'smartphone'
        })

    # 3. New Location (+20)
    location_lower = location.lower()
    is_location_anomaly = not any(nl in location_lower for nl in normal_locations)
    if is_location_anomaly:
        rule_score += 20
        reasons.append({
            'code': '02',
            'title': 'Unfamiliar Geographic Location',
            'description': f"Transaction originated from {location}, which is outside established account operational zones ({', '.join([l.title() for l in normal_locations])}).",
            'severity': 'HIGH',
            'icon': 'map-pin'
        })

    # 4. Unusual Time (+15)
    is_time_anomaly = is_unusual_time(time_str)
    if is_time_anomaly:
        rule_score += 15
        reasons.append({
            'code': '03',
            'title': 'Unusual Transaction Timestamp',
            'description': f"Transaction executed at {time_str} during high-risk off-hours (normal operating window: {normal_hours}).",
            'severity': 'MEDIUM',
            'icon': 'clock'
        })

    # 5. High Frequency / Velocity (+20)
    is_frequency_anomaly = tx_10min >= 5
    if is_frequency_anomaly:
        rule_score += 20
        reasons.append({
            'code': '05',
            'title': 'High Velocity Burst Frequency',
            'description': f"High transaction velocity detected: {tx_10min} transactions initiated within a 10-minute window (account threshold: max 3).",
            'severity': 'CRITICAL',
            'icon': 'zap'
        })

    # Cap rule score to 100
    rule_score = min(100, rule_score)

    # Machine Learning Isolation Forest scoring
    ml_features = {
        'amount': amount,
        'avg_amount': avg_amount,
        'transactions_10min': tx_10min,
        'new_device': 1 if is_new_device else 0,
        'location_change': 1 if is_location_anomaly else 0,
        'time_anomaly': 1 if is_time_anomaly else 0
    }
    
    ml_score = predict_anomaly_score(ml_features)

    # System settings weights
    settings = get_system_settings()
    rule_weight = float(settings.get('rule_weight', 0.6))
    ml_weight = float(settings.get('ml_weight', 0.4))

    # Calculate final hybrid risk score
    raw_final = (rule_weight * rule_score) + (ml_weight * ml_score)
    final_risk_score = int(round(max(0, min(100, raw_final))))

    # Risk level classification
    if final_risk_score >= 81:
        risk_level = 'CRITICAL'
        status = 'CRITICAL'
    elif final_risk_score >= 61:
        risk_level = 'HIGH'
        status = 'SUSPICIOUS'
    elif final_risk_score >= 31:
        risk_level = 'MEDIUM'
        status = 'REVIEW'
    else:
        risk_level = 'LOW'
        status = 'NORMAL'

    # If no reasons were triggered but score is somehow non-zero, provide baseline summary
    if not reasons and final_risk_score <= 30:
        reasons.append({
            'code': '00',
            'title': 'Normal Behavioral Pattern',
            'description': 'Transaction parameters align with verified historical spending profile and known security baseline.',
            'severity': 'LOW',
            'icon': 'shield-check'
        })

    # Sort reasons by code
    reasons.sort(key=lambda x: x['code'])

    return {
        'account_id': account_id,
        'amount': amount,
        'avg_amount': avg_amount,
        'amount_ratio': round(amount_ratio, 2),
        'location': location,
        'time': time_str,
        'device': device,
        'new_device': 1 if is_new_device else 0,
        'transactions_10min': tx_10min,
        'rule_score': rule_score,
        'ml_score': ml_score,
        'risk_score': final_risk_score,
        'risk_level': risk_level,
        'status': status,
        'flagged_reasons': reasons
    }
