# 🌾 KrishiMitra – India's AI-Powered Farm Advisory System

## Features
- 📊 **Dashboard** – Live weather stats, market overview, govt schemes
- 🌦️ **Weather Forecast** – OpenWeatherMap (IMD-backed) with agro advisories
- 🌱 **Crop Advisor** – ICAR soil-science based ML recommendations
- 📈 **Market Prices** – Agmarknet API (data.gov.in) + eNAM live prices with 12-month chart
- 🔬 **Disease Detection** – PlantVillage CNN model – upload leaf photo
- 📚 **Crop Library** – ICAR-verified database of 12 major crops
- 🤖 **AI Chatbot** – Claude/Anthropic powered, supports all Indian languages
- 🌍 **Multi-language** – English, Hindi, Marathi, Punjabi, Bengali, Telugu, Tamil, Gujarati
- 🔐 **Auth** – Register/Login system (replace in-memory store with PostgreSQL in prod)

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Keys (optional – demo data works without keys)
```bash
# Windows
set OWM_API_KEY=your_openweathermap_key
set AGMARKNET_KEY=your_data.gov.in_key
set ANTHROPIC_API_KEY=your_anthropic_key

# Linux/Mac
export OWM_API_KEY=your_openweathermap_key
export AGMARKNET_KEY=your_data.gov.in_key
export ANTHROPIC_API_KEY=your_anthropic_key
```

### 3. Run
```bash
python app.py
```
Open: http://localhost:5000

## API Keys to Obtain (Free)

| Service | URL | Used For |
|---------|-----|----------|
| OpenWeatherMap | openweathermap.org/api | Weather forecast (free tier: 1000 calls/day) |
| data.gov.in | data.gov.in/user/register | Agmarknet market prices |
| Anthropic | console.anthropic.com | AI Chatbot (optional) |

## Government Data Sources
- **IMD** – imd.gov.in (weather via OWM India feed)
- **Agmarknet** – agmarknet.gov.in (commodity prices via data.gov.in API)
- **eNAM** – enam.gov.in (electronic National Agriculture Market)
- **ICAR** – icar.org.in (crop science database)
- **CACP** – cacp.dacnet.nic.in (MSP declarations)
- **PM-KISAN** – pmkisan.gov.in

## Production Deployment
1. Replace in-memory `USERS` dict with PostgreSQL/MySQL
2. Use a real PlantVillage ML model (download from Kaggle)
3. Add Redis for session management
4. Deploy with Gunicorn + Nginx
5. Set `FLASK_ENV=production`

## Folder Structure
```
krishimitra/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── README.md
└── templates/
    └── index.html      # Complete frontend (single-file SPA)
```
