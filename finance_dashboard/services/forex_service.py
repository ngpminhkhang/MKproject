import yfinance as yf
import pandas as pd
import numpy as np

def get_forex_data(symbol="EURUSD=X", period="3mo", interval="1d", indicators=None):
    """
    Fetch dữ liệu Forex + tính indicators cơ bản.
    indicators: list ["sma", "ema", "rsi", "macd"]
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            # Fallback data nếu không lấy được dữ liệu
            dates = pd.date_range(start='2023-01-01', periods=30, freq='D')
            df = pd.DataFrame({
                'Close': [1.08 + 0.01 * np.sin(i/10) for i in range(30)],
                'Open': [1.08 + 0.01 * np.sin(i/10) for i in range(30)],
                'High': [1.09 + 0.01 * np.sin(i/10) for i in range(30)],
                'Low': [1.07 + 0.01 * np.sin(i/10) for i in range(30)],
                'Volume': [1000000] * 30
            }, index=dates)

        # Tính toán indicators
        if indicators:
            if "sma" in indicators:
                df["SMA20"] = df["Close"].rolling(window=20, min_periods=1).mean()
                df["SMA50"] = df["Close"].rolling(window=50, min_periods=1).mean()
                df["SMA200"] = df["Close"].rolling(window=200, min_periods=1).mean()
            
            if "ema" in indicators:
                df["EMA12"] = df["Close"].ewm(span=12).mean()
                df["EMA26"] = df["Close"].ewm(span=26).mean()
            
            if "rsi" in indicators:
                # Tính RSI
                delta = df["Close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df["RSI"] = 100 - (100 / (1 + rs))
                df["RSI"] = df["RSI"].fillna(50)
            
            if "macd" in indicators:
                # Tính MACD
                ema12 = df["Close"].ewm(span=12).mean()
                ema26 = df["Close"].ewm(span=26).mean()
                df["MACD"] = ema12 - ema26
                df["MACD_signal"] = df["MACD"].ewm(span=9).mean()
                df["MACD_histogram"] = df["MACD"] - df["MACD_signal"]

        return df
    except Exception as e:
        print(f"Error fetching forex data: {e}")
        # Return fallback data
        dates = pd.date_range(start='2023-01-01', periods=30, freq='D')
        return pd.DataFrame({
            'Close': [1.08 + 0.01 * np.sin(i/10) for i in range(30)],
            'Open': [1.08 + 0.01 * np.sin(i/10) for i in range(30)],
            'High': [1.09 + 0.01 * np.sin(i/10) for i in range(30)],
            'Low': [1.07 + 0.01 * np.sin(i/10) for i in range(30)],
            'Volume': [1000000] * 30
        }, index=dates)

def get_macro_data(macro_type):
    """
    Xử lý dữ liệu macro dựa trên loại được chọn
    """
    try:
        if macro_type == 'cot':
            # Lấy và xử lý dữ liệu COT
            cot_df = get_cot_data()
            if not cot_df.empty:
                # Chuyển đổi DataFrame COT thành danh sách dictionary
                macro_data = []
                for _, row in cot_df.iterrows():
                    macro_data.append({
                        'name': row.get('Market_and_Exchange_Names', 'N/A'),
                        'value': row.get('Noncommercial_Positions_Long_All', 0),
                        'signal': 'Bullish' if row.get('Noncommercial_Positions_Long_All', 0) > 0 else 'Bearish'
                    })
                return macro_data
            return []
        
        elif macro_type == 'yield':
            # Lấy dữ liệu yield
            yield_df = get_us10y_yield()
            if not yield_df.empty:
                macro_data = []
                for date, row in yield_df.iterrows():
                    macro_data.append({
                        'name': date.strftime('%Y-%m-%d'),
                        'value': round(row.get('Close', 0), 2),
                        'signal': 'High' if row.get('Close', 0) > 4.0 else 'Low'
                    })
                return macro_data
            return []
        
        elif macro_type == 'inflation':
            # Dữ liệu giả định cho inflation
            return [
                {'name': 'CPI', 'value': 3.2, 'signal': 'Moderate'},
                {'name': 'PCE', 'value': 2.8, 'signal': 'Low'},
                {'name': 'Core CPI', 'value': 3.5, 'signal': 'High'}
            ]
        
        else:
            return []
            
    except Exception as e:
        print(f"Error getting macro data: {e}")
        return []
