import requests
import time
from datetime import datetime
import threading
import os
from flask import Flask

# ==========================================
# 1. إعدادات تيليجرام (جاهزة)
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
# 3. خادم الويب الوهمي (لمنع السيرفر من النوم)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ بوت مراقبة الأضاحي (ولاية بشار) يعمل بنجاح 24/7!"

def run_web_server():
    # جلب المنفذ التلقائي من بيئة Render لتفادي خطأ الفشل (Timeout)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 4. دوال البوت الأصلية
# ==========================================
def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")

def send_telegram_alert(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception:
        pass

def send_initial_tracking_message():
    global tracking_message_id
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": "⏳ جاري بدء المراقبة المستمرة لولاية بشار من السيرفر المجاني...",
        "disable_notification": "true" 
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            tracking_message_id = response.json().get("result", {}).get("message_id")
    except Exception:
        pass

def update_telegram_tracking_message(status_msg):
    global tracking_message_id
    if not tracking_message_id:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    payload = {
        "chat_id": CHAT_ID,
        "message_id": tracking_message_id,
        "text": status_msg
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            err = response.json().get("description", "")
            if "not found" in err.lower() or "deleted" in err.lower():
                tracking_message_id = None
                send_initial_tracking_message()
    except Exception:
        pass

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
            now = datetime.now().strftime("%H:%M:%S")
            
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
                            update_telegram_tracking_message(f"🔄 مراقبة ولاية بشار (مباشر):\n\nآخر فحص: {now}\nالحالة: ❌ الحجز غير متوفر حالياً.")
                        break
            else:
                update_telegram_tracking_message(f"❌ خطأ في الاتصال بالموقع ({now}) - الكود: {response.status_code}")
        except Exception:
            pass

        time.sleep(30)

if __name__ == "__main__":
    # تشغيل خادم الويب في مسار خلفي (Thread) لكي لا يوقف عمل البوت
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()

    # تشغيل حلقة البوت
    start_monitoring()