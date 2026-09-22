import os
import re
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

def get_telephony_credentials():
    """
    Retrieves credentials from environment variables or database settings.
    """
    sid = os.environ.get('TWILIO_ACCOUNT_SID', '').strip()
    token = os.environ.get('TWILIO_AUTH_TOKEN', '').strip()
    from_phone = os.environ.get('TWILIO_PHONE_NUMBER', '').strip()
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

    return {
        'sid': sid,
        'token': token,
        'from_phone': from_phone,
        'default_phone': default_phone,
        'is_configured': bool(sid and token and from_phone)
    }

def send_real_sms(to_phone, message_text):
    """
    Sends a real SMS to the user's mobile number via Twilio (or logs live simulation).
    """
    creds = get_telephony_credentials()
    target_phone = normalize_phone_number(to_phone or creds['default_phone'])
    
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
                'message': f"Real SMS dispatched to {target_phone} (SID: {message.sid})"
            }
        except Exception as e:
            safe_log(f">>> [TWILIO SMS ERROR] Failed to send SMS to {target_phone}: {e}")
            return {
                'success': False,
                'mode': 'LIVE_TWILIO_ERROR',
                'error': str(e),
                'to': target_phone,
                'message': f"Twilio SMS delivery failed: {str(e)}"
            }
    else:
        # Graceful simulation fallback with clear instructions
        safe_log(f">>> [SIMULATED SMS] Dispatched to {target_phone}: '{message_text}'")
        return {
            'success': True,
            'mode': 'SIMULATED',
            'to': target_phone,
            'message': f"SMS simulated to {target_phone}. (Configure Twilio in Settings to ring real phones via live SMS API)"
        }

def make_real_call(to_phone, voice_text=None, transaction_details=None):
    """
    Initiates an actual live outbound voice call to the user's phone via Twilio Voice API.
    Plays Text-to-Speech (TTS) audio with TwiML.
    """
    creds = get_telephony_credentials()
    target_phone = normalize_phone_number(to_phone or creds['default_phone'])
    
    # Generate interactive TwiML script
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
            safe_log(f">>> [TWILIO LIVE CALL] Call initiated to {target_phone} | Call SID: {call.sid}")
            return {
                'success': True,
                'mode': 'LIVE_TWILIO',
                'call_sid': call.sid,
                'to': target_phone,
                'status': call.status,
                'message': f"📞 Real Voice Call initiated! Your phone {target_phone} should ring now (SID: {call.sid})."
            }
        except Exception as e:
            safe_log(f">>> [TWILIO CALL ERROR] Failed to place call to {target_phone}: {e}")
            return {
                'success': False,
                'mode': 'LIVE_TWILIO_ERROR',
                'error': str(e),
                'to': target_phone,
                'message': f"Twilio Call delivery failed: {str(e)}"
            }
    else:
        safe_log(f">>> [SIMULATED VOICE CALL] Dialing {target_phone} with TTS script...")
        return {
            'success': True,
            'mode': 'SIMULATED',
            'to': target_phone,
            'script': voice_text,
            'message': f"Voice call simulated to {target_phone}. (Configure Twilio in Settings to ring real physical phones!)"
        }

def send_real_otp(to_phone, otp_code):
    """
    Sends real 6-digit OTP code to the user's mobile phone via SMS.
    """
    msg = f"FraudGuard AI: Your 6-digit verification code is {otp_code}. Valid for 10 minutes. Do not share."
    return send_real_sms(to_phone, msg)
