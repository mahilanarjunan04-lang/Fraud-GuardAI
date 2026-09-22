import sqlite3
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'fraudguard.db')

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'Administrator',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Drop old accounts table if it lacks new columns
    try:
        cursor.execute("SELECT call_attempts, hold_reason FROM accounts LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("DROP TABLE IF EXISTS accounts")

    # Accounts table with full workflow states: ACTIVE, ACCOUNT_HOLD, ADMIN_REVIEW, BLOCKED
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT UNIQUE NOT NULL,
            holder_name TEXT NOT NULL,
            phone_number TEXT DEFAULT '+91 98450 12345',
            email TEXT DEFAULT 'customer@bank.com',
            avg_amount REAL DEFAULT 2500.0,
            min_amount REAL DEFAULT 500.0,
            max_amount REAL DEFAULT 15000.0,
            normal_locations TEXT DEFAULT 'Chennai, Coimbatore',
            normal_hours TEXT DEFAULT '08:00 - 22:00',
            known_devices INTEGER DEFAULT 2,
            avg_daily_tx INTEGER DEFAULT 3,
            risk_score INTEGER DEFAULT 10,
            status TEXT DEFAULT 'ACTIVE', -- ACTIVE, ACCOUNT_HOLD, ADMIN_REVIEW, BLOCKED, FLAGGED
            call_attempts INTEGER DEFAULT 0,
            last_call_status TEXT DEFAULT 'NONE',
            hold_reason TEXT DEFAULT '',
            block_reason TEXT DEFAULT '',
            held_at TIMESTAMP,
            blocked_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            account_id TEXT NOT NULL,
            recipient_account_id TEXT,
            amount REAL NOT NULL,
            avg_amount REAL NOT NULL,
            location TEXT NOT NULL,
            time_str TEXT NOT NULL,
            device TEXT NOT NULL,
            new_device INTEGER DEFAULT 0,
            transactions_10min INTEGER DEFAULT 1,
            rule_score INTEGER DEFAULT 0,
            ml_score INTEGER DEFAULT 0,
            risk_score INTEGER DEFAULT 0,
            risk_level TEXT DEFAULT 'LOW',
            status TEXT DEFAULT 'NORMAL', -- NORMAL, REVIEW, SUSPICIOUS, CRITICAL, HELD, BLOCKED
            flagged_reasons TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT UNIQUE NOT NULL,
            transaction_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            reasons TEXT DEFAULT '[]',
            status TEXT DEFAULT 'PENDING', -- PENDING, UNDER_INVESTIGATION, ADMIN_REVIEW, RESOLVED, DISMISSED
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
        )
    ''')

    # Customer Communications Table (Calls & SMS logs)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_communications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT NOT NULL,
            transaction_id TEXT,
            type TEXT NOT NULL, -- CALL_ATTEMPT_1, CALL_ATTEMPT_2, SMS, WHATSAPP, ADMIN_REVIEW
            recipient_contact TEXT NOT NULL,
            message_content TEXT NOT NULL,
            status TEXT DEFAULT 'DELIVERED', -- DELIVERED, ATTENDED_VERIFIED, NOT_ATTENDED, AUTO_HELD, BLOCKED, UNHELD
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # System settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_weight REAL DEFAULT 0.6,
            ml_weight REAL DEFAULT 0.4,
            auto_alert_threshold INTEGER DEFAULT 60,
            auto_block_threshold INTEGER DEFAULT 81,
            high_risk_threshold INTEGER DEFAULT 61,
            critical_risk_threshold INTEGER DEFAULT 81,
            isolation_contamination REAL DEFAULT 0.08,
            max_call_attempts INTEGER DEFAULT 2,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def create_user(email, password, name='Administrator', role='Administrator'):
    conn = get_db_connection()
    password_hash = generate_password_hash(password)
    try:
        conn.execute(
            'INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)',
            (email, password_hash, name, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_account_profile(account_id):
    conn = get_db_connection()
    account = conn.execute('SELECT * FROM accounts WHERE account_id = ?', (account_id,)).fetchone()
    conn.close()
    return account

def get_all_accounts():
    conn = get_db_connection()
    accounts = conn.execute('SELECT * FROM accounts ORDER BY (CASE WHEN status="BLOCKED" THEN 0 WHEN status="ACCOUNT_HOLD" THEN 1 WHEN status="ADMIN_REVIEW" THEN 2 ELSE 3 END), risk_score DESC').fetchall()
    conn.close()
    return [dict(acc) for acc in accounts]

def set_account_hold(account_id, reason="Customer verification call unattended (2 attempts). Placed on automated security hold."):
    conn = get_db_connection()
    conn.execute('''
        UPDATE accounts 
        SET status = 'ACCOUNT_HOLD', hold_reason = ?, held_at = CURRENT_TIMESTAMP
        WHERE account_id = ?
    ''', (reason, account_id))
    conn.commit()
    conn.close()

def set_account_admin_review(account_id):
    conn = get_db_connection()
    conn.execute('''
        UPDATE accounts 
        SET status = 'ADMIN_REVIEW'
        WHERE account_id = ?
    ''', (account_id,))
    conn.commit()
    conn.close()

def set_account_blocked(account_id, reason="Critical fraud confirmed by Admin Review"):
    conn = get_db_connection()
    conn.execute('''
        UPDATE accounts 
        SET status = 'BLOCKED', block_reason = ?, blocked_at = CURRENT_TIMESTAMP
        WHERE account_id = ?
    ''', (reason, account_id))
    conn.commit()
    conn.close()

def set_account_unhold(account_id):
    conn = get_db_connection()
    conn.execute('''
        UPDATE accounts 
        SET status = 'ACTIVE', hold_reason = NULL, block_reason = NULL, held_at = NULL, blocked_at = NULL, call_attempts = 0, last_call_status = 'VERIFIED_SAFE'
        WHERE account_id = ?
    ''', (account_id,))
    conn.commit()
    conn.close()

def set_account_unblocked(account_id):
    set_account_unhold(account_id)

def increment_call_attempt(account_id, outcome):
    conn = get_db_connection()
    conn.execute('''
        UPDATE accounts 
        SET call_attempts = call_attempts + 1, last_call_status = ?
        WHERE account_id = ?
    ''', (outcome, account_id))
    conn.commit()
    conn.close()

def log_customer_communication(account_id, tx_id, comm_type, contact, message, status='DELIVERED', response=None):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO customer_communications (account_id, transaction_id, type, recipient_contact, message_content, status, response)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (account_id, tx_id, comm_type, contact, message, status, response))
    conn.commit()
    conn.close()

def get_communications_for_account(account_id):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM customer_communications WHERE account_id = ? ORDER BY id DESC', (account_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_transactions(limit=100, offset=0, filter_risk=None, filter_location=None, filter_status=None, search=None):
    conn = get_db_connection()
    query = 'SELECT * FROM transactions WHERE 1=1'
    params = []

    if filter_risk and filter_risk != 'ALL':
        query += ' AND risk_level = ?'
        params.append(filter_risk)

    if filter_location and filter_location != 'ALL':
        query += ' AND location = ?'
        params.append(filter_location)

    if filter_status and filter_status != 'ALL':
        query += ' AND status = ?'
        params.append(filter_status)

    if search:
        query += ' AND (transaction_id LIKE ? OR account_id LIKE ? OR location LIKE ?)'
        term = f'%{search}%'
        params.extend([term, term, term])

    query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    
    count_query = 'SELECT COUNT(*) as total FROM transactions WHERE 1=1'
    count_params = params[:-2]
    
    if filter_risk and filter_risk != 'ALL':
        count_query += ' AND risk_level = ?'
    if filter_location and filter_location != 'ALL':
        count_query += ' AND location = ?'
    if filter_status and filter_status != 'ALL':
        count_query += ' AND status = ?'
    if search:
        count_query += ' AND (transaction_id LIKE ? OR account_id LIKE ? OR location LIKE ?)'

    total = conn.execute(count_query, count_params).fetchone()['total']
    conn.close()
    return [dict(r) for r in rows], total

def get_transaction_by_id(tx_id):
    conn = get_db_connection()
    tx = conn.execute('SELECT * FROM transactions WHERE transaction_id = ? OR id = ?', (tx_id, tx_id)).fetchone()
    conn.close()
    return dict(tx) if tx else None

def get_transactions_for_account(account_id):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM transactions WHERE account_id = ? OR recipient_account_id = ? ORDER BY id DESC', (account_id, account_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_alerts(status_filter=None):
    conn = get_db_connection()
    if status_filter and status_filter != 'ALL':
        rows = conn.execute('SELECT * FROM alerts WHERE status = ? ORDER BY id DESC', (status_filter,)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM alerts ORDER BY id DESC').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_alert_status(alert_id, new_status):
    conn = get_db_connection()
    conn.execute('UPDATE alerts SET status = ? WHERE alert_id = ? OR id = ?', (new_status, alert_id, alert_id))
    conn.commit()
    conn.close()

def get_dashboard_metrics():
    conn = get_db_connection()
    total_tx = conn.execute('SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total_val FROM transactions').fetchone()
    suspicious_tx = conn.execute('SELECT COUNT(*) as count FROM transactions WHERE risk_level IN ("HIGH", "CRITICAL")').fetchone()
    critical_tx = conn.execute('SELECT COUNT(*) as count FROM transactions WHERE risk_level = "CRITICAL"').fetchone()
    high_tx = conn.execute('SELECT COUNT(*) as count FROM transactions WHERE risk_level = "HIGH"').fetchone()
    medium_tx = conn.execute('SELECT COUNT(*) as count FROM transactions WHERE risk_level = "MEDIUM"').fetchone()
    low_tx = conn.execute('SELECT COUNT(*) as count FROM transactions WHERE risk_level = "LOW"').fetchone()
    pending_alerts = conn.execute('SELECT COUNT(*) as count FROM alerts WHERE status = "PENDING"').fetchone()
    held_accounts = conn.execute('SELECT COUNT(*) as count FROM accounts WHERE status = "ACCOUNT_HOLD"').fetchone()
    blocked_accounts = conn.execute('SELECT COUNT(*) as count FROM accounts WHERE status = "BLOCKED"').fetchone()

    total_count = total_tx['count']
    total_value = total_tx['total_val']
    suspicious_count = suspicious_tx['count']
    critical_count = critical_tx['count']
    high_count = high_tx['count']
    medium_count = medium_tx['count']
    low_count = low_tx['count']
    held_count = held_accounts['count']
    blocked_count = blocked_accounts['count']

    fraud_rate = (suspicious_count / total_count * 100) if total_count > 0 else 0.0

    if total_value >= 10000000:
        formatted_value = f"₹{total_value / 10000000:.2f} Cr"
    elif total_value >= 100000:
        formatted_value = f"₹{total_value / 100000:.2f} L"
    else:
        formatted_value = f"₹{total_value:,.2f}"

    conn.close()

    return {
        'total_transactions': total_count,
        'suspicious_transactions': suspicious_count,
        'critical_transactions': critical_count,
        'high_transactions': high_count,
        'medium_transactions': medium_count,
        'low_transactions': low_count,
        'held_accounts': held_count,
        'blocked_accounts': blocked_count,
        'total_value': total_value,
        'formatted_value': formatted_value,
        'fraud_detection_rate': round(fraud_rate, 1),
        'pending_alerts': pending_alerts['count']
    }

def get_system_settings():
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM system_settings ORDER BY id DESC LIMIT 1').fetchone()
    if not row:
        conn.execute('INSERT INTO system_settings (rule_weight, ml_weight, auto_block_threshold) VALUES (0.6, 0.4, 81)')
        conn.commit()
        row = conn.execute('SELECT * FROM system_settings ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    return dict(row)

def update_system_settings(rule_weight, ml_weight, auto_alert_threshold, high_threshold, crit_threshold, auto_block=81):
    conn = get_db_connection()
    conn.execute('''
        UPDATE system_settings 
        SET rule_weight = ?, ml_weight = ?, auto_alert_threshold = ?, high_risk_threshold = ?, critical_risk_threshold = ?, auto_block_threshold = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''', (rule_weight, ml_weight, auto_alert_threshold, high_threshold, crit_threshold, auto_block))
    conn.commit()
    conn.close()
