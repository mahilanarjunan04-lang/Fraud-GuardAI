import os
import io
import csv
import json
import random
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, flash, send_file, Response
)
from werkzeug.security import check_password_hash
from database import (
    init_db, get_user_by_email, get_dashboard_metrics,
    get_all_transactions, get_transaction_by_id, get_all_accounts,
    get_account_profile, get_account_by_identifier, get_transactions_for_account,
    get_all_alerts, update_alert_status, get_system_settings, update_system_settings,
    get_db_connection, set_account_blocked, set_account_hold, set_account_unhold,
    set_account_admin_review, increment_call_attempt, log_customer_communication,
    get_communications_for_account, generate_otp, verify_otp_code, process_sms_decision
)
from fraud_detection import analyze_transaction
from ml_model import get_or_load_model

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fraudguard-ai-hackathon-2026-secret-key-3f1b0989')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required. Please log in.'}), 401
            return redirect(url_for('login_view', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================================
# PUBLIC WEB ROUTES
# ==========================================================

@app.route('/')
def landing_page():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        auth_mode = request.form.get('auth_mode', 'otp')
        
        if auth_mode == 'otp':
            identifier = request.form.get('identifier', '').strip()
            otp_code = request.form.get('otp_code', '').strip()
            
            if not identifier or not otp_code:
                flash('Please enter Account Number / Mobile Number and the 6-digit OTP.', 'warning')
                return render_template('login.html', identifier=identifier, auth_mode='otp')
                
            is_valid, account = verify_otp_code(identifier, otp_code)
            if is_valid and account:
                session['user_id'] = account['account_id']
                session['user_email'] = account.get('email', 'customer@bank.com')
                session['user_name'] = account['holder_name']
                session['user_role'] = 'Verified Customer'
                session['user_account_id'] = account['account_id']
                session['user_phone'] = account.get('phone_number', '+91 8148534339')
                flash(f"Welcome back, {account['holder_name']}! Signed in via OTP verification.", 'success')
                return redirect(url_for('dashboard_view'))
            else:
                flash('Invalid OTP code. Please enter the active 6-digit OTP sent to your phone (or 123456).', 'danger')
                return render_template('login.html', identifier=identifier, auth_mode='otp')
        else: # analyst email login
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            
            user = get_user_by_email(email)
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['user_name'] = user['name']
                session['user_role'] = user['role']
                flash('Signed in successfully as Lead Investigator.', 'success')
                return redirect(url_for('dashboard_view'))
            else:
                flash('Invalid email or password. Use admin@fraudguard.ai / admin123 for demo.', 'danger')
                return render_template('login.html', email=email, auth_mode='analyst')
            
    return render_template('login.html', identifier='8148534339', auth_mode='otp')

@app.route('/logout')
def logout_view():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('landing_page'))

# ==========================================================
# AUTHENTICATED WEB DASHBOARD ROUTES
# ==========================================================

@app.route('/dashboard')
@login_required
def dashboard_view():
    metrics = get_dashboard_metrics()
    recent_txs, _ = get_all_transactions(limit=10)
    alerts = get_all_alerts(status_filter='PENDING')[:5]
    all_accounts = get_all_accounts()
    admin_review_queue = [a for a in all_accounts if a['status'] in ['ACCOUNT_HOLD', 'ADMIN_REVIEW']]
    return render_template('dashboard.html', metrics=metrics, recent_transactions=recent_txs, alerts=alerts, review_queue=admin_review_queue)

@app.route('/transactions')
@login_required
def transactions_view():
    risk_filter = request.args.get('risk', 'ALL')
    location_filter = request.args.get('location', 'ALL')
    status_filter = request.args.get('status', 'ALL')
    search_query = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 15
    offset = (page - 1) * per_page

    tx_list, total_count = get_all_transactions(
        limit=per_page,
        offset=offset,
        filter_risk=risk_filter,
        filter_location=location_filter,
        filter_status=status_filter,
        search=search_query
    )

    total_pages = max(1, (total_count + per_page - 1) // per_page)

    return render_template(
        'transactions.html',
        transactions=tx_list,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
        risk_filter=risk_filter,
        location_filter=location_filter,
        status_filter=status_filter,
        search_query=search_query
    )

@app.route('/transactions/<tx_id>')
@login_required
def transaction_details_view(tx_id):
    tx = get_transaction_by_id(tx_id)
    if not tx:
        flash(f'Transaction {tx_id} not found.', 'warning')
        return redirect(url_for('transactions_view'))

    account = get_account_profile(tx['account_id'])
    
    try:
        flagged_reasons = json.loads(tx['flagged_reasons']) if tx['flagged_reasons'] else []
    except Exception:
        flagged_reasons = []

    account_history = get_transactions_for_account(tx['account_id'])[:6]
    communications = get_communications_for_account(tx['account_id'])

    return render_template(
        'transaction_details.html',
        tx=tx,
        account=dict(account) if account else None,
        reasons=flagged_reasons,
        account_history=account_history,
        communications=communications
    )

@app.route('/accounts')
@login_required
def accounts_view():
    accounts_list = get_all_accounts()
    return render_template('accounts.html', accounts=accounts_list)

@app.route('/accounts/<account_id>')
@login_required
def account_details_view(account_id):
    account = get_account_profile(account_id)
    if not account:
        flash(f'Account {account_id} not found.', 'warning')
        return redirect(url_for('accounts_view'))

    account_txs = get_transactions_for_account(account_id)
    suspicious_count = sum(1 for t in account_txs if t['risk_level'] in ['HIGH', 'CRITICAL'])
    communications = get_communications_for_account(account_id)

    return render_template(
        'account_details.html',
        account=dict(account),
        transactions=account_txs,
        suspicious_count=suspicious_count,
        communications=communications
    )

@app.route('/analytics')
@login_required
def analytics_view():
    metrics = get_dashboard_metrics()
    return render_template('analytics.html', metrics=metrics)

@app.route('/alerts')
@login_required
def alerts_view():
    status_filter = request.args.get('status', 'ALL')
    alerts_list = get_all_alerts(status_filter=status_filter)
    
    for a in alerts_list:
        try:
            a['reasons_list'] = json.loads(a['reasons']) if a['reasons'] else []
        except Exception:
            a['reasons_list'] = []

    return render_template('alerts.html', alerts=alerts_list, status_filter=status_filter)

@app.route('/upload')
@login_required
def upload_view():
    return render_template('upload.html')

@app.route('/presentation')
def presentation_view():
    return render_template('presentation.html')

@app.route('/download-ppt')
def download_ppt():
    ppt_path = os.path.join(os.path.dirname(__file__), 'FraudGuard_AI_Presentation.pptx')
    if not os.path.exists(ppt_path):
        from generate_ppt import create_presentation
        create_presentation()
    return send_file(ppt_path, as_attachment=True, download_name='FraudGuard_AI_Presentation.pptx')

@app.route('/settings')
@login_required
def settings_view():
    settings = get_system_settings()
    return render_template('settings.html', settings=settings)

# ==========================================================
# REST API: MULTI-STAGE USER CALL & ADMIN REVIEW WORKFLOW
# ==========================================================

# ==========================================================
# REST API: OTP AUTHENTICATION & VERIFICATION
# ==========================================================

@app.route('/api/auth/send-otp', methods=['POST'])
def api_send_otp():
    """
    Generates and returns 6-digit OTP for Account Number / Mobile Number.
    """
    data = request.get_json() or {}
    identifier = data.get('identifier', '8148534339').strip()
    
    if not identifier:
        return jsonify({'success': False, 'message': 'Please provide an Account Number or Mobile Number.'}), 400
        
    otp_data = generate_otp(identifier)
    return jsonify({
        'success': True,
        'message': f"OTP successfully sent to registered mobile {otp_data['phone']}.",
        'otp': otp_data['otp'],
        'account_id': otp_data['account_id'],
        'phone': otp_data['phone'],
        'holder_name': otp_data['holder_name']
    })

@app.route('/api/auth/verify-otp', methods=['POST'])
def api_verify_otp():
    """
    Verifies 6-digit OTP code and logs user in.
    """
    data = request.get_json() or {}
    identifier = data.get('identifier', '').strip()
    otp_code = data.get('otp_code', '').strip()
    
    if not identifier or not otp_code:
        return jsonify({'success': False, 'message': 'Identifier and OTP code are required.'}), 400
        
    is_valid, account = verify_otp_code(identifier, otp_code)
    if is_valid and account:
        session['user_id'] = account['account_id']
        session['user_email'] = account.get('email', 'customer@bank.com')
        session['user_name'] = account['holder_name']
        session['user_role'] = 'Verified Customer'
        session['user_account_id'] = account['account_id']
        session['user_phone'] = account.get('phone_number', '+91 8148534339')
        return jsonify({
            'success': True,
            'message': 'OTP verification successful. Welcome to FraudGuard AI!',
            'account': {
                'account_id': account['account_id'],
                'holder_name': account['holder_name'],
                'phone': account.get('phone_number', '+91 8148534339'),
                'avg_amount': account.get('avg_amount', 3200.0)
            }
        })
    return jsonify({'success': False, 'message': 'Invalid OTP code. Please check your SMS or use 123456.'}), 401

# ==========================================================
# REST API: MULTI-STAGE USER CALL & SMS DECISION WORKFLOW
# ==========================================================

@app.route('/api/accounts/<account_id>/call-step', methods=['POST'])
def api_call_workflow_step(account_id):
    """
    Executes the complete flowchart:
    Transaction -> AI High Risk -> User Notification -> Call User (Attempt 1)
    -> YES: Verify (Safe / Block)
    -> NO: Retry Call (Attempt 2)
       -> YES: Verify (Safe / Block)
       -> NO: Fallback to SMS Decision ("Was this done by you?")
          -> YES (Done by Me / Self): SAFE (Account NOT blocked)
          -> NO (Not Done by Me / Others): FRAUD (Account BLOCKED)
          -> Timeout: ACCOUNT_HOLD -> Admin Review
    """
    data = request.get_json() or {}
    step = int(data.get('attempt', 1)) # 1 or 2
    outcome = data.get('outcome', 'NOT_ATTENDED') # 'ATTENDED' or 'NOT_ATTENDED'
    tx_id = data.get('transaction_id', 'TX10045')
    amount = data.get('amount', '75,000')
    location = data.get('location', 'Dubai')

    acc = get_account_profile(account_id)
    phone = acc['phone_number'] if acc else '+91 8148534339'
    name = acc['holder_name'] if acc else 'Cardholder'

    if outcome == 'NOT_ATTENDED':
        if step == 1:
            increment_call_attempt(account_id, 'ATTEMPT_1_UNATTENDED')
            log_customer_communication(
                account_id, tx_id, 'CALL_ATTEMPT_1', phone,
                f"Automated Call Attempt #1 to {phone} for ₹{amount} transaction in {location} was UNATTENDED / MISSED.",
                status='NOT_ATTENDED', response='RETRY_CALL_REQUIRED'
            )
            return jsonify({
                'success': True,
                'next_step': 'RETRY_CALL',
                'attempt': 2,
                'message': f"Call Attempt #1 to {phone} was unattended. Initiating Automated Retry Call (Attempt #2)..."
            })
        else: # step == 2
            # Trigger SMS Fallback Message to Customer
            sms_prompt = (
                f"🔴 Bank Security Alert: A transaction of ₹{amount} at {location} was requested on Account {account_id}. "
                f"Was this transaction done by you? Reply [1: DONE BY ME] or [2: NOT DONE BY ME / FRAUD]."
            )
            log_customer_communication(
                account_id, tx_id, 'SMS_ALERT', phone,
                sms_prompt,
                status='SMS_SENT_PENDING_RESPONSE', response='AWAITING_USER_DECISION'
            )
            return jsonify({
                'success': True,
                'next_step': 'SMS_DECISION',
                'phone': phone,
                'sms_text': sms_prompt,
                'message': f"📱 Call Attempt #2 missed. Dispatched urgent SMS verification to {phone}: 'Was this transaction done by you or others?'"
            })
    else: # outcome == 'ATTENDED'
        log_customer_communication(
            account_id, tx_id, f'CALL_ATTEMPT_{step}', phone,
            f"Call Attempt #{step} ATTENDED by cardholder {name}. Awaiting verification.",
            status='ATTENDED_VERIFY', response='VERIFYING'
        )
        return jsonify({
            'success': True,
            'next_step': 'VERIFY',
            'script': f"Hello {name}, this is FraudGuard AI security desk. We detected an unusual transaction of ₹{amount} from {location}. Did you authorize this?",
            'message': f"Customer attended Call Attempt #{step}. Interactive voice verification in progress."
        })

@app.route('/api/accounts/<account_id>/sms-response', methods=['POST'])
def api_sms_response(account_id):
    """
    Handles SMS decision from user:
    - 'SELF': Done by me -> SAFE, account NOT blocked (remains ACTIVE).
    - 'OTHERS': Not done by me / fraud -> FRAUD, account IMMEDIATELY BLOCKED.
    """
    data = request.get_json() or {}
    decision = data.get('decision', 'SELF') # 'SELF' or 'OTHERS'
    tx_id = data.get('transaction_id', 'TX10045')
    
    result = process_sms_decision(account_id, decision, tx_id)
    return jsonify({
        'success': True,
        'action': result['action'],
        'status': result['status'],
        'message': result['message']
    })

@app.route('/api/accounts/<account_id>/admin-review', methods=['POST'])
def api_admin_review_decision(account_id):
    """
    Admin Review resolution step:
    Admin Review -> SAFE (UNHOLD ACCOUNT) or FRAUD (BLOCK ACCOUNT)
    """
    data = request.get_json() or {}
    decision = data.get('decision', 'FRAUD') # 'SAFE' or 'FRAUD'
    tx_id = data.get('transaction_id', '')

    acc = get_account_profile(account_id)
    phone = acc['phone_number'] if acc else '+91 8148534339'

    if decision == 'SAFE':
        set_account_unhold(account_id)
        log_customer_communication(
            account_id, tx_id, 'ADMIN_REVIEW', phone,
            "Admin Review completed: Investigator cleared transaction as LEGITIMATE / SAFE. Account UNHELD and restored to ACTIVE.",
            status='UNHELD', response='ACTIVE'
        )
        return jsonify({
            'success': True,
            'action': 'UNHOLD',
            'status': 'ACTIVE',
            'message': f"✅ Account {account_id} verified SAFE by Admin Review. ACCOUNT UNHELD & restored to ACTIVE status."
        })
    else: # FRAUD
        set_account_blocked(account_id, reason=f"Confirmed FRAUD during Admin Review for {tx_id}")
        log_customer_communication(
            account_id, tx_id, 'ADMIN_REVIEW', phone,
            "Admin Review completed: Investigator confirmed FRAUD. Account permanently BLOCKED to prevent financial theft.",
            status='BLOCKED', response='PERMANENT_FREEZE'
        )
        return jsonify({
            'success': True,
            'action': 'BLOCK',
            'status': 'BLOCKED',
            'message': f"🚨 Fraud confirmed by Admin Review. Account {account_id} is permanently BLOCKED and transfers frozen."
        })

@app.route('/api/accounts/<account_id>/block', methods=['POST'])
def api_block_account(account_id):
    data = request.get_json() or {}
    reason = data.get('reason', 'Critical transaction fraud detected by security analyst')
    set_account_blocked(account_id, reason=reason)
    return jsonify({'success': True, 'message': f'Account {account_id} has been BLOCKED.', 'status': 'BLOCKED'})

@app.route('/api/accounts/<account_id>/unblock', methods=['POST'])
def api_unblock_account(account_id):
    set_account_unhold(account_id)
    return jsonify({'success': True, 'message': f'Account {account_id} has been UNBLOCKED and restored to ACTIVE.', 'status': 'ACTIVE'})

@app.route('/api/accounts/<account_id>/send-message', methods=['POST'])
def api_send_customer_message(account_id):
    data = request.get_json() or {}
    tx_id = data.get('transaction_id', '')
    amount = data.get('amount', '0')
    location = data.get('location', 'Unknown')
    
    acc = get_account_profile(account_id)
    phone = acc['phone_number'] if acc else '+91 8148534339'
    
    msg = f"📱 FraudGuard Notification: Unusual transaction of ₹{amount} detected from {location} on account {account_id}. Security call incoming. If unauthorized, reply 'HOLD'."
    
    log_customer_communication(account_id, tx_id, 'SMS_NOTIFICATION', phone, msg, 'DELIVERED', 'Notification sent')
    
    return jsonify({'success': True, 'message': f'📱 User Notification SMS sent to {phone}. Customer notified.'})

@app.route('/api/accounts/<account_id>/call', methods=['POST'])
def api_call_customer(account_id):
    data = request.get_json() or {}
    tx_id = data.get('transaction_id', 'TX10045')
    amount = data.get('amount', '75,000')
    location = data.get('location', 'Dubai')

    acc = get_account_profile(account_id)
    phone = acc['phone_number'] if acc else '+91 98450 12345'
    name = acc['holder_name'] if acc else 'Valued Customer'

    call_script = f"Hello {name}, this is the FraudGuard AI security desk. We detected an unusual transaction of ₹{amount} from {location}. Did you authorize this transaction?"

    return jsonify({
        'success': True,
        'account_id': account_id,
        'customer_name': name,
        'phone': phone,
        'script': call_script,
        'tx_id': tx_id
    })

@app.route('/api/simulate', methods=['POST'])
def api_simulate():
    """
    Simulates high-risk transaction -> notifies user -> initiates verification flow
    """
    accounts = get_all_accounts()
    selected_acc = random.choice(accounts) if accounts else {
        'account_id': 'ACC102', 'avg_amount': 3500.0, 'normal_locations': 'Chennai, Coimbatore', 'normal_hours': '08:00 - 22:00', 'phone_number': '+91 98450 12345'
    }

    scenario = random.choices(['critical_dubai', 'burst_velocity', 'high_delhi'], weights=[0.50, 0.30, 0.20])[0]

    tx_id = f"TX{random.randint(10100, 99999)}"
    recipients = ['ACC105', 'ACC109', 'ACC102', 'ACC108', 'ACC121']
    recip = random.choice([r for r in recipients if r != selected_acc['account_id']])

    if scenario == 'critical_dubai':
        amount = float(random.randint(65000, 115000))
        location = 'Dubai'
        time_str = random.choice(['02:30 AM', '03:15 AM', '04:10 AM'])
        device = 'New Device (Dubai Anonymous Gateway)'
        new_dev = 1
        tx_10min = random.choice([6, 8, 9])
    elif scenario == 'burst_velocity':
        amount = float(random.randint(28000, 48000))
        location = 'Delhi'
        time_str = random.choice(['11:50 PM', '02:05 AM'])
        device = 'Unregistered Linux VM Client'
        new_dev = 1
        tx_10min = 8
    else:
        amount = float(random.randint(45000, 62000))
        location = 'Delhi'
        time_str = '03:15 AM'
        device = 'New iPhone 15 Pro'
        new_dev = 1
        tx_10min = 5

    sim_payload = {
        'transaction_id': tx_id,
        'account_id': selected_acc['account_id'],
        'recipient_account_id': recip,
        'amount': amount,
        'avg_amount': selected_acc['avg_amount'],
        'location': location,
        'time': time_str,
        'device': device,
        'new_device': new_dev,
        'transactions_10min': tx_10min
    }

    analysis = analyze_transaction(sim_payload, selected_acc)

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO transactions (
            transaction_id, account_id, recipient_account_id, amount, avg_amount,
            location, time_str, device, new_device, transactions_10min,
            rule_score, ml_score, risk_score, risk_level, status, flagged_reasons
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        tx_id, selected_acc['account_id'], recip, amount, selected_acc['avg_amount'],
        location, time_str, device, new_dev, tx_10min,
        analysis['rule_score'], analysis['ml_score'], analysis['risk_score'],
        analysis['risk_level'], analysis['status'], json.dumps(analysis['flagged_reasons'])
    ))

    alert_info = None
    if analysis['risk_level'] in ['HIGH', 'CRITICAL']:
        alert_id = f"ALT-{random.randint(3000, 9999)}"
        reasons_summary = [r['title'] for r in analysis['flagged_reasons']]
        msg = f"₹{amount:,.0f} suspicious activity detected on {selected_acc['account_id']} originating from {location}."
        cursor.execute('''
            INSERT INTO alerts (alert_id, transaction_id, account_id, severity, message, reasons, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (alert_id, tx_id, selected_acc['account_id'], analysis['risk_level'], msg, json.dumps(reasons_summary), 'PENDING'))
        alert_info = {
            'alert_id': alert_id,
            'severity': analysis['risk_level'],
            'message': msg
        }

    conn.commit()
    conn.close()

    if analysis['risk_level'] in ['HIGH', 'CRITICAL']:
        # Auto-send SMS notification
        log_customer_communication(
            selected_acc['account_id'], tx_id, 'SMS_NOTIFICATION', selected_acc.get('phone_number', '+91 98450 12345'),
            f"📱 High Risk Alert: ₹{amount:,.0f} detected from {location}. Verification call initiating.",
            status='DELIVERED', response='Automated Notification'
        )

    steps = [
        { 'step': 1, 'title': 'Transaction Ingested', 'detail': f"{tx_id} ({selected_acc['account_id']}): ₹{amount:,.2f} at {location}." },
        { 'step': 2, 'title': 'AI Detects HIGH/CRITICAL RISK', 'detail': f"Composite Score: {analysis['risk_score']}/100 [{analysis['risk_level']} RISK]." },
        { 'step': 3, 'title': '📱 User Notification Sent', 'detail': f"Dispatched immediate SMS notification to {selected_acc.get('phone_number', '+91 98450 12345')}." },
        { 'step': 4, 'title': '📞 Automated Call Initiated', 'detail': "Calling user for interactive voice authentication..." },
        { 'step': 5, 'title': 'Interactive Verification Ready', 'detail': "Awaiting call attendance (YES -> Verify | NO -> Retry -> Hold -> Admin Review)." }
    ]

    updated_metrics = get_dashboard_metrics()

    return jsonify({
        'success': True,
        'transaction_id': tx_id,
        'account_id': selected_acc['account_id'],
        'amount': amount,
        'location': location,
        'transaction': {
            'transaction_id': tx_id,
            'account_id': selected_acc['account_id'],
            'recipient_account_id': recip,
            'amount': amount,
            'location': location,
            'time_str': time_str,
            'device': device,
            'risk_score': analysis['risk_score'],
            'risk_level': analysis['risk_level'],
            'status': analysis['status'],
            'rule_score': analysis['rule_score'],
            'ml_score': analysis['ml_score'],
            'flagged_reasons': analysis['flagged_reasons']
        },
        'alert': alert_info,
        'steps': steps,
        'updated_metrics': updated_metrics
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    user = get_user_by_email(email)
    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_name'] = user['name']
        session['user_role'] = user['role']
        return jsonify({'success': True, 'message': 'Login successful', 'user': {'name': user['name'], 'email': user['email'], 'role': user['role']}})
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    metrics = get_dashboard_metrics()
    recent_txs, _ = get_all_transactions(limit=10)
    alerts = get_all_alerts(status_filter='PENDING')[:5]
    all_accs = get_all_accounts()
    review_queue = [a for a in all_accs if a['status'] in ['ACCOUNT_HOLD', 'ADMIN_REVIEW']]
    return jsonify({'success': True, 'metrics': metrics, 'recent_transactions': recent_txs, 'recent_alerts': alerts, 'admin_review_queue': review_queue})

@app.route('/api/transactions', methods=['GET', 'POST'])
def api_transactions():
    if request.method == 'GET':
        risk = request.args.get('risk', 'ALL')
        location = request.args.get('location', 'ALL')
        status = request.args.get('status', 'ALL')
        search = request.args.get('search', '')
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        tx_list, total = get_all_transactions(limit=limit, offset=offset, filter_risk=risk, filter_location=location, filter_status=status, search=search)
        return jsonify({'success': True, 'transactions': tx_list, 'total': total})
    
    data = request.get_json() or {}
    analysis = analyze_transaction(data)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    tx_id = data.get('transaction_id', f"TX{random.randint(10000, 99999)}")
    acc_id = analysis['account_id']
    recip_id = data.get('recipient_account_id', 'ACC105')
    
    cursor.execute('''
        INSERT INTO transactions (
            transaction_id, account_id, recipient_account_id, amount, avg_amount,
            location, time_str, device, new_device, transactions_10min,
            rule_score, ml_score, risk_score, risk_level, status, flagged_reasons
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        tx_id, acc_id, recip_id, analysis['amount'], analysis['avg_amount'],
        analysis['location'], analysis['time'], analysis['device'],
        analysis['new_device'], analysis['transactions_10min'],
        analysis['rule_score'], analysis['ml_score'], analysis['risk_score'],
        analysis['risk_level'], analysis['status'], json.dumps(analysis['flagged_reasons'])
    ))

    alert_created = None
    if analysis['risk_level'] in ['HIGH', 'CRITICAL']:
        alert_id = f"ALT-{random.randint(2000, 9999)}"
        reasons_summary = [r['title'] for r in analysis['flagged_reasons']]
        msg = f"₹{analysis['amount']:,.0f} flagged with {analysis['risk_level']} score of {analysis['risk_score']}/100 from {analysis['location']}."
        cursor.execute('''
            INSERT INTO alerts (alert_id, transaction_id, account_id, severity, message, reasons, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (alert_id, tx_id, acc_id, analysis['risk_level'], msg, json.dumps(reasons_summary), 'PENDING'))
        alert_created = alert_id

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'transaction_id': tx_id, 'analysis': analysis, 'alert_created': alert_created}), 201

@app.route('/api/transactions/<tx_id>', methods=['GET'])
def api_transaction_detail(tx_id):
    tx = get_transaction_by_id(tx_id)
    if not tx:
        return jsonify({'success': False, 'message': 'Transaction not found'}), 404
    try:
        tx['flagged_reasons'] = json.loads(tx['flagged_reasons']) if tx['flagged_reasons'] else []
    except Exception:
        pass
    return jsonify({'success': True, 'transaction': tx})

@app.route('/api/accounts', methods=['GET'])
def api_accounts():
    accounts_list = get_all_accounts()
    return jsonify({'success': True, 'accounts': accounts_list})

@app.route('/api/accounts/<account_id>', methods=['GET'])
def api_account_detail(account_id):
    account = get_account_profile(account_id)
    if not account:
        return jsonify({'success': False, 'message': 'Account not found'}), 404
    txs = get_transactions_for_account(account_id)
    comms = get_communications_for_account(account_id)
    return jsonify({'success': True, 'account': dict(account), 'transactions': txs, 'communications': comms})

@app.route('/api/alerts', methods=['GET'])
def api_alerts():
    status = request.args.get('status', 'ALL')
    alerts = get_all_alerts(status_filter=status)
    for a in alerts:
        try:
            a['reasons'] = json.loads(a['reasons']) if a['reasons'] else []
        except Exception:
            pass
    return jsonify({'success': True, 'alerts': alerts})

@app.route('/api/alerts/<alert_id>/review', methods=['POST'])
def api_review_alert(alert_id):
    update_alert_status(alert_id, 'UNDER_INVESTIGATION')
    return jsonify({'success': True, 'message': f'Alert {alert_id} moved to Under Investigation status.'})

@app.route('/api/alerts/<alert_id>/dismiss', methods=['POST'])
def api_dismiss_alert(alert_id):
    update_alert_status(alert_id, 'DISMISSED')
    return jsonify({'success': True, 'message': f'Alert {alert_id} has been dismissed.'})

@app.route('/api/upload', methods=['POST'])
def api_upload_csv():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No CSV file attached in request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        
        results = []
        conn = get_db_connection()
        cursor = conn.cursor()

        for row in reader:
            tx_id = row.get('transaction_id') or f"TX{random.randint(10000, 99999)}"
            acc_id = row.get('account_id') or 'ACC101'
            amount = float(row.get('amount', 1000.0))
            avg_amount = float(row.get('avg_amount', 2500.0))
            location = row.get('location', 'Chennai')
            time_str = row.get('time', '12:00 PM')
            new_dev = int(row.get('new_device', 0))
            tx_10min = int(row.get('transactions_10min', 1))

            payload = {
                'transaction_id': tx_id, 'account_id': acc_id, 'amount': amount,
                'avg_amount': avg_amount, 'location': location, 'time_str': time_str,
                'device': 'Imported Device' if not new_dev else 'New Unverified Hardware',
                'new_device': new_dev, 'transactions_10min': tx_10min
            }

            analysis = analyze_transaction(payload)
            status = 'CRITICAL' if analysis['risk_level'] == 'CRITICAL' else ('SUSPICIOUS' if analysis['risk_level'] == 'HIGH' else ('REVIEW' if analysis['risk_level'] == 'MEDIUM' else 'NORMAL'))

            cursor.execute('''
                INSERT OR REPLACE INTO transactions (
                    transaction_id, account_id, recipient_account_id, amount, avg_amount,
                    location, time_str, device, new_device, transactions_10min,
                    rule_score, ml_score, risk_score, risk_level, status, flagged_reasons
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tx_id, acc_id, 'ACC105', amount, avg_amount, location, time_str,
                payload['device'], new_dev, tx_10min,
                analysis['rule_score'], analysis['ml_score'], analysis['risk_score'],
                analysis['risk_level'], status, json.dumps(analysis['flagged_reasons'])
            ))

            if analysis['risk_level'] in ['HIGH', 'CRITICAL']:
                alert_id = f"ALT-{random.randint(4000, 9999)}"
                reasons_summary = [r['title'] for r in analysis['flagged_reasons']]
                msg = f"CSV Batch: ₹{amount:,.0f} flagged {analysis['risk_level']} ({analysis['risk_score']}/100) from {location}."
                cursor.execute('''
                    INSERT INTO alerts (alert_id, transaction_id, account_id, severity, message, reasons, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (alert_id, tx_id, acc_id, analysis['risk_level'], msg, json.dumps(reasons_summary), 'PENDING'))

            results.append({
                'transaction_id': tx_id, 'account_id': acc_id, 'amount': amount,
                'location': location, 'time': time_str, 'risk_score': analysis['risk_score'],
                'risk_level': analysis['risk_level'], 'status': status
            })

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': f'Successfully processed {len(results)} transactions from CSV.', 'count': len(results), 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error parsing CSV: {str(e)}'}), 500

@app.route('/api/export-report', methods=['GET'])
def api_export_report():
    conn = get_db_connection()
    txs = conn.execute('SELECT transaction_id, account_id, recipient_account_id, amount, location, time_str, device, rule_score, ml_score, risk_score, risk_level, status, created_at FROM transactions ORDER BY id DESC').fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Transaction ID', 'Account ID', 'Recipient', 'Amount (INR)', 'Location', 'Time', 'Device', 'Rule Score', 'ML Score', 'Final Risk Score', 'Risk Level', 'Status', 'Timestamp'])

    for t in txs:
        writer.writerow([t['transaction_id'], t['account_id'], t['recipient_account_id'], t['amount'], t['location'], t['time_str'], t['device'], t['rule_score'], t['ml_score'], t['risk_score'], t['risk_level'], t['status'], t['created_at']])

    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=fraudguard_investigation_report.csv"})

@app.route('/api/analytics', methods=['GET'])
def api_analytics():
    conn = get_db_connection()
    low_c = conn.execute('SELECT COUNT(*) as c FROM transactions WHERE risk_level = "LOW"').fetchone()['c']
    med_c = conn.execute('SELECT COUNT(*) as c FROM transactions WHERE risk_level = "MEDIUM"').fetchone()['c']
    high_c = conn.execute('SELECT COUNT(*) as c FROM transactions WHERE risk_level = "HIGH"').fetchone()['c']
    crit_c = conn.execute('SELECT COUNT(*) as c FROM transactions WHERE risk_level = "CRITICAL"').fetchone()['c']

    loc_rows = conn.execute('''
        SELECT location, COUNT(*) as total_tx, SUM(CASE WHEN risk_level IN ("HIGH", "CRITICAL") THEN 1 ELSE 0 END) as suspicious_tx, MAX(risk_score) as max_risk
        FROM transactions GROUP BY location ORDER BY suspicious_tx DESC
    ''').fetchall()

    days_data = {
        'labels': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        'normal': [1420, 1680, 1850, 1920, 2100, 1750, 1400],
        'suspicious': [38, 45, 52, 68, 92, 74, 51]
    }

    hourly_rows = [
        {'hour': '00:00 - 03:00', 'count': 42}, {'hour': '03:00 - 06:00', 'count': 68},
        {'hour': '06:00 - 09:00', 'count': 12}, {'hour': '09:00 - 12:00', 'count': 18},
        {'hour': '12:00 - 15:00', 'count': 24}, {'hour': '15:00 - 18:00', 'count': 31},
        {'hour': '18:00 - 21:00', 'count': 45}, {'hour': '21:00 - 24:00', 'count': 56}
    ]

    amount_ranges = [{'range': '< ₹5K', 'count': 32}, {'range': '₹5K-15K', 'count': 18}, {'range': '₹15K-35K', 'count': 9}, {'range': '₹35K-75K', 'count': 7}, {'range': '₹75K+', 'count': 5}]
    conn.close()

    return jsonify({'success': True, 'risk_distribution': {'low': low_c, 'medium': med_c, 'high': high_c, 'critical': crit_c}, 'location_analysis': [dict(r) for r in loc_rows], 'weekly_activity': days_data, 'hourly_anomalies': hourly_rows, 'amount_distribution': amount_ranges})

@app.route('/api/network', methods=['GET'])
def api_network():
    conn = get_db_connection()
    accounts = conn.execute('SELECT account_id, holder_name, risk_score, status FROM accounts').fetchall()
    transfers = conn.execute('''
        SELECT account_id as source, recipient_account_id as target, amount, risk_level, risk_score, transaction_id
        FROM transactions WHERE recipient_account_id IS NOT NULL AND recipient_account_id != ''
        ORDER BY id DESC LIMIT 25
    ''').fetchall()
    conn.close()

    nodes = []
    for a in accounts:
        nodes.append({
            'id': a['account_id'], 'label': a['account_id'], 'name': a['holder_name'],
            'risk_score': a['risk_score'], 'status': a['status'], 'is_blocked': a['status'] == 'BLOCKED',
            'is_held': a['status'] == 'ACCOUNT_HOLD', 'is_high_risk': a['risk_score'] >= 61
        })

    edges = []
    for t in transfers:
        edges.append({
            'from': t['source'], 'to': t['target'], 'amount': t['amount'],
            'risk_level': t['risk_level'], 'risk_score': t['risk_score'], 'tx_id': t['transaction_id']
        })

    return jsonify({'success': True, 'nodes': nodes, 'edges': edges})

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    data = request.get_json() or {}
    try:
        rule_w = float(data.get('rule_weight', 0.6))
        ml_w = float(data.get('ml_weight', 0.4))
        alert_thresh = int(data.get('auto_alert_threshold', 60))
        high_thresh = int(data.get('high_risk_threshold', 61))
        crit_thresh = int(data.get('critical_risk_threshold', 81))
        auto_block = int(data.get('auto_block_threshold', 81))

        update_system_settings(rule_w, ml_w, alert_thresh, high_thresh, crit_thresh, auto_block)
        return jsonify({'success': True, 'message': 'System engine parameters updated successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

if __name__ == '__main__':
    init_db()
    get_or_load_model()
    print(">>> FraudGuard AI Server starting on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
