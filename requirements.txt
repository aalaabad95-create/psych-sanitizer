# /requirements.txt
Flask>=3.0
Flask-Cors>=4.0
gunicorn>=21.2

# /app.py
import os, logging, re
from typing import List, Tuple, Dict
from flask import Flask, request, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("psych-sanitizer")

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
CORS(app)
app.config["JSON_AS_ASCII"] = False
app.config["JSON_SORT_KEYS"] = False

REPLACEMENTS: Dict[str, str] = {
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
    "منتشي": "في حالة تغير في الوعي نتيجة استخدام مواد مؤثرة نفسيًا",
}

HARAKAT_CLASS = r"[\u064B-\u0652\u0670\u0640]*"
CHAR_MAP = {
    "ا": "[اأإآ]", "أ": "[اأإآ]", "إ": "[اأإآ]", "آ": "[اأإآ]",
    "ى": "[يى]", "ي": "[يى]", "ه": "[هة]", "ة": "[هة]",
    "ؤ": "[ؤو]", "ئ": "[ئىي]", "و": "[ووؤ]", " ": r"\s+",
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
    out = text
    for pattern, rep in _COMPILED_RULES:
        out = pattern.sub(rep, out)
    return out

OPENAPI_SPEC = {
    "openapi": "3.1.0",
    "info": {
        "title": "Sanitizer-GPT API",
        "version": "1.0.0",
        "description": "API مخصص لمعالجة النصوص النفسية الحساسة واستبدالها بصياغات مهنية حيادية.",
    },
    "servers": [{"url": "/"}],  # same-origin للـ GPT Actions
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
                                "properties": {"input": {"type": "string", "description": "النص المطلوب تنقيته"}},
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
                                    "properties": {"output": {"type": "string", "description": "النص بعد التنقية"}},
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
    return jsonify(OPENAPI_SPEC)

@app.get("/docs")
def docs():
    return """
<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Sanitizer-GPT • Docs</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
<style>body{margin:0}#swagger-ui{max-width:1200px;margin:0 auto}</style></head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
<script>window.ui=SwaggerUIBundle({url:'/openapi.json',dom_id:'#swagger-ui'});</script>
</body></html>"""

@app.post("/sanitize")
@app.post("/api/sanitize")
def sanitize_endpoint():
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get("input") or "").strip()
        if not text:
            return jsonify({"error": "النص المدخل مطلوب"}), 400
        max_len = int(os.environ.get("MAX_INPUT_CHARS", "20000"))
        if len(text) > max_len:
            return jsonify({"error": "النص طويل جدًا"}), 413
        out = sanitize_text_strict(text)
        log.info("sanitize chars=%s", len(text))
        return jsonify({"output": out})
    except Exception as e:
        log.exception("sanitize failed: %s", e)
        return jsonify({"error": "حدث خطأ أثناء معالجة الطلب"}), 500

@app.get("/healthz")
@app.get("/health")
def health(): return jsonify({"status": "healthy", "version": "1.0.0"})

@app.get("/")
def home():
    return """
<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>PsychSanitizer API</title>
<style>
body{font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;line-height:1.8}
.card{border:1px solid #ddd;border-radius:14px;padding:16px}
textarea{width:100%;min-height:120px}
pre{background:#f7f7f8;border-radius:8px;padding:12px;overflow:auto}
.row{display:flex;gap:8px;margin-top:8px}
button{padding:10px 14px;border:0;border-radius:10px;background:#4463ff;color:#fff;cursor:pointer}
nav a{margin-right:10px}
</style></head>
<body>
<nav>
  <a href="/docs">📘 التوثيق</a>
  <a href="/openapi.json">🧾 openapi.json</a>
  <a href="/healthz">💚 الصحة</a>
</nav>
<h1>✅ PsychSanitizer (Flask)</h1>
<div class="card">
  <p>أرسل نصًا إلى <code>POST /sanitize</code>.</p>
  <textarea id="inp" placeholder="اكتب هنا..."></textarea>
  <div class="row"><button id="btn">تنقية</button><span id="status"></span></div>
  <h3>النتيجة</h3><pre id="out"></pre>
</div>
<script>
const btn=document.getElementById('btn');
btn.onclick=async()=>{const text=document.getElementById('inp').value;
document.getElementById('status').textContent='...';
const res=await fetch('/sanitize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input:text})});
const data=await res.json();
document.getElementById('status').textContent=res.ok?'تم':'خطأ';
document.getElementById('out').textContent=JSON.stringify(data,null,2);};
</script>
</body></html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

# /render.yaml  (اختياري)
services:
  - type: web
    name: psych-sanitizer
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "gunicorn -w 2 -k gthread --threads 8 -t 120 -b 0.0.0.0:$PORT app:app"
    autoDeploy: true
    envVars:
      - key: MAX_INPUT_CHARS
        value: "20000"
