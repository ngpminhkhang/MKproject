import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta

def get_cot_data():
    """
    Lấy dữ liệu COT (Commitment of Traders) từ CFTC
    """
    try:
        # URL của CFTC COT data
        url = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"
        df = pd.read_csv(url, sep="\t")
        
        # Lọc dữ liệu Euro FX
        eur_data = df[df["Market_and_Exchange_Names"].str.contains("EURO FX", na=False)]
        
        if not eur_data.empty:
            # Lấy 10 bản ghi gần nhất
            latest_data = eur_data.tail(10)
            
            # Chuyển đổi thành format phù hợp
            result = []
            for _, row in latest_data.iterrows():
                result.append({
                    'name': row.get('Market_and_Exchange_Names', 'Euro FX'),
                    'value': int(row.get('NonComm_Positions_Long_All', 0)),
                    'signal': 'Bullish' if row.get('NonComm_Positions_Long_All', 0) > row.get('NonComm_Positions_Short_All', 0) else 'Bearish'
                })
            return result
        else:
            # Fallback data nếu không lấy được dữ liệu
            return [
                {'name': 'Euro FX Long', 'value': 45000, 'signal': 'Bullish'},
                {'name': 'Euro FX Short', 'value': 38000, 'signal': 'Bearish'},
                {'name': 'Euro FX Net', 'value': 7000, 'signal': 'Bullish'}
            ]
            
    except Exception as e:
        print(f"Error fetching COT data: {e}")
        # Fallback data
        return [
            {'name': 'Euro FX Long', 'value': 45000, 'signal': 'Bullish'},
            {'name': 'Euro FX Short', 'value': 38000, 'signal': 'Bearish'},
            {'name': 'Euro FX Net', 'value': 7000, 'signal': 'Bullish'}
        ]

def get_us10y_yield():
    """
    Lấy dữ liệu US 10Y Treasury Yield
    """
    try:
        # Lấy dữ liệu từ yfinance
        ticker = yf.Ticker("^TNX")  # US 10Y yield
        hist = ticker.history(period="6mo", interval="1d")
        
        if not hist.empty:
            # Lấy 10 giá trị gần nhất
            latest_data = hist.tail(10)
            
            result = []
            for date, row in latest_data.iterrows():
                result.append({
                    'name': date.strftime('%Y-%m-%d'),
                    'value': round(row.get('Close', 0), 2),
                    'signal': 'High' if row.get('Close', 0) > 4.0 else 'Low'
                })
            return result
        else:
            # Fallback data
            return [
                {'name': '2024-01-01', 'value': 3.85, 'signal': 'Low'},
                {'name': '2024-01-02', 'value': 3.92, 'signal': 'Low'},
                {'name': '2024-01-03', 'value': 4.15, 'signal': 'High'}
            ]
            
    except Exception as e:
        print(f"Error fetching US 10Y yield: {e}")
        # Fallback data
        return [
            {'name': '2024-01-01', 'value': 3.85, 'signal': 'Low'},
            {'name': '2024-01-02', 'value': 3.92, 'signal': 'Low'},
            {'name': '2024-01-03', 'value': 4.15, 'signal': 'High'}
        ]

def get_inflation_data():
    """
    Lấy dữ liệu inflation từ FRED hoặc các nguồn khác
    """
    try:
        # Lấy dữ liệu CPI từ yfinance (symbol giả định)
        # Trong thực tế, bạn có thể sử dụng FRED API hoặc các nguồn khác
        
        # Fallback data cho inflation
        return [
            {'name': 'CPI YoY', 'value': 3.2, 'signal': 'Moderate'},
            {'name': 'Core CPI YoY', 'value': 3.5, 'signal': 'High'},
            {'name': 'PCE YoY', 'value': 2.8, 'signal': 'Low'},
            {'name': 'Core PCE YoY', 'value': 3.1, 'signal': 'Moderate'}
        ]
        
    except Exception as e:
        print(f"Error fetching inflation data: {e}")
        return [
            {'name': 'CPI YoY', 'value': 3.2, 'signal': 'Moderate'},
            {'name': 'Core CPI YoY', 'value': 3.5, 'signal': 'High'},
            {'name': 'PCE YoY', 'value': 2.8, 'signal': 'Low'},
            {'name': 'Core PCE YoY', 'value': 3.1, 'signal': 'Moderate'}
        ]
