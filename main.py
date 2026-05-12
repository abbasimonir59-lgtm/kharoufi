import requests
import time
from datetime import datetime
import threading
import os
from flask import Flask

# ==========================================
# 1. إعدادات تيليجرام
# ==========================================
TELEGRAM_TOKEN = "8775731549:AAG88LAbKClrRUWdOLpGS-OlwRoyd0GEPgw"
CHAT_ID = "8641282194"

# ==========================================
# 2. إعدادات الموقع
# ==========================================
API_URL = "https://adhahi.dz/api/v1/public/wilaya-quotas"
WILAYA_CODE = "08" # كود ولاية بشار

tracking_message_id = None

# ==========================================
# 3. خادم الويب (لمنع توقف السكريبت في Replit)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ السكريبت المطور يعمل بنجاح ويراقب الموقع 24/7!"

def run_web_server():
    # استخدام المنفذ الذي توفره البيئة لتفادي الأخطاء
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 4. دوال تيليجرام
# ==========================================
def log(message):
    """طباعة الوقت والرسالة في الشاشة السوداء"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")

def send_telegram_alert(message):
    """إرسال إشعار التوفر النهائي"""
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try: 
        requests.post(url, json=payload)
    except: pass

def send_initial_tracking_message():
    """إرسال رسالة التتبع الصامتة في البداية"""
    global tracking_message_id
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "⏳ جاري بدء المراقبة وتفقد الاتصال بالموقع...",
        "disable_notification": True
    }
    try:
        # استخدام json لضمان التوافق التام مع تيليجرام
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            tracking_message_id = response.json().get("result", {}).get("message_id")
    except: pass

def update_telegram_tracking_message(connection_status, is_available_text):
    """تحديث الرسالة في تيليجرام مع تنسيق احترافي"""
    global tracking_message_id
    if not tracking_message_id: return
    
    now = datetime.now().strftime("%H:%M:%S")
    
    msg = (
        f"🔄 *مراقبة ولاية بشار (تحديث مباشر)*\n"
        f"-----------------------------------\n"
        f"🌐 *الاتصال بالموقع:* {connection_status}\n"
        f"⏰ *آخر فحص:* {now}\n"
        f"🐑 *حالة الحجز:* {is_available_text}"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    payload = {
        "chat_id": CHAT_ID,
        "message_id": tracking_message_id,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        # التعديل الأهم هنا: استخدام json بدلاً من data لكي لا يرفض تيليجرام التعديل
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            err = response.json().get("description", "")
            if "not found" in err.lower() or "deleted" in err.lower():
                tracking_message_id = None
                send_initial_tracking_message()
    except: pass

# ==========================================
# 5. دالة المراقبة الرئيسية
# ==========================================
def start_monitoring():
    log("▶ بدأت المراقبة على السيرفر. سيتم الفحص كل 30 ثانية.")
    send_initial_tracking_message()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    while True:
        try:
            response = requests.get(API_URL, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                bechar_found = False
                
                for wilaya in data:
                    if wilaya.get("wilayaCode") == WILAYA_CODE:
                        bechar_found = True
                        is_available = wilaya.get("available", False)
                        
                        if is_available:
                            log("🎉 عاجل: الحجز متاح!")
                            send_telegram_alert("🚨 عاجل: الحجز في ولاية بشار أصبح متاحاً الآن!\nسارع بالدخول: https://adhahi.dz/register")
                            return # إيقاف السكريبت
                        else:
                            log("✓ الاتصال سليم - الحجز غير متوفر حالياً")
                            update_telegram_tracking_message("متصل بنجاح ✅", "❌ غير متوفر حالياً")
                        break
                        
                if not bechar_found:
                    log("⚠️ كود الولاية غير موجود.")
                    update_telegram_tracking_message("متصل بنجاح ✅", "⚠️ كود الولاية غير موجود بالموقع")
                    
            elif response.status_code == 403 or response.status_code == 401:
                log(f"❌ الموقع يمنع الوصول (الكود {response.status_code})")
                update_telegram_tracking_message(f"محظور من الموقع 🚫 (الكود {response.status_code})", "غير معروف")
            else:
                log(f"❌ الموقع يعيد الكود {response.status_code}")
                update_telegram_tracking_message(f"يوجد مشكلة في الموقع ⚠️ (الكود {response.status_code})", "غير معروف")
                
        except requests.exceptions.Timeout:
            log("⚠️ الموقع بطيء ولا يستجيب (Timeout)")
            update_telegram_tracking_message("الموقع بطيء جداً أو عليه ضغط ⏳", "غير معروف")
        except requests.exceptions.ConnectionError:
            log("⚠️ فشل الاتصال بالشبكة أو الموقع ساقط")
            update_telegram_tracking_message("الموقع لا يعمل أو متوقف ❌", "غير معروف")
        except Exception as e:
            log(f"⚠️ خطأ غير متوقع: {e}")
            update_telegram_tracking_message("خطأ في قراءة البيانات ⚠️", "غير معروف")

        time.sleep(30)

if __name__ == "__main__":
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()

    start_monitoring()
