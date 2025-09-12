import yfinance as yf

def get_forex_data(symbol="EURUSD=X", period="1mo", interval="1d"):
    """
    Lấy dữ liệu forex từ Yahoo Finance qua yfinance.
    symbol: mã cặp forex (VD: "EURUSD=X", "USDJPY=X")
    period: khoảng thời gian (1d, 5d, 1mo, 3mo, 6mo, 1y, 5y, max)
    interval: khung dữ liệu (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period, interval=interval)
    return hist
