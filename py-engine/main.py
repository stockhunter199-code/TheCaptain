import os
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from jinja2 import Template
from datetime import datetime

# 1. Daftar saham US yang ingin dipantau (batasi agar tidak terkena limit rate yfinance)
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "AMZN", "META", "GOOGL"]

def get_signal(ticker):
    try:
        # Mengambil data jangka pendek (Interval 1 Jam, data 60 hari terakhir)
        df = yf.download(ticker, period="60d", interval="1h", progress=False)
        if df.empty:
            return {"ticker": ticker, "status": "ERROR", "price": 0, "action": "NO SIGNAL"}

        # Meratakan MultiIndex jika ada (antisipasi perubahan format yfinance)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 2. Hitung Indikator Teknikal
        df['EMA_200'] = ta.ema(df['close'], length=200)
        stoch_rsi = ta.stochrsi(df['close'], length=14, k=3, d=3)
        df['STOCHK'] = stoch_rsi.iloc[:, 0]
        df['STOCHD'] = stoch_rsi.iloc[:, 1]
        df['CMF'] = ta.cmf(df['high'], df['low'], df['close'], df['volume'], length=20)

        # Ambil baris terakhir (data paling terbaru / real-time)
        last_row = df.iloc[-1]
        price = round(float(last_row['close']), 2)

        # 3. Logika Sinyal (Win Rate Tinggi)
        # Beli jika di atas EMA 200, Stochastic Oversold (<20) & Golden Cross, CMF Positif
        if (last_row['close'] > last_row['EMA_200']) and \
           (last_row['STOCHK'] < 20) and \
           (last_row['STOCHK'] > last_row['STOCHD']) and \
           (last_row['CMF'] > 0):
            action = "BUY"
        # Jual jika di bawah EMA 200, Stochastic Overbought (>80) & Dead Cross
        elif (last_row['close'] < last_row['EMA_200']) and \
             (last_row['STOCHK'] > 80) and \
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

    # 4. Render ke HTML menggunakan Jinja2
        # ... (bagian atas kode main.py tetap sama) ...

    # 4. Render ke HTML menggunakan Jinja2
    html_template = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>US Stock Short-Term Trading Signals</title>
        <!-- PERUBAHAN DI SINI: Memanggil file CSS lokal dari folder Assets -->
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
    
    # ... (bagian bawah kode untuk menyimpan file tetap sama seperti sebelumnya) ...

    
        # ... (kode bagian atas tetap sama seperti sebelumnya) ...
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    template = Template(html_template)
    rendered_html = template.render(data=results, last_update=current_time)

    # PERUBAHAN DI SINI: Gunakan "../index.html" untuk menyimpan ke folder root (luar)
    output_path = os.path.join(os.path.dirname(__file__), "..", "index.html")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print("File index.html di folder root berhasil diperbarui!")

if __name__ == "__main__":
    main()
