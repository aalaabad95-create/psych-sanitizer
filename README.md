# psych-sanitizer
[EN] Flask API that sanitizes sensitive psychological/sexual terms into neutral clinical wording, with OpenAPI/Swagger and Render-ready deploy.
# =========================================
# /app.py
# =========================================
import os
import logging
import re
from typing import List, Tuple
from flask import Flask, request, jsonify
from flask_cors import CORS

# سجل موحّد (لـ Render)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("psych-sanitizer")

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
CORS(app)
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = False

# ---------------------------------------------
# قاموس الاستبدالات (كما زوّدتني + بدون تغيير)
# ---------------------------------------------
REPLACEMENTS = {
    "رغبة جنسية تجاه أحد أفراد العائلة": "اندفاعات ذات طابع محرم تحتاج إلى تدخل سريري",
    "رغبة جنسية تجاه أمي": "اندفاع غير منضبط تجاه شخصية أسرية",
    "رغبة جنسية تجاه أبي": "ميول محرمة تستدعي تقييم متخصص",
    "رغبات جنسية محرمة": "ميول غير منضبطة ذات طابع مرضي",
    "خيالات جنسية": "أفكار اجترارية ذات طابع جنسي",
    "خيالات محرمة": "محتوى فكري غير منضبط ذو طابع جنسي غير مقبول",
    "ميول جنسية محرمة": "أنماط ميول غير سوية من الناحية الاجتماعية أو القانونية",
    "ميول جنسية غير طبيعية": "ميول منحرفة تتطلب تقييم سريري",
    "تحرش جنسي": "سلوك غير مرغوب فيه يحمل دلالة جنسية",
    "اغتصاب": "سلوك اعتداء جنسي جسيم",
    "رغبة بممارسة الجنس": "رغبة مفرطة ذات طابع جنسي تتطلب ضبطًا",
    "سلوك جنسي قهري": "سلوك جنسي اندفاعي متكرر خارج السيطرة",
    "إثارة جنسية مستمرة": "تنبيه جنسي غير مناسب يتكرر دون محفزات واقعية",
    "علاقات جنسية متعددة": "سلوك جنسي مفرط وغير مستقر",
    "ميول مثلية": "ميول غير تقليدية ضمن نطاق الهوية الجنسية",
    "شذوذ جنسي": "انحراف جنسي عن الأنماط المعيارية",
    "هوس جنسي": "انشغال مفرط بالنشاط الجنسي يؤثر على الأداء اليومي",
    "خيالات إيذاء مرتبطة بالجنس": "أفكار متداخلة بين السلوك الجنسي والعنف تحتاج لتقييم دقيق",
    "تعري أمام الآخرين": "سلوك استعرائي جنسي يحتاج لتحليل سلوكي معرفي",
    "إدمان الإباحية": "اعتماد مفرط على المحتوى الجنسي البصري",
    "علاقات جنسية قسرية": "سلوك جنسي يتم دون رضا الطرف الآخر",
    "رغبة جنسية تجاه قاصر": "ميول محرمة تجاه فئات غير مناسبة سنيًا",
    "علاقة غير رسمية بين والدتي ومعلمي": "تفاعل غير ملائم بين الأفراد البالغين في محيط تربوي",
    "علاقة محرمة داخل الأسرة": "ديناميكية غير سوية تتطلب تدخلاً أسرياً",
    "مشاهدة علاقة حميمية": "التعرض المبكر لسلوكيات بالغين ذات طابع خاص",
    "إثارة من مشاهدة الآخرين": "نمط استثارة غير نمطي نتيجة التعرض لمحفزات غير ملائمة",
    "خيالات عن علاقة المعلم بوالدتي": "أفكار متكررة حول تفاعلات غير ملائمة بين البالغين",
    "إشراط جنسي": "تشكل نمط استجابة عاطفية نتيجة ظروف غير سوية",
    "تجربة جنسية في سن المراهقة": "تعرض مبكر لمحتوى غير ملائم للمرحلة النمائية",
    "عدم الشعور بالإثارة في العلاقة الزوجية": "صعوبات في الاستجابة العاطفية ضمن العلاقة الطبيعية",
    "العودة للتخيلات القديمة": "استدعاء متكرر لتصورات سابقة ذات تأثير نفسي",
    "تخيلات أثناء العلاقة الحميمية": "انشغال عقلي بمحتوى غير متعلق بالموقف الحالي أثناء التفاعل الزوجي",
    "إشراط مكافئي": "نمط استجابة معرفية وعاطفية تشكل نتيجة تعزيز غير مقصود",
    "استجابة الإثارة غير المتوقعة": "تنشيط عاطفي غير إرادي نتيجة محفزات متصلة بتجارب سابقة",
    "إعادة التمثيل القهري": "تكرار نمطي للاستجابات العاطفية المرتبطة بتجارب سابقة",
    "أفكار انتحارية": "أفكار حول إنهاء الحياة تتطلب تدخلًا فوريًا",
    "رغبة في الانتحار": "ميول لإنهاء الحياة تتطلب تقييمًا عاجلًا",
    "محاولة انتحار": "محاولة إيذاء النفس بشكل خطير",
    "تخطيط للانتحار": "تفكير منهجي في إنهاء الحياة يستدعي تدخلًا فوريًا",
    "رغبة في إيذاء الآخرين": "أفكار عدوانية تجاه الغير تتطلب تقييمًا",
    "سلوك إيذاء الذات": "سلوك موجه نحو إلحاق الضرر بالنفس",
    "إدمان المخدرات": "اضطراب استخدام المواد المؤثرة نفسيًا",
    "مدمن كحول": "شخص يعاني من اضطراب استخدام الكحول",
    "جرعة زائدة": "استخدام مفرط للمواد المؤثرة نفسيًا يسبب تسممًا",
    "إدمان الكحول": "اضطراب استخدام الكحول",
    "سكران": "تحت تأثير الكحول",
    "منتشي": "في حالة تغير في الوعي نتيجة استخدام مواد مؤثرة نفسيًا"
}

