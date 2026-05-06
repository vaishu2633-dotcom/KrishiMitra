from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import requests, json, os, hashlib, datetime, random
from functools import wraps

app = Flask(__name__)
app.secret_key = 'krishimitra_secret_2024'
CORS(app)

# ─── In-memory user store (replace with DB in production) ───────────────────
USERS = {}

# ─── API Keys (set as env vars in production) ────────────────────────────────
OWM_API_KEY   = os.getenv('OWM_API_KEY',   'YOUR_OPENWEATHERMAP_KEY')
AGMARKNET_KEY = os.getenv('AGMARKNET_KEY', 'YOUR_AGMARKNET_KEY')
ANTHROPIC_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# ─── Helpers ─────────────────────────────────────────────────────────────────
def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

# ─── Auth ────────────────────────────────────────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username','').strip()
    password = data.get('password','')
    name     = data.get('name','')
    state    = data.get('state','')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if username in USERS:
        return jsonify({'error': 'Username already exists'}), 409
    USERS[username] = {'password': hash_pw(password), 'name': name, 'state': state, 'created': str(datetime.datetime.now())}
    session['user'] = username
    return jsonify({'success': True, 'name': name})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username','').strip()
    password = data.get('password','')
    user = USERS.get(username)
    if not user or user['password'] != hash_pw(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    session['user'] = username
    return jsonify({'success': True, 'name': user['name'], 'state': user['state']})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({'success': True})

@app.route('/api/me')
def me():
    if 'user' not in session:
        return jsonify({'logged_in': False})
    u = USERS.get(session['user'], {})
    return jsonify({'logged_in': True, 'name': u.get('name',''), 'state': u.get('state',''), 'username': session['user']})

# ─── Weather ─────────────────────────────────────────────────────────────────
@app.route('/api/weather')
@login_required
def weather():
    city = request.args.get('city', 'Delhi')
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={city},IN&appid={OWM_API_KEY}&units=metric&cnt=40"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return jsonify(r.json())
    except Exception as e:
        pass
    # Fallback demo data
    return jsonify(get_demo_weather(city))

def get_demo_weather(city):
    base_temp = random.randint(22,35)
    forecasts = []
    for i in range(8):
        dt = datetime.datetime.now() + datetime.timedelta(hours=i*3)
        forecasts.append({
            "dt": int(dt.timestamp()),
            "dt_txt": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "main": {"temp": base_temp + random.uniform(-3,3), "humidity": random.randint(40,85), "feels_like": base_temp-2},
            "weather": [{"description": random.choice(["clear sky","few clouds","scattered clouds","light rain"]), "icon": "01d"}],
            "wind": {"speed": random.uniform(2,12)},
            "rain": {"3h": random.uniform(0,5)} if random.random()>0.6 else {}
        })
    return {"city": {"name": city}, "list": forecasts}

# ─── Crop Recommendation ─────────────────────────────────────────────────────
CROP_DB = {
    "rice":    {"N":80,"P":40,"K":40,"temp":[20,35],"pH":[5.5,7.0],"rain":[150,300],"season":"Kharif","profit":"High","water":"High"},
    "wheat":   {"N":60,"P":60,"K":40,"temp":[10,25],"pH":[6.0,7.5],"rain":[30,100],"season":"Rabi","profit":"Medium","water":"Medium"},
    "maize":   {"N":80,"P":40,"K":20,"temp":[18,27],"pH":[5.5,7.5],"rain":[50,100],"season":"Kharif","profit":"Medium","water":"Medium"},
    "cotton":  {"N":60,"P":30,"K":30,"temp":[21,30],"pH":[6.0,8.0],"rain":[50,100],"season":"Kharif","profit":"High","water":"Medium"},
    "sugarcane":{"N":100,"P":60,"K":60,"temp":[20,35],"pH":[6.0,7.5],"rain":[150,250],"season":"Annual","profit":"High","water":"Very High"},
    "soybean": {"N":40,"P":60,"K":40,"temp":[20,30],"pH":[6.0,7.0],"rain":[50,100],"season":"Kharif","profit":"Medium","water":"Low"},
    "chickpea":{"N":20,"P":60,"K":40,"temp":[10,25],"pH":[6.0,9.0],"rain":[60,90],"season":"Rabi","profit":"Medium","water":"Low"},
    "tomato":  {"N":100,"P":80,"K":60,"temp":[20,27],"pH":[6.0,7.0],"rain":[40,60],"season":"Rabi","profit":"Very High","water":"Medium"},
    "potato":  {"N":80,"P":60,"K":100,"temp":[15,20],"pH":[5.0,6.5],"rain":[50,75],"season":"Rabi","profit":"High","water":"Medium"},
    "onion":   {"N":60,"P":60,"K":60,"temp":[13,24],"pH":[6.0,7.5],"rain":[36,75],"season":"Rabi","profit":"High","water":"Medium"},
    "groundnut":{"N":20,"P":60,"K":30,"temp":[25,30],"pH":[5.5,7.0],"rain":[50,75],"season":"Kharif","profit":"Medium","water":"Low"},
    "mustard": {"N":60,"P":40,"K":40,"temp":[10,25],"pH":[6.0,7.5],"rain":[25,50],"season":"Rabi","profit":"Medium","water":"Low"},
}

@app.route('/api/recommend', methods=['POST'])
@login_required
def recommend():
    d = request.json
    N, P, K = float(d.get('N',50)), float(d.get('P',50)), float(d.get('K',50))
    temp     = float(d.get('temperature',25))
    pH       = float(d.get('pH',6.5))
    rain     = float(d.get('rainfall',100))
    scores = []
    for crop, params in CROP_DB.items():
        score = 100
        score -= abs(N - params['N']) * 0.3
        score -= abs(P - params['P']) * 0.3
        score -= abs(K - params['K']) * 0.3
        if not (params['temp'][0] <= temp <= params['temp'][1]):
            score -= 20
        if not (params['pH'][0] <= pH <= params['pH'][1]):
            score -= 15
        if not (params['rain'][0] <= rain <= params['rain'][1]):
            score -= 10
        scores.append({"crop": crop, "score": max(0, round(score, 1)), **params})
    scores.sort(key=lambda x: x['score'], reverse=True)
    return jsonify({"recommendations": scores[:5]})

# ─── Market Prices (Agmarknet demo + real fallback) ──────────────────────────
MARKET_DEMO = {
    "rice":     {"price": 2100, "min": 1900, "max": 2300, "trend": "+2.3%", "msp": 2183},
    "wheat":    {"price": 2200, "min": 2000, "max": 2400, "trend": "+1.8%", "msp": 2275},
    "maize":    {"price": 1870, "min": 1700, "max": 2050, "trend": "-0.5%", "msp": 2090},
    "cotton":   {"price": 6080, "min": 5800, "max": 6500, "trend": "+3.1%", "msp": 6620},
    "sugarcane":{"price": 315,  "min": 305,  "max": 325,  "trend": "+0.9%", "msp": 340},
    "soybean":  {"price": 4600, "min": 4200, "max": 4900, "trend": "+1.2%", "msp": 4892},
    "chickpea": {"price": 5200, "min": 4900, "max": 5600, "trend": "+2.7%", "msp": 5440},
    "tomato":   {"price": 1800, "min": 1200, "max": 2800, "trend": "+8.4%", "msp": None},
    "potato":   {"price": 1100, "min": 800,  "max": 1600, "trend": "-1.2%", "msp": None},
    "onion":    {"price": 2200, "min": 1500, "max": 3500, "trend": "+5.6%", "msp": None},
    "groundnut":{"price": 5550, "min": 5200, "max": 5900, "trend": "+0.8%", "msp": 6377},
    "mustard":  {"price": 5200, "min": 4900, "max": 5500, "trend": "+1.5%", "msp": 5650},
}

@app.route('/api/market')
@login_required
def market():
    commodity = request.args.get('commodity', '').lower()
    state     = request.args.get('state', 'Maharashtra')
    # Try Agmarknet real API
    try:
        url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={AGMARKNET_KEY}&format=json&filters[Commodity]={commodity}&filters[State]={state}&limit=5"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if data.get('records'):
                return jsonify({'source': 'agmarknet', 'records': data['records']})
    except:
        pass
    # Demo fallback
    if commodity in MARKET_DEMO:
        rec = MARKET_DEMO[commodity]
        history = [round(rec['price'] * (1 + random.uniform(-0.08,0.08))) for _ in range(12)]
        return jsonify({'source': 'demo', 'commodity': commodity, 'state': state, 'current': rec, 'history_12m': history})
    return jsonify({'source': 'demo', 'commodity': commodity, 'state': state, 'current': MARKET_DEMO['wheat'], 'history_12m': [2200]*12})

@app.route('/api/market/all')
@login_required
def market_all():
    return jsonify({'commodities': [
        {'name': k, **v} for k, v in MARKET_DEMO.items()
    ]})

# ─── Disease Detection ────────────────────────────────────────────────────────
DISEASE_DB = {
    "leaf_blight": {"name": "Leaf Blight", "crop": "Rice/Wheat", "cause": "Fungal (Helminthosporium)", "symptoms": "Brown lesions on leaves with yellow halo", "treatment": "Apply Mancozeb 75% WP @ 2.5g/L water. Remove infected parts.", "prevention": "Seed treatment with Thiram, balanced fertilization", "severity": "High"},
    "powdery_mildew": {"name": "Powdery Mildew", "crop": "Wheat/Pea", "cause": "Fungal (Erysiphe)", "symptoms": "White powdery coating on leaves and stems", "treatment": "Spray Triadimefon 25% WP @ 0.5g/L or Sulphur 80% WP", "prevention": "Resistant varieties, avoid excess nitrogen", "severity": "Medium"},
    "bacterial_blight": {"name": "Bacterial Blight", "crop": "Cotton/Rice", "cause": "Bacterial (Xanthomonas)", "symptoms": "Water-soaked lesions turning brown/black at leaf margins", "treatment": "Copper oxychloride 50% WP @ 3g/L. No cure – manage spread.", "prevention": "Disease-free seeds, avoid injury to plants", "severity": "High"},
    "rust": {"name": "Rust Disease", "crop": "Wheat/Sorghum", "cause": "Fungal (Puccinia)", "symptoms": "Orange/brown pustules on leaves and stems", "treatment": "Propiconazole 25% EC @ 1mL/L, Hexaconazole 5% SC", "prevention": "Resistant varieties (HD3086), early sowing", "severity": "Very High"},
    "healthy": {"name": "Healthy Plant", "crop": "General", "cause": "No disease detected", "symptoms": "Plant appears healthy with normal growth", "treatment": "Continue regular maintenance and monitoring", "prevention": "Maintain good agronomic practices", "severity": "None"},
}

@app.route('/api/detect', methods=['POST'])
@login_required
def detect_disease():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    # In production: run ML model (PlantVillage CNN)
    # Demo: return random disease with confidence
    diseases = list(DISEASE_DB.keys())
    weights  = [0.2, 0.15, 0.15, 0.15, 0.35]
    detected = random.choices(diseases, weights=weights)[0]
    confidence = round(random.uniform(72, 97), 1)
    result = DISEASE_DB[detected]
    return jsonify({'disease': result, 'confidence': confidence, 'model': 'PlantVillage-CNN-Demo'})

# ─── Crop Library ─────────────────────────────────────────────────────────────
CROP_LIBRARY = {
    "rice": {"hindi":"चावल","region":"Kharif – All India","duration":"90-120 days","yield":"40-60 q/ha","irrigation":"Flooded field","desc":"India's most important staple, grown across Assam, West Bengal, Odisha, Andhra Pradesh, Tamil Nadu.","tips":["Transplant at 25-day-old seedlings","Maintain 5cm water level during tillering","Apply zinc sulphate for deficiency"]},
    "wheat": {"hindi":"गेहूँ","region":"Rabi – North India","duration":"110-130 days","yield":"40-50 q/ha","irrigation":"4-6 irrigations","desc":"Second most important cereal crop; major states include Punjab, Haryana, UP, MP.","tips":["Sow between Nov 1-15 for best yield","First irrigation at crown root initiation","Apply 120:60:40 kg NPK/ha"]},
    "cotton": {"hindi":"कपास","region":"Kharif – Deccan, Punjab","duration":"150-180 days","yield":"20-25 q/ha seed cotton","irrigation":"6-8 irrigations","desc":"White Gold of India; Bt Cotton transformed Indian agriculture after 2002.","tips":["Use certified Bt hybrid seeds","Spray Chlorpyrifos for bollworm","Harvest when 60% bolls open"]},
    "sugarcane": {"hindi":"गन्ना","region":"Annual – UP, Maharashtra, TN","duration":"300-365 days","yield":"70-100 t/ha","irrigation":"Every 7-10 days","desc":"India is world's 2nd largest producer; supports sugar and ethanol industries.","tips":["Plant single-budded setts at 75cm spacing","Rattle-trash (dried leaves) mulching saves water","Ratoon crop for second season"]},
    "maize": {"hindi":"मक्का","region":"Kharif/Rabi – Widespread","duration":"80-95 days","yield":"45-55 q/ha","irrigation":"Critical at silking","desc":"Versatile crop used for food, feed, and starch; fast-growing hybrid varieties available.","tips":["Plant at 60×25cm spacing","Earthing up prevents lodging","Detasseling improves seed set"]},
    "tomato": {"hindi":"टमाटर","region":"Rabi – All India","duration":"60-70 days","yield":"20-25 t/ha","irrigation":"Drip preferred","desc":"High-value vegetable crop; major source of lycopene; India 2nd largest producer globally.","tips":["Harden seedlings before transplanting","Stake plants at 30cm height","Mulching conserves moisture and reduces weeds"]},
    "onion": {"hindi":"प्याज","region":"Rabi – Maharashtra, Karnataka","duration":"90-120 days","yield":"25-30 t/ha","irrigation":"Sprinkler","desc":"Critical kitchen crop with high export value; Maharashtra's Nashik is India's onion capital.","tips":["Top the onions 2-3 weeks before harvest","Cure bulbs in shade for 7-10 days","Store at low humidity to prevent rot"]},
    "soybean": {"hindi":"सोयाबीन","region":"Kharif – MP, Maharashtra","duration":"90-100 days","yield":"20-25 q/ha","irrigation":"Rainwater mainly","desc":"Protein-rich oilseed; Madhya Pradesh is India's largest producer. Key for edible oil.","tips":["Rhizobium inoculation essential","Avoid waterlogging","Harvest at 14% moisture content"]},
}

@app.route('/api/crop-library')
@login_required
def crop_library():
    return jsonify({'crops': CROP_LIBRARY})

@app.route('/api/crop-library/<name>')
@login_required
def crop_detail(name):
    crop = CROP_LIBRARY.get(name.lower())
    if not crop: return jsonify({'error': 'Not found'}), 404
    return jsonify({'name': name, **crop})

# ─── Chatbot ──────────────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    message  = data.get('message','')
    history  = data.get('history', [])
    language = data.get('language', 'en')

    lang_instruction = {
        'hi': 'Always respond in Hindi (Devanagari script)',
        'mr': 'Always respond in Marathi',
        'pa': 'Always respond in Punjabi',
        'bn': 'Always respond in Bengali',
        'te': 'Always respond in Telugu',
        'ta': 'Always respond in Tamil',
        'gu': 'Always respond in Gujarati',
        'en': 'Respond in English',
    }.get(language, 'Respond in English')

    system_prompt = f"""You are KrishiMitra AI, an expert agricultural advisor for Indian farmers. You have deep knowledge about:
- Indian crops (Kharif, Rabi, Zaid seasons)
- Government schemes: PM-KISAN, Pradhan Mantri Fasal Bima Yojana, Soil Health Card, eNAM
- MSP (Minimum Support Prices) for all crops
- IMD weather advisories and their impact on farming
- ICAR research recommendations
- Pest and disease management
- Market prices and trading on Agmarknet/eNAM
- Modern farming: drip irrigation, precision farming, organic farming
- State-specific advice for all Indian states
{lang_instruction}. Be concise, practical, and empathetic to farmers' challenges. Always give actionable advice."""

    messages = []
    for h in history[-10:]:
        messages.append({'role': h['role'], 'content': h['content']})
    messages.append({'role': 'user', 'content': message})

    if ANTHROPIC_KEY:
        try:
            r = requests.post('https://api.anthropic.com/v1/messages',
                headers={'x-api-key': ANTHROPIC_KEY, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'},
                json={'model': 'claude-haiku-4-5-20251001', 'max_tokens': 1024, 'system': system_prompt, 'messages': messages},
                timeout=30)
            if r.status_code == 200:
                reply = r.json()['content'][0]['text']
                return jsonify({'reply': reply})
        except Exception as e:
            pass

    # Offline demo responses
    kw = message.lower()
    if any(w in kw for w in ['weather','rain','mausam']):
        reply = "🌦️ Based on IMD forecast, expect moderate rainfall this week. Avoid spraying pesticides before rain. Check agromet advisory at imd.gov.in/agrimet"
    elif any(w in kw for w in ['price','bhav','msp','rate']):
        reply = "📊 Current MSP for wheat is ₹2,275/qtl, rice ₹2,183/qtl (2024-25). Check live prices on eNAM portal: enam.gov.in or Agmarknet: agmarknet.gov.in"
    elif any(w in kw for w in ['disease','blight','pest','kida','rog']):
        reply = "🌿 For disease identification, use our Disease Detection feature to upload a leaf photo. For immediate help: contact your KVK (Krishi Vigyan Kendra) or call Kisan Call Centre: 1800-180-1551"
    elif any(w in kw for w in ['scheme','yojana','subsidy','pm-kisan','insurance']):
        reply = "🏛️ Key schemes: PM-KISAN (₹6000/year), PMFBY crop insurance, Soil Health Card, PM Krishi Sinchai Yojana. Apply at pmkisan.gov.in or your nearest CSC."
    elif any(w in kw for w in ['fertilizer','khad','npk','urea']):
        reply = "🌱 For balanced nutrition: get Soil Health Card test done (free from govt). General NPK: 120:60:40 kg/ha for wheat, 80:40:40 for rice. Neem-coated urea is mandatory now."
    else:
        reply = f"🌾 Namaste! I'm KrishiMitra, your AI farm advisor. I can help with crop advice, market prices, weather, government schemes, and disease management. Please ask your question and I'll provide guidance based on ICAR and government recommendations. For urgent help: Kisan Call Centre 1800-180-1551"
    return jsonify({'reply': reply})

# ─── Main Routes ──────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
