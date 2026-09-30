import os
import json
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from jinja2 import Template
from datetime import datetime

# Ambil jalur absolut direktori skrip ini dijalankan
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Memuat File Konfigurasi dari folder Config
config_path = os.path.join(BASE_DIR, "Config", "settings.json")
with open(config_path, "file", encoding="utf-8") as f:
    config = json.load(f)

TICKERS = config["tickers"]
IND = config["indicators"]
THRES = config["thresholds"]

def get_signal(ticker):
    try:
        # Mengambil data jangka pendek (Interval 1 Jam, data 60 hari terakhir)
        df = yf.download(ticker, period="60d", interval="1h", progress=False)
        if df.empty:
            return {"ticker": ticker, "status": "ERROR", "price": 0, "action": "NO SIGNAL"}

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 2. Hitung Indikator Teknikal Menggunakan Parameter dari JSON
        df['EMA_200'] = ta.ema(df['close'], length=IND["ema_trend_length"])
        
        stoch_rsi = ta.stochrsi(
            df['close'], 
            length=IND["stoch_rsi_length"], 
            k=IND["stoch_k"], 
            d=IND["stoch_d"]
        )
        df['STOCHK'] = stoch_rsi.iloc[:, 0]
        df['STOCHD'] = stoch_rsi.iloc[:, 1]
        
        df['CMF'] = ta.cmf(
            df['high'], df['low'], df['close'], df['volume'], 
            length=IND["cmf_length"]
        )

        last_row = df.iloc[-1]
        price = round(float(last_row['close']), 2)

        # 3. Logika Sinyal Menggunakan Batas Batas dari JSON
        # BUY: Tren Naik, Stoch RSI Oversold & Golden Cross, Volume Aliran Dana Positif
        if (last_row['close'] > last_row['EMA_200']) and \
           (last_row['STOCHK'] < THRES["stoch_oversold"]) and \
           (last_row['STOCHK'] > last_row['STOCHD']) and \
           (last_row['CMF'] > 0):
            action = "BUY"
        # SELL: Tren Turun, Stoch RSI Overbought & Dead Cross
        elif (last_row['close'] < last_row['EMA_200']) and \
             (last_row['STOCHK'] > THRES["stoch_overbought"]) and \
             (last_row['STOCHK'] < last_row['STOCHD']):
            action = "SELL"
        else:
            action = "HOLD / NEUTRAL"

        return {
            "ticker": ticker,
            "status": "OK",
            "price": price,
            "action": action,
            "stochk": round(float(last_row['STOCHK']), 2),
            "cmf": round(float(last_row['CMF']), 2)
        }
    except Exception as e:
        print(f"Gagal memproses {ticker}: {e}")
        return {"ticker": ticker, "status": "ERROR", "price": 0, "action": "NO SIGNAL"}

def main():
    results = []
    for ticker in TICKERS:
        print(f"Memproses {ticker}...")
        results.append(get_signal(ticker))

    # 4. Template HTML Statis Lokal
    html_template = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>US Stock Short-Term Trading Signals</title>
        <link rel="stylesheet" href="Assets/style.css">
    </head>
    <body>
        <h1>🚀 US Stock Short-Term Signals</h1>
        <p>Terakhir diperbarui: <strong>{{ last_update }} (WIB)</strong></p>
        <p>Strategi: Momentum & Mean Reversion Jangka Pendek (Interval 1 Jam)</p>
        
        <table>
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Harga Terakhir</th>
                    <th>Sinyal Aksi</th>
                    <th>Stoch RSI (%K)</th>
                    <th>Money Flow (CMF)</th>
                </tr>
            </thead>
            <tbody>
                {% for res in data %}
                <tr>
                    <td><strong>{{ res.ticker }}</strong></td>
                    <td>${{ res.price }}</td>
                    <td style="color: {% if res.action == 'BUY' %}#2ecc71{% elif res.action == 'SELL' %}#e74c3c{% else %}#7f8c8d{% endif %}; font-weight: bold;">
                        {{ res.action }}
                    </td>
                    <td>{{ res.stochk }}</td>
                    <td>{{ res.cmf }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <footer>
            <p>Dibuat otomatis menggunakan Python & GitHub Actions. Bebas Limit Data & Server Mandiri.</p>
        </footer>
    </body>
    </html>
    """
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    template = Template(html_template)
    rendered_html = template.render(data=results, last_update=current_time)

    # Simpan index.html naik satu tingkat (ke folder root utama)
    output_path = os.path.join(BASE_DIR, "..", "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print("File index.html di folder root berhasil diperbarui!")

if __name__ == "__main__":
    main()