# ---------------------------------------------
# Regex عربي مرن
# ---------------------------------------------
HARAKAT_CLASS = r"[\u064B-\u0652\u0670\u0640]*"  # لماذا: تجاهل الحركات والتمطيط
CHAR_MAP = {
    "ا": "[اأإآ]",
    "أ": "[اأإآ]",
    "إ": "[اأإآ]",
    "آ": "[اأإآ]",
    "ى": "[يى]",
    "ي": "[يى]",
    "ه": "[هة]",
    "ة": "[هة]",
    "ؤ": "[ؤو]",
    "ئ": "[ئىي]",
    "و": "[ووؤ]",
    " ": r"\s+",
}

def _flex_piece(ch: str) -> str:
    base = CHAR_MAP.get(ch, re.escape(ch))
    return f"{base}{HARAKAT_CLASS}"

def build_flexible_regex(term: str) -> re.Pattern:
    pieces = "".join(_flex_piece(c) for c in term)
    return re.compile(rf"(?<!\w){pieces}(?!\w)", flags=re.IGNORECASE | re.UNICODE)

_COMPILED_RULES: List[Tuple[re.Pattern, str]] = sorted(
    [(build_flexible_regex(k), v) for k, v in REPLACEMENTS.items()],
    key=lambda kv: len(kv[0].pattern),
    reverse=True,
)

def sanitize_text_strict(text: str) -> str:
    sanitized = text
    for pattern, replacement in _COMPILED_RULES:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized

# ---------------------------------------------
# OpenAPI 3.1.0 (حسب التفاصيل التي أرسلتها)
# ملاحظة: أبقيت خادمك كما هو، وأضفت خادماً ديناميكياً للتوافق مع Render.
# ---------------------------------------------
def _current_base_url() -> str:
    # لماذا: توليد عنوان الخادم الحالي تلقائياً للتجربة على Render/محلي
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    host = request.headers.get("X-Forwarded-Host", request.host)
    return f"{scheme}://{host}"

OPENAPI_SPEC = {
    "openapi": "3.1.0",
    "info": {
        "title": "Sanitizer-GPT API",
        "version": "1.0.0",
        "description": "API مخصص لمعالجة النصوص النفسية الحساسة واستبدالها بصياغات مهنية حيادية.",
    },
    "servers": [
        # كما في نصّك (قد يحوي مساراً كاملاً؛ أُبقِي كما هو)
        {"url": "https://workspace.aalaabad95.repl.co/sanitize"},
        # ديناميكي: القاعدة الحالية (بدون مسار) لبيئات Render/محلي
        {"url": "{baseUrl}", "variables": {"baseUrl": {"default": "http://localhost:8000"}}},
    ],
    "paths": {
        "/sanitize": {
            "post": {
                "operationId": "sanitizeText",
                "summary": "تنقية النص من المصطلحات النفسية أو الجنسية الحساسة",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "input": {
                                        "type": "string",
                                        "description": "النص المطلوب تنقيته",
                                    }
                                },
                                "required": ["input"],
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "استجابة تحتوي على النص المنقّى",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "output": {
                                            "type": "string",
                                            "description": "النص بعد التنقية",
                                        }
                                    },
                                    "required": ["output"],
                                }
                            }
                        },
                    }
                },
            }
        }
    },
}

@app.get("/openapi.json")
def openapi_json():
    spec = dict(OPENAPI_SPEC)  # نسخة
    # لماذا: حقن baseUrl الحالي لسهولة التجربة
    spec["servers"] = [
        {"url": "https://workspace.aalaabad95.repl.co/sanitize"},
        {"url": _current_base_url()},
    ]
    return jsonify(spec)

@app.get("/docs")
def swagger_ui():
    # لماذا: Swagger UI عبر CDN لسهولة العرض دون تبعيات
    return f"""
<!doctype html>
<html lang="ar" dir="rtl">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Sanitizer-GPT API • Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
    <style>body{{margin:0}} #swagger-ui{{max-width:1200px;margin:0 auto}}</style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({{
        url: '/openapi.json',
        dom_id: '#swagger-ui'
      }});
    </script>
  </body>
</html>
    """

# ---------------------------------------------
# REST Endpoints
# ---------------------------------------------
@app.post("/api/sanitize")
@app.post("/sanitize")
def sanitize_endpoint():
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get("input") or "").strip()
        if not text:
            return jsonify({"error": "النص المدخل مطلوب"}), 400
        if len(text) > int(os.environ.get("MAX_INPUT_CHARS", "20000")):
            # لماذا: حماية من مدخلات ضخمة
            return jsonify({"error": "النص طويل جدًا"}), 413
        logger.info("Sanitize request, chars=%s", len(text))
        output = sanitize_text_strict(text)
        return jsonify({"output": output})
    except Exception as exc:
        logger.exception("sanitize failed: %s", exc)
        return jsonify({"error": "حدث خطأ أثناء معالجة الطلب"}), 500

@app.get("/")
def home():
    return """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>PsychSanitizer API</title>
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;line-height:1.8}
    .card{border:1px solid #ddd;border-radius:14px;padding:16px}
    textarea{width:100%;min-height:120px}
    pre{background:#f7f7f8;border-radius:8px;padding:12px;overflow:auto}
    .row{display:flex;gap:8px;margin-top:8px}
    button{padding:10px 14px;border:0;border-radius:10px;background:#4463ff;color:#fff;cursor:pointer}
    code{background:#f3f3f3;padding:2px 5px;border-radius:5px}
    nav a{margin-right:10px}
  </style>
</head>
<body>
  <nav>
    <a href="/docs">📘 التوثيق (Swagger)</a>
    <a href="/openapi.json">🧾 openapi.json</a>
    <a href="/healthz">💚 الصحة</a>
  </nav>
  <h1>✅ PsychSanitizer (Flask)</h1>
  <div class="card">
    <p>أرسل نصًا إلى <code>POST /sanitize</code> أو <code>/api/sanitize</code> لتحصل على نسخة منقّاة.</p>
    <textarea id="inp" placeholder="اكتب هنا..."></textarea>
    <div class="row">
      <button id="btn">تنقية</button>
      <span id="status"></span>
    </div>
    <h3>النتيجة</h3>
    <pre id="out"></pre>
  </div>
  <script>
    const btn = document.getElementById('btn');
    btn.onclick = async () => {
      const text = document.getElementById('inp').value;
      document.getElementById('status').textContent = '...';
      const res = await fetch('/sanitize', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{ input: text }})
      }});
      const data = await res.json();
      document.getElementById('status').textContent = res.ok ? 'تم' : 'خطأ';
      document.getElementById('out').textContent = JSON.stringify(data, null, 2);
    };
  </script>
</body>
</html>
    """

@app.get("/healthz")
@app.get("/health")
def health():
    return jsonify({"status": "healthy", "version": "1.0.0"})

@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "route_not_found"}), 404

@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"error": "method_not_allowed"}), 405

@app.errorhandler(500)
def internal_error(_):
    return jsonify({"error": "internal_server_error"}), 500

if __name__ == "__main__":
    # تشغيل محلي؛ على Render سيُستخدم Gunicorn
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)

# =========================================
# /requirements.txt
# =========================================
Flask>=3.0
Flask-Cors>=4.0
gunicorn>=21.2

# =========================================
# /render.yaml
# =========================================
services:
  - type: web
    name: psych-sanitizer
    env: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn -w 2 -k gthread --threads 8 -t 120 -b 0.0.0.0:$PORT app:app"
    autoDeploy: true
    envVars:
      - key: MAX_INPUT_CHARS
        value: "20000"

# =========================================
# /README.md
# =========================================
# Sanitizer-GPT API
خدمة Flask لتنقية مصطلحات نفسية/جنسية حساسة.
## نقاط النهاية
- `POST /sanitize` و`POST /api/sanitize`: { "input": "..." } → { "output": "..." }
- `GET /openapi.json`: مواصفة OpenAPI 3.1.0 (تتضمّن خادمك + خادم ديناميكي)
- `GET /docs`: Swagger UI
- `GET /healthz`
## تشغيل محليًا
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python app.py
## النشر على Render (Web Service)
Build: `pip install -r requirements.txt`
Start: `gunicorn -w 2 -k gthread --threads 8 -t 120 -b 0.0.0.0:$PORT app:app`
