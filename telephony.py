import os
import re
import threading
import requests
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

def safe_log(text):
    """
    Safely prints logs without failing on Windows cp1252 character map issues.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        safe_text = text.encode('ascii', errors='replace').decode('ascii')
        print(safe_text)

def normalize_phone_number(phone_str, default_country_code='+91'):
    """
    Cleans and standardizes phone number to E.164 format (+918148534339).
    """
    if not phone_str:
        return '+918148534339'
    
    raw = str(phone_str).strip()
    digits = re.sub(r'\D', '', raw)
    
    if raw.startswith('+'):
        return f"+{digits}"
    elif len(digits) == 10:
        return f"{default_country_code}{digits}"
    elif len(digits) == 12 and digits.startswith('91'):
        return f"+{digits}"
    else:
        return f"+{digits}"

def get_10_digit_number(phone_str):
    """
    Returns only the 10 digits for Indian SMS gateways (e.g. 8148534339).
    """
    digits = re.sub(r'\D', '', str(phone_str))
    if len(digits) >= 10:
        return digits[-10:]
    return '8148534339'

TWILIO_WEB_APP_URLS = {
    'voice_console': 'https://console.twilio.com/us1/develop/voice/try-voice',
    'sms_console': 'https://console.twilio.com/us1/develop/sms/try-sms',
    'call_logs': 'https://console.twilio.com/us1/monitor/logs/calls',
    'sms_logs': 'https://console.twilio.com/us1/monitor/logs/sms',
    'verified_caller_ids': 'https://console.twilio.com/us1/develop/phone-numbers/manage/verified',
    'incoming_numbers': 'https://console.twilio.com/us1/develop/phone-numbers/manage/incoming'
}

def get_telephony_credentials():
    """
    Retrieves credentials from environment variables or database settings.
    Auto-discovers provisioned Twilio phone numbers if not explicitly set.
    """
    sid = os.environ.get('TWILIO_ACCOUNT_SID', '').strip()
    token = os.environ.get('TWILIO_AUTH_TOKEN', '').strip()
    from_phone = os.environ.get('TWILIO_PHONE_NUMBER', '').strip()
    fast2sms_key = os.environ.get('FAST2SMS_API_KEY', '').strip()
    default_phone = os.environ.get('DEFAULT_RECIPIENT_PHONE', '+918148534339').strip()

    # Fallback to database system_settings if not in env
    try:
        from database import get_system_settings
        settings = get_system_settings()
        if not sid and settings.get('twilio_account_sid'):
            sid = settings.get('twilio_account_sid', '').strip()
        if not token and settings.get('twilio_auth_token'):
            token = settings.get('twilio_auth_token', '').strip()
        if not from_phone and settings.get('twilio_from_phone'):
            from_phone = settings.get('twilio_from_phone', '').strip()
        if settings.get('default_recipient_phone'):
            default_phone = settings.get('default_recipient_phone', '+918148534339').strip()
    except Exception:
        pass

    # Auto-discover provisioned incoming phone number from Twilio if available
    if sid and token and not from_phone:
        try:
            from twilio.rest import Client
            _client = Client(sid, token)
            _incoming = _client.incoming_phone_numbers.list(limit=1)
            if _incoming:
                from_phone = _incoming[0].phone_number
                os.environ['TWILIO_PHONE_NUMBER'] = from_phone
                try:
                    from database import get_db_connection
                    _conn = get_db_connection()
                    _conn.execute('UPDATE system_settings SET twilio_from_phone = ? WHERE id = 1', (from_phone,))
                    _conn.commit()
                    _conn.close()
                except Exception:
                    pass
        except Exception:
            pass

    return {
        'sid': sid,
        'token': token,
        'from_phone': from_phone,
        'fast2sms_key': fast2sms_key,
        'default_phone': default_phone,
        'is_configured': bool(sid and token and from_phone),
        'has_fast2sms': bool(fast2sms_key),
        'web_urls': TWILIO_WEB_APP_URLS
    }

def speak_local_voice_async(text):
    """
    Speaks the voice call audio through computer speakers using pyttsx3.
    Runs asynchronously in a background thread so web requests do not stall.
    """
    def _run_tts():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 165)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            safe_log(f">>> [LOCAL TTS NOTICE] {e}")

    t = threading.Thread(target=_run_tts, daemon=True)
    t.start()

def send_fast2sms(to_phone, message_text, api_key):
    """
    Sends direct cellular SMS in India via Fast2SMS API.
    """
    digits_10 = get_10_digit_number(to_phone)
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        "route": "q",
        "message": message_text,
        "language": "english",
        "flash": 0,
        "numbers": digits_10
    }
    headers = {
        "authorization": api_key,
        "Content-Type": "application/json"
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        res_json = resp.json()
        if res_json.get('return'):
            safe_log(f">>> [FAST2SMS LIVE] Successfully delivered to {digits_10}")
            return {'success': True, 'mode': 'FAST2SMS_LIVE', 'to': digits_10, 'message': f"Real SMS sent to {digits_10} via Fast2SMS"}
        else:
            return {'success': False, 'mode': 'FAST2SMS_ERROR', 'error': res_json.get('message', 'SMS failed')}
    except Exception as e:
        return {'success': False, 'mode': 'FAST2SMS_ERROR', 'error': str(e)}

def send_real_sms(to_phone, message_text):
    """
    Sends a real SMS to the user's mobile number via Twilio, Fast2SMS, or logs live simulation.
    """
    creds = get_telephony_credentials()
    target_phone = normalize_phone_number(to_phone or creds['default_phone'])
    
    # 1. Try Twilio if configured
    if creds['is_configured']:
        try:
            from twilio.rest import Client
            client = Client(creds['sid'], creds['token'])
            message = client.messages.create(
                body=message_text,
                from_=creds['from_phone'],
                to=target_phone
            )
            safe_log(f">>> [TWILIO LIVE SMS] Successfully sent to {target_phone} | SID: {message.sid}")
            return {
                'success': True,
                'mode': 'LIVE_TWILIO',
                'sid': message.sid,
                'to': target_phone,
                'status': message.status,
                'web_urls': creds.get('web_urls', TWILIO_WEB_APP_URLS),
                'message': f"Real SMS dispatched to {target_phone} (SID: {message.sid})"
            }
        except Exception as e:
            safe_log(f">>> [TWILIO SMS ERROR] {e}")

    # 2. Try Fast2SMS if configured
    if creds['has_fast2sms']:
        f_res = send_fast2sms(target_phone, message_text, creds['fast2sms_key'])
        if f_res.get('success'):
            f_res['web_urls'] = creds.get('web_urls', TWILIO_WEB_APP_URLS)
            return f_res

    # 3. If carrier credentials not configured
    safe_log(f">>> [TELEPHONY NOTICE] Real SMS cannot reach physical phone {target_phone}: Carrier credentials not set.")
    return {
        'success': False,
        'mode': 'CREDENTIALS_REQUIRED',
        'to': target_phone,
        'web_urls': creds.get('web_urls', TWILIO_WEB_APP_URLS),
        'message': f"⚠️ Real cellular SMS to physical phone {target_phone} requires Twilio credentials or Fast2SMS API key in Settings."
    }

def make_real_call(to_phone, voice_text=None, transaction_details=None):
    """
    Initiates an actual live outbound voice call to the person's physical phone via Twilio Voice API.
    Does NOT simulate or display on the laptop screen.
    """
    creds = get_telephony_credentials()
    target_phone = normalize_phone_number(to_phone or creds['default_phone'])
    
    # Generate voice script
    if not voice_text:
        tx_info = transaction_details or {}
        amount = tx_info.get('amount', '75,000')
        location = tx_info.get('location', 'Dubai')
        voice_text = (
            f"Hello. This is an urgent security alert from FraudGuard AI. "
            f"We detected a high-risk transaction of {amount} Rupees originating from {location}. "
            f"If you authorized this transaction, please reply to our SMS message to confirm. "
            f"If you did not make this transaction, please reply with fraud immediately to block your account. "
            f"Thank you."
        )

    # Twilio outbound cellular phone call
    twiml_payload = f"""<Response>
    <Pause length="1"/>
    <Say voice="Polly.Aditi" language="en-IN">
        {voice_text}
    </Say>
    <Pause length="1"/>
    <Say voice="Polly.Aditi" language="en-IN">
        Repeating: {voice_text}
    </Say>
</Response>"""

    if creds['is_configured']:
        try:
            from twilio.rest import Client
            client = Client(creds['sid'], creds['token'])
            call = client.calls.create(
                twiml=twiml_payload,
                to=target_phone,
                from_=creds['from_phone']
            )
            safe_log(f">>> [TWILIO LIVE CELLULAR CALL] Dispatched to {target_phone} | Call SID: {call.sid}")
            return {
                'success': True,
                'mode': 'LIVE_TWILIO',
                'call_sid': call.sid,
                'to': target_phone,
                'status': call.status,
                'web_urls': creds.get('web_urls', TWILIO_WEB_APP_URLS),
                'message': f"📞 Outbound cellular call initiated! Real phone {target_phone} is ringing now (SID: {call.sid})."
            }
        except Exception as e:
            safe_log(f">>> [TWILIO CALL ERROR] {e}")
            return {
                'success': False,
                'mode': 'LIVE_TWILIO_ERROR',
                'error': str(e),
                'to': target_phone,
                'web_urls': creds.get('web_urls', TWILIO_WEB_APP_URLS),
                'message': f"Twilio cellular call delivery failed: {str(e)}"
            }
    else:
        safe_log(f">>> [TELEPHONY NOTICE] Cannot dial physical phone {target_phone}: Twilio credentials not configured.")
        return {
            'success': False,
            'mode': 'CREDENTIALS_REQUIRED',
            'to': target_phone,
            'script': voice_text,
            'web_urls': creds.get('web_urls', TWILIO_WEB_APP_URLS),
            'message': f"⚠️ Real cellular call to physical phone {target_phone} requires Twilio credentials. Enter your Twilio Account SID, Auth Token & Twilio Virtual Number in Settings to make your phone ring."
        }

def send_real_otp(to_phone, otp_code):
    """
    Sends real 6-digit OTP code to the user's mobile phone via SMS.
    """
    msg = f"FraudGuard AI: Your 6-digit verification code is {otp_code}. Valid for 10 minutes. Do not share."
    return send_real_sms(to_phone, msg)
