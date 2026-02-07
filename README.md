# Coinbook

## Project Overview
Coinbook is a comprehensive Flask-based web application designed to provide real-time Bitcoin cryptocurrency data visualization. It displays live market metrics including price, market cap, trading volume, and supply information with an interactive dashboard interface.

## Features
- **Real-time Bitcoin Data:** Live price updates in USD
- **Market Metrics Dashboard:** Price, Market Cap, 24h Volume, Supply information
- **Price Change Tracking:** 24-hour and 7-day percentage changes with color coding (green for gains, red for losses)
- **Responsive Design:** Mobile-friendly grid-based layout with CSS media queries
- **Error Handling:** Graceful fallback when data is unavailable
- **Interactive UI:** Hover effects on metric cards for better user experience

## Tech Stack
- **Frontend:** HTML5, CSS3, Jinja2 Templates
- **Backend:** Python, Flask 3.1.0
- **API:** CoinGecko API for real-time cryptocurrency data
- **Server:** Gunicorn/Werkzeug WSGI server
- **Deployment:** Render.com (Python 3 runtime)

## Installation & Setup
To get started with Coinbook locally, clone the repository and install the necessary dependencies:

```bash
git clone https://github.com/tyagi2607/bookopedia.git
cd bookopedia/coinbook
pip install -r requirements.txt
```

### Dependencies
```
Flask==3.1.0
Jinja2==3.1.6
requests==2.32.3
Werkzeug==3.1.3
```

## Usage
To run the application locally:

```bash
python run.py
```

The application will start on `http://0.0.0.0:5000` in debug mode. Visit `http://localhost:5000` in your browser to see the Bitcoin dashboard.

## Project Structure
```
bookopedia/
├── coinbook/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   ├── routes.py            # Main route handler and BtcData class
│   │   ├── services/
│   │   │   └── coins.py         # Bitcoin data fetching service
│   │   ├── static/
│   │   │   └── style.css        # Dashboard styling and responsive design
│   │   └── templates/
│   │       └── index.html       # Bitcoin dashboard UI with metric cards
│   ├── requirements.txt         # Python dependencies
│   └── run.py                   # Application entry point
└── README.md                    # Project documentation
```

## Deployment
The application is deployed on **Render.com** and accessible at:
- **Service URL:** https://bookopedia-qk5z.onrender.com
- **Service ID:** srv-cvpf8s7gj27c73b50fmg
- **Repository:** tyagi2607/bookopedia (main branch)
- **Runtime:** Python 3
- **Status:** Deployed and monitoring active

### Deployment Details
- **Platform:** Render.com
- **Branch:** main
- **Auto-deploy:** Enabled on main branch pushes
- **Recent Deployments:** 
  - February 7, 2026 at 22:23 PM - Deploy live (formatted cards visual)
  - February 7, 2026 at 22:21 PM - Deploy started (formatted cards visual)
  - February 7, 2026 at 22:20 PM - Service restarted

## How It Works
1. **run.py** - Entry point that initializes the Flask app on port 5000
2. **routes.py** - Handles the home route `/` and creates a BtcData object for templating
3. **coins.py** - Queries the CoinGecko API for current Bitcoin metrics (price, market cap, volume, supply)
4. **index.html** - Renders the dashboard with formatted metric cards displaying live data
5. **style.css** - Provides responsive styling with a grid-based layout for metric cards

## API Integration
The application uses the **CoinGecko API** (free tier) to fetch Bitcoin data:
- **Endpoint:** https://api.coingecko.com/api/v3/coins/markets
- **Parameters:** Currency (USD), Coin ID (bitcoin), 7-day price change percentage
- **Data Points:** Price, Market Cap, 24h Volume, Circulating Supply, Max Supply, 24h/7d Changes

## Development
For contributing to this project, please:
1. Fork the repository
2. Create a feature branch
3. Make your changes and test locally
4. Submit a pull request

Code contributions are welcome! Please adhere to the coding conventions and ensure all features are tested before submission.