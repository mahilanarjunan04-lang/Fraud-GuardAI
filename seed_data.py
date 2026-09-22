import json
import random
from datetime import datetime, timedelta
from database import (
    init_db, get_db_connection, create_user
)
from ml_model import train_model
from fraud_detection import analyze_transaction

def seed_database():
    print(">>> Initializing SQLite Database...")
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data to allow fresh deterministic seeding
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM accounts")
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM system_settings")
    conn.commit()

    # 1. Create Default Admin User
    print(">>> Creating default admin user (admin@fraudguard.ai / admin123)...")
    create_user('admin@fraudguard.ai', 'admin123', name='Rajesh Kumar (Lead Investigator)', role='Administrator')

    # 2. Initialize System Settings
    cursor.execute('''
        INSERT INTO system_settings (rule_weight, ml_weight, auto_alert_threshold, high_risk_threshold, critical_risk_threshold, isolation_contamination)
        VALUES (0.60, 0.40, 60, 61, 81, 0.08)
    ''')
    conn.commit()

    # 3. Create Sample Accounts with distinct behavioral profiles
    print(">>> Seeding Account Behavioral Profiles...")
    sample_accounts = [
        {
            'account_id': 'ACC101',
            'holder_name': 'Aarav Sharma',
            'avg_amount': 3200.0,
            'min_amount': 500.0,
            'max_amount': 8500.0,
            'normal_locations': 'Chennai, Coimbatore',
            'normal_hours': '08:00 - 22:00',
            'known_devices': 2,
            'avg_daily_tx': 3,
            'risk_score': 12,
            'status': 'ACTIVE'
        },
        {
            'account_id': 'ACC102',
            'holder_name': 'Vikram Rathore',
            'avg_amount': 3500.0,
            'min_amount': 400.0,
            'max_amount': 9000.0,
            'normal_locations': 'Chennai, Coimbatore, Erode',
            'normal_hours': '08:00 - 22:00',
            'known_devices': 2,
            'avg_daily_tx': 3,
            'risk_score': 94, # High risk due to Dubai transaction
            'status': 'FLAGGED'
        },
        {
            'account_id': 'ACC105',
            'holder_name': 'Meera Sundaram',
            'avg_amount': 4500.0,
            'min_amount': 800.0,
            'max_amount': 12000.0,
            'normal_locations': 'Bangalore, Chennai',
            'normal_hours': '09:00 - 21:00',
            'known_devices': 3,
            'avg_daily_tx': 4,
            'risk_score': 65,
            'status': 'FLAGGED'
        },
        {
            'account_id': 'ACC108',
            'holder_name': 'Kavita Menon',
            'avg_amount': 2800.0,
            'min_amount': 300.0,
            'max_amount': 7500.0,
            'normal_locations': 'Chennai, Erode',
            'normal_hours': '07:30 - 21:30',
            'known_devices': 1,
            'avg_daily_tx': 2,
            'risk_score': 78,
            'status': 'FLAGGED'
        },
        {
            'account_id': 'ACC109',
            'holder_name': 'Sanjay Varma',
            'avg_amount': 5500.0,
            'min_amount': 1000.0,
            'max_amount': 18000.0,
            'normal_locations': 'Bangalore, Mumbai',
            'normal_hours': '09:00 - 23:00',
            'known_devices': 2,
            'avg_daily_tx': 5,
            'risk_score': 85,
            'status': 'FLAGGED'
        },
        {
            'account_id': 'ACC112',
            'holder_name': 'Pooja Iyer',
            'avg_amount': 1800.0,
            'min_amount': 200.0,
            'max_amount': 5000.0,
            'normal_locations': 'Coimbatore, Erode',
            'normal_hours': '08:00 - 20:00',
            'known_devices': 1,
            'avg_daily_tx': 2,
            'risk_score': 15,
            'status': 'ACTIVE'
        },
        {
            'account_id': 'ACC115',
            'holder_name': 'Anand Swaminathan',
            'avg_amount': 6200.0,
            'min_amount': 1500.0,
            'max_amount': 20000.0,
            'normal_locations': 'Mumbai, Delhi',
            'normal_hours': '09:00 - 22:30',
            'known_devices': 3,
            'avg_daily_tx': 4,
            'risk_score': 22,
            'status': 'ACTIVE'
        },
        {
            'account_id': 'ACC121',
            'holder_name': 'Deepak Balaji',
            'avg_amount': 2200.0,
            'min_amount': 300.0,
            'max_amount': 6000.0,
            'normal_locations': 'Chennai, Vellore',
            'normal_hours': '08:30 - 21:00',
            'known_devices': 2,
            'avg_daily_tx': 3,
            'risk_score': 68,
            'status': 'UNDER_REVIEW'
        },
        {
            'account_id': 'ACC124',
            'holder_name': 'Sneha Nair',
            'avg_amount': 3800.0,
            'min_amount': 500.0,
            'max_amount': 10000.0,
            'normal_locations': 'Bangalore, Mysore',
            'normal_hours': '08:00 - 22:00',
            'known_devices': 2,
            'avg_daily_tx': 3,
            'risk_score': 18,
            'status': 'ACTIVE'
        },
        {
            'account_id': 'ACC130',
            'holder_name': 'Gautam Patel',
            'avg_amount': 8500.0,
            'min_amount': 2000.0,
            'max_amount': 25000.0,
            'normal_locations': 'Mumbai, Ahmedabad',
            'normal_hours': '09:00 - 23:00',
            'known_devices': 3,
            'avg_daily_tx': 5,
            'risk_score': 32,
            'status': 'ACTIVE'
        }
    ]

    for acc in sample_accounts:
        cursor.execute('''
            INSERT INTO accounts (account_id, holder_name, avg_amount, min_amount, max_amount, normal_locations, normal_hours, known_devices, avg_daily_tx, risk_score, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            acc['account_id'], acc['holder_name'], acc['avg_amount'], acc['min_amount'], acc['max_amount'],
            acc['normal_locations'], acc['normal_hours'], acc['known_devices'], acc['avg_daily_tx'], acc['risk_score'], acc['status']
        ))
    conn.commit()

    # 4. Train the Isolation Forest Model
    print(">>> Training and persisting ML Model...")
    train_model()

    # 5. Generate 60+ Realistic Transactions
    print(">>> Seeding 60+ Transactions spanning all risk levels...")
    
    # Specific key transactions from prompt requirement
    promoted_transactions = [
        {
            'transaction_id': 'TX10045',
            'account_id': 'ACC102',
            'recipient_account_id': 'ACC105',
            'amount': 75000.0,
            'location': 'Dubai',
            'time_str': '02:30 AM',
            'device': 'New iPhone 15 Pro (Dubai Gateway)',
            'new_device': 1,
            'transactions_10min': 8,
            'force_score': 94,
            'force_level': 'CRITICAL'
        },
        {
            'transaction_id': 'TX10046',
            'account_id': 'ACC108',
            'recipient_account_id': 'ACC109',
            'amount': 45000.0,
            'location': 'Delhi',
            'time_str': '03:15 AM',
            'device': 'Unregistered Linux Browser',
            'new_device': 1,
            'transactions_10min': 5,
            'force_score': 78,
            'force_level': 'HIGH'
        },
        {
            'transaction_id': 'TX10047',
            'account_id': 'ACC121',
            'recipient_account_id': 'ACC102',
            'amount': 18500.0,
            'location': 'Chennai',
            'time_str': '11:45 PM',
            'device': 'Registered Android App',
            'new_device': 0,
            'transactions_10min': 6,
            'force_score': 68,
            'force_level': 'HIGH'
        },
        {
            'transaction_id': 'TX10048',
            'account_id': 'ACC101',
            'recipient_account_id': 'ACC102',
            'amount': 2850.0,
            'location': 'Chennai',
            'time_str': '01:15 PM',
            'device': 'Pixel 8 Pro (Primary)',
            'new_device': 0,
            'transactions_10min': 1,
            'force_score': 12,
            'force_level': 'LOW'
        },
        {
            'transaction_id': 'TX10049',
            'account_id': 'ACC105',
            'recipient_account_id': 'ACC109',
            'amount': 88000.0,
            'location': 'Dubai',
            'time_str': '04:10 AM',
            'device': 'Unknown Tor Exit Node',
            'new_device': 1,
            'transactions_10min': 7,
            'force_score': 96,
            'force_level': 'CRITICAL'
        }
    ]

    devices_pool = [
        'Samsung Galaxy S23 (Primary)',
        'Apple iPhone 14 (Registered)',
        'Chrome Windows 11 (Home Desktop)',
        'MacBook Pro Safari (Work)',
        'iPad Pro (Trusted Tablet)',
        'Unregistered Android Emulator',
        'New Device - Unknown Web Client',
        'Firefox Linux (Untrusted Proxy)'
    ]

    locations_pool = ['Chennai', 'Coimbatore', 'Erode', 'Bangalore', 'Mumbai', 'Delhi', 'Dubai']
    hours_pool = ['08:30 AM', '10:15 AM', '12:45 PM', '02:20 PM', '04:50 PM', '07:10 PM', '09:30 PM', '11:55 PM', '02:15 AM', '04:40 AM']

    account_keys = [a['account_id'] for a in sample_accounts]

    # Generate additional 55 transactions
    all_raw_txs = list(promoted_transactions)
    
    for i in range(50, 105):
        tx_id = f"TX100{i:02d}"
        acc_id = random.choice(account_keys)
        recip_id = random.choice([x for x in account_keys if x != acc_id])
        acc_meta = next(a for a in sample_accounts if a['account_id'] == acc_id)
        
        # Decide if this transaction is normal, high, or medium
        tier = random.choices(['normal', 'medium', 'high', 'critical'], weights=[0.68, 0.16, 0.10, 0.06])[0]
        
        if tier == 'normal':
            amount = round(random.uniform(acc_meta['min_amount'], acc_meta['max_amount'] * 0.8), 2)
            location = random.choice(acc_meta['normal_locations'].split(', ')).strip()
            time_str = random.choice(['09:15 AM', '11:30 AM', '02:00 PM', '04:30 PM', '06:15 PM', '08:45 PM'])
            device = random.choice(devices_pool[:5])
            new_dev = 0
            tx_10m = random.choice([1, 1, 2])
        elif tier == 'medium':
            amount = round(random.uniform(acc_meta['max_amount'] * 0.9, acc_meta['max_amount'] * 1.8), 2)
            location = random.choice(locations_pool)
            time_str = random.choice(['10:30 PM', '11:15 PM', '07:00 AM'])
            device = random.choice(devices_pool)
            new_dev = 1 if 'Unregistered' in device or 'New' in device else 0
            tx_10m = random.choice([2, 3, 4])
        elif tier == 'high':
            amount = round(random.uniform(35000, 65000), 2)
            location = random.choice(['Delhi', 'Mumbai', 'Bangalore', 'Dubai'])
            time_str = random.choice(['11:45 PM', '01:20 AM', '03:40 AM', '05:10 AM'])
            device = random.choice(devices_pool[5:])
            new_dev = 1
            tx_10m = random.choice([4, 5, 6])
        else: # critical
            amount = round(random.uniform(70000, 150000), 2)
            location = 'Dubai' if random.random() > 0.3 else 'Delhi'
            time_str = random.choice(['01:45 AM', '02:30 AM', '03:15 AM', '04:00 AM'])
            device = random.choice(devices_pool[5:])
            new_dev = 1
            tx_10m = random.choice([6, 7, 8, 10])

        all_raw_txs.append({
            'transaction_id': tx_id,
            'account_id': acc_id,
            'recipient_account_id': recip_id,
            'amount': amount,
            'location': location,
            'time_str': time_str,
            'device': device,
            'new_device': new_dev,
            'transactions_10min': tx_10m
        })

    # Process and insert all transactions through the fraud engine
    alert_counter = 1
    for raw in all_raw_txs:
        # If force score is present (from prompt examples), honor it or compute
        analysis = analyze_transaction(raw)
        
        if 'force_score' in raw:
            risk_score = raw['force_score']
            risk_level = raw['force_level']
        else:
            risk_score = analysis['risk_score']
            risk_level = analysis['risk_level']

        status = 'CRITICAL' if risk_level == 'CRITICAL' else ('SUSPICIOUS' if risk_level == 'HIGH' else ('REVIEW' if risk_level == 'MEDIUM' else 'NORMAL'))

        cursor.execute('''
            INSERT INTO transactions (
                transaction_id, account_id, recipient_account_id, amount, avg_amount,
                location, time_str, device, new_device, transactions_10min,
                rule_score, ml_score, risk_score, risk_level, status, flagged_reasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            raw['transaction_id'], raw['account_id'], raw['recipient_account_id'],
            raw['amount'], analysis['avg_amount'], raw['location'], raw['time_str'],
            raw['device'], raw['new_device'], raw['transactions_10min'],
            analysis['rule_score'], analysis['ml_score'], risk_score, risk_level, status,
            json.dumps(analysis['flagged_reasons'])
        ))

        # Create alert if HIGH or CRITICAL
        if risk_level in ['HIGH', 'CRITICAL']:
            alert_id = f"ALT-{1000 + alert_counter}"
            alert_counter += 1
            reason_summaries = [r['title'] for r in analysis['flagged_reasons']]
            msg = f"₹{raw['amount']:,.0f} transaction flagged with {risk_level} risk score of {risk_score}/100 from {raw['location']}."
            
            cursor.execute('''
                INSERT INTO alerts (alert_id, transaction_id, account_id, severity, message, reasons, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert_id, raw['transaction_id'], raw['account_id'], risk_level,
                msg, json.dumps(reason_summaries), 'PENDING'
            ))

    conn.commit()
    conn.close()
    print(">>> Seeding completed successfully with rich accounts, transactions, and security alerts!")

if __name__ == '__main__':
    seed_database()
