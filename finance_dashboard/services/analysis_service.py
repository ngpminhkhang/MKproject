# finance_dashboard/services/analysis_service.py
import yfinance as yf
import pandas as pd
import ta  # ĐÃ ĐỔI TỪ pandas_ta sang ta
import requests
from fredapi import Fred
from django.core.cache import cache
from django.conf import settings
import logging
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self):
        # FRED API key - bạn cần đăng ký tại https://fred.stlouisfed.org/docs/api/api_key.html
        self.fred = Fred(api_key=getattr(settings, 'FRED_API_KEY', 'your_fred_api_key_here'))
        
    def get_macro_data(self, cache_timeout=3600):
        """Fetch real macro economic data"""
        cache_key = "macro_data_analysis"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        macro_data = {}
        
        try:
            # VIX - Volatility Index
            vix = yf.Ticker("^VIX")
            vix_hist = vix.history(period="30d")
            if not vix_hist.empty:
                vix_current = float(vix_hist['Close'].iloc[-1])
                vix_change = float(((vix_hist['Close'].iloc[-1] - vix_hist['Close'].iloc[-2]) / vix_hist['Close'].iloc[-2]) * 100)
                macro_data['VIX'] = {
                    'value': round(vix_current, 2),
                    'change': round(vix_change, 2),
                    'signal': 'Low' if vix_current < 20 else 'High' if vix_current > 30 else 'Medium',
                    'history': [float(x) for x in vix_hist['Close'].tail(30).tolist()]
                }
                
            # S&P 500
            sp500 = yf.Ticker("^GSPC")
            sp500_hist = sp500.history(period="30d")
            if not sp500_hist.empty:
                sp500_current = float(sp500_hist['Close'].iloc[-1])
                sp500_change = float(((sp500_hist['Close'].iloc[-1] - sp500_hist['Close'].iloc[-2]) / sp500_hist['Close'].iloc[-2]) * 100)
                macro_data['SP500'] = {
                    'value': round(sp500_current, 2),
                    'change': round(sp500_change, 2),
                    'signal': 'Bullish' if sp500_change > 0 else 'Bearish',
                    'history': [float(x) for x in sp500_hist['Close'].tail(30).tolist()]
                }
                
            # SPY ETF
            spy = yf.Ticker("SPY")
            spy_hist = spy.history(period="30d")
            if not spy_hist.empty:
                spy_current = float(spy_hist['Close'].iloc[-1])
                spy_change = float(((spy_hist['Close'].iloc[-1] - spy_hist['Close'].iloc[-2]) / spy_hist['Close'].iloc[-2]) * 100)
                macro_data['SPY'] = {
                    'value': round(spy_current, 2),
                    'change': round(spy_change, 2),
                    'signal': 'Bullish' if spy_change > 0 else 'Bearish',
                    'history': [float(x) for x in spy_hist['Close'].tail(30).tolist()]
                }
                
            # Gold
            gold = yf.Ticker("GC=F")
            gold_hist = gold.history(period="30d")
            if not gold_hist.empty:
                gold_current = float(gold_hist['Close'].iloc[-1])
                gold_change = float(((gold_hist['Close'].iloc[-1] - gold_hist['Close'].iloc[-2]) / gold_hist['Close'].iloc[-2]) * 100)
                macro_data['Gold'] = {
                    'value': round(gold_current, 2),
                    'change': round(gold_change, 2),
                    'signal': 'Bullish' if gold_change > 0 else 'Bearish',
                    'history': [float(x) for x in gold_hist['Close'].tail(30).tolist()]
                }
                
            # TLT - Long-term Treasury ETF
            tlt = yf.Ticker("TLT")
            tlt_hist = tlt.history(period="30d")
            if not tlt_hist.empty:
                tlt_current = float(tlt_hist['Close'].iloc[-1])
                tlt_change = float(((tlt_hist['Close'].iloc[-1] - tlt_hist['Close'].iloc[-2]) / tlt_hist['Close'].iloc[-2]) * 100)
                macro_data['TLT'] = {
                    'value': round(tlt_current, 2),
                    'change': round(tlt_change, 2),
                    'signal': 'Bullish' if tlt_change > 0 else 'Bearish',
                    'history': [float(x) for x in tlt_hist['Close'].tail(30).tolist()]
                }
                
            # US10Y Yield from FRED
            try:
                us10y_data = self.fred.get_series('DGS10', limit=30)
                if not us10y_data.empty:
                    us10y_current = float(us10y_data.iloc[-1])
                    us10y_prev = float(us10y_data.iloc[-2]) if len(us10y_data) > 1 else us10y_current
                    us10y_change = us10y_current - us10y_prev
                    macro_data['US10Y'] = {
                        'value': round(us10y_current, 2),
                        'change': round(us10y_change, 2),
                        'signal': 'Rising' if us10y_change > 0 else 'Falling',
                        'history': [float(x) for x in us10y_data.tail(30).tolist()]
                    }
            except Exception as e:
                logger.warning(f"FRED US10Y error: {e}")
                # Fallback to Yahoo Finance TNX
                tnx = yf.Ticker("^TNX")
                tnx_hist = tnx.history(period="5d")
                if not tnx_hist.empty:
                    tnx_current = float(tnx_hist['Close'].iloc[-1])
                    tnx_change = float(tnx_hist['Close'].iloc[-1] - tnx_hist['Close'].iloc[-2])
                    macro_data['US10Y'] = {
                        'value': round(tnx_current, 2),
                        'change': round(tnx_change, 2),
                        'signal': 'Rising' if tnx_change > 0 else 'Falling',
                        'history': [float(x) for x in tnx_hist['Close'].tail(30).tolist()]
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching macro data: {e}")
            
        # COT Data (simplified version - real implementation would parse CFTC reports)
        macro_data['COT'] = self.get_cot_summary()
        
        cache.set(cache_key, macro_data, cache_timeout)
        return macro_data
    
    def get_cot_summary(self):
        """Get COT (Commitment of Traders) summary - simplified version"""
        # In production, you would parse CFTC COT reports
        # For now, return mock data with realistic structure
        return {
            'net_positions': 'Bearish USD',
            'long_positions': 45000,
            'short_positions': 60000,
            'signal': 'Bearish',
            'interpretation': 'Large speculators are net short USD'
        }
    
    def get_technical_analysis(self, pair="EURUSD=X", period="3mo", indicators=None, cache_timeout=1800):
        """Get technical analysis for forex pair with real indicators"""
        cache_key = f"technical_{pair}_{period}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            # Fetch data from yfinance
            ticker = yf.Ticker(pair)
            df = ticker.history(period=period, interval="1d")
            
            if df.empty:
                logger.warning(f"No data available for {pair}")
                return None
                
            # Ensure we have enough data for calculations
            if len(df) < 50:
                logger.warning(f"Insufficient data for {pair}: only {len(df)} days")
                return None
                
            # Calculate technical indicators using ta library
            try:
                # SMA
                df['SMA_20'] = ta.trend.SMAIndicator(close=df['Close'], window=20).sma_indicator()
                df['SMA_50'] = ta.trend.SMAIndicator(close=df['Close'], window=50).sma_indicator()
                
                # EMA
                df['EMA_12'] = ta.trend.EMAIndicator(close=df['Close'], window=12).ema_indicator()
                df['EMA_26'] = ta.trend.EMAIndicator(close=df['Close'], window=26).ema_indicator()
                
                # RSI
                df['RSI_14'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
                
                # MACD
                macd = ta.trend.MACD(close=df['Close'], window_fast=12, window_slow=26, window_sign=9)
                df['MACD_12_26_9'] = macd.macd()
                df['MACDs_12_26_9'] = macd.macd_signal()
                
                # Bollinger Bands
                bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
                df['BBU_20_2.0'] = bb.bollinger_hband()
                df['BBL_20_2.0'] = bb.bollinger_lband()
                
                # Stochastic
                stoch = ta.momentum.StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3)
                df['STOCHk_14_3_3'] = stoch.stoch()
                
                # ATR
                df['ATR_14'] = ta.volatility.AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range()
                
            except Exception as ta_error:
                logger.error(f"Error calculating technical indicators for {pair}: {ta_error}")
                return None
            
            # Get latest values for indicators
            latest = df.iloc[-1]
            
            # Helper function to safely convert values
            def safe_float(value, decimals=2):
                try:
                    if pd.notna(value):
                        return round(float(value), decimals)
                    return None
                except (ValueError, TypeError):
                    return None
            
            # Helper function to safely get history
            def safe_history(series, length=30):
                try:
                    history = series.tail(length).tolist()
                    # Convert any NaN values to None for JSON serialization
                    return [float(x) if pd.notna(x) else None for x in history]
                except Exception:
                    return []
            
            technical_data = {
                'pair': pair.replace('=X', ''),
                'price': {
                    'current': safe_float(latest['Close'], 5),
                    'change': safe_float((latest['Close'] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100, 2) if len(df) > 1 else 0,
                    'history': safe_history(df['Close'])
                },
                'indicators': {
                    'SMA_20': {
                        'value': safe_float(latest.get('SMA_20'), 5),
                        'signal': self._get_ma_signal(latest['Close'], latest.get('SMA_20')),
                        'history': safe_history(df.get('SMA_20', pd.Series()))
                    },
                    'SMA_50': {
                        'value': safe_float(latest.get('SMA_50'), 5),
                        'signal': self._get_ma_signal(latest['Close'], latest.get('SMA_50')),
                        'history': safe_history(df.get('SMA_50', pd.Series()))
                    },
                    'RSI_14': {
                        'value': safe_float(latest.get('RSI_14'), 2),
                        'signal': self._get_rsi_signal(latest.get('RSI_14')),
                        'history': safe_history(df.get('RSI_14', pd.Series()))
                    },
                    'MACD_12_26_9': {
                        'value': safe_float(latest.get('MACD_12_26_9'), 6),
                        'signal': self._get_macd_signal(latest.get('MACD_12_26_9'), latest.get('MACDs_12_26_9')),
                        'history': safe_history(df.get('MACD_12_26_9', pd.Series()))
                    },
                    'BBU_20_2.0': {
                        'value': safe_float(latest.get('BBU_20_2.0'), 5),
                        'signal': self._get_bb_signal(latest['Close'], latest.get('BBL_20_2.0'), latest.get('BBU_20_2.0')),
                        'history': safe_history(df.get('BBU_20_2.0', pd.Series()))
                    },
                    'STOCHk_14_3_3': {
                        'value': safe_float(latest.get('STOCHk_14_3_3'), 2),
                        'signal': self._get_stoch_signal(latest.get('STOCHk_14_3_3')),
                        'history': safe_history(df.get('STOCHk_14_3_3', pd.Series()))
                    },
                    'ATR_14': {
                        'value': safe_float(latest.get('ATR_14'), 6),
                        'signal': 'High' if pd.notna(latest.get('ATR_14')) and latest.get('ATR_14', 0) > 0.01 else 'Low',
                        'history': safe_history(df.get('ATR_14', pd.Series()))
                    }
                },
                'labels': [d.strftime('%Y-%m-%d') for d in df.index[-30:]]
            }
            
            cache.set(cache_key, technical_data, cache_timeout)
            return technical_data
            
        except Exception as e:
            logger.error(f"Error in technical analysis for {pair}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _get_ma_signal(self, price, ma):
        """Get moving average signal"""
        if pd.isna(price) or pd.isna(ma):
            return 'Neutral'
        return 'Bullish' if price > ma else 'Bearish'
    
    def _get_rsi_signal(self, rsi):
        """Get RSI signal"""
        if pd.isna(rsi):
            return 'Neutral'
        if rsi > 70:
            return 'Overbought'
        elif rsi < 30:
            return 'Oversold'
        else:
            return 'Neutral'
    
    def _get_macd_signal(self, macd, signal):
        """Get MACD signal"""
        if pd.isna(macd) or pd.isna(signal):
            return 'Neutral'
        return 'Bullish' if macd > signal else 'Bearish'
    
    def _get_bb_signal(self, price, bb_lower, bb_upper):
        """Get Bollinger Bands signal"""
        if pd.isna(price) or pd.isna(bb_lower) or pd.isna(bb_upper):
            return 'Neutral'
        if price > bb_upper:
            return 'Overbought'
        elif price < bb_lower:
            return 'Oversold'
        else:
            return 'Neutral'
    
    def _get_stoch_signal(self, stoch):
        """Get Stochastic signal"""
        if pd.isna(stoch):
            return 'Neutral'
        if stoch > 80:
            return 'Overbought'
        elif stoch < 20:
            return 'Oversold'
        else:
            return 'Neutral'
    
    def get_forex_gainers_losers(self, cache_timeout=1800):
        """Get forex pairs performance for gainers/losers analysis"""
        cache_key = "forex_gainers_losers"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        pairs = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", 
                "NZDUSD=X", "USDCAD=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X"]
        
        forex_data = []
        
        try:
            for pair in pairs:
                ticker = yf.Ticker(pair)
                hist = ticker.history(period="5d", interval="1d")
                
                if not hist.empty and len(hist) >= 2:
                    current = float(hist['Close'].iloc[-1])
                    previous = float(hist['Close'].iloc[-2])
                    daily_change = ((current - previous) / previous) * 100
                    
                    # Weekly change
                    if len(hist) >= 5:
                        week_ago = float(hist['Close'].iloc[-5])
                        weekly_change = ((current - week_ago) / week_ago) * 100
                    else:
                        weekly_change = daily_change
                    
                    # Volume approximation (using volume if available)
                    volume = hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
                    volume_status = 'High' if volume > hist['Volume'].mean() * 1.2 else 'Medium' if volume > hist['Volume'].mean() * 0.8 else 'Low'
                    
                    forex_data.append({
                        'pair': pair.replace('=X', ''),
                        'current_price': round(current, 5),
                        'daily_change': round(daily_change, 2),
                        'weekly_change': round(weekly_change, 2),
                        'volume_status': volume_status,
                        'volatility': self._calculate_volatility(hist['Close'])
                    })
                    
        except Exception as e:
            logger.error(f"Error fetching forex gainers/losers: {e}")
            
        # Sort by daily change (descending for gainers first)
        forex_data.sort(key=lambda x: x['daily_change'], reverse=True)
        
        cache.set(cache_key, forex_data, cache_timeout)
        return forex_data
    
    def _calculate_volatility(self, prices):
        """Calculate simple volatility measure"""
        if len(prices) < 2:
            return 'Low'
        
        returns = prices.pct_change().dropna()
        volatility = returns.std() * 100
        
        if volatility > 1.5:
            return 'High'
        elif volatility > 0.8:
            return 'Medium'
        else:
            return 'Low'
    
    def generate_signals_alerts(self, macro_data, technical_data_list):
        """Generate trading signals based on macro and technical analysis"""
        signals = []
        
        try:
            # Get VIX level for risk sentiment
            vix_level = macro_data.get('VIX', {}).get('value', 20)
            risk_sentiment = 'High Risk' if vix_level > 25 else 'Low Risk' if vix_level < 15 else 'Medium Risk'
            
            for tech_data in technical_data_list:
                if not tech_data:
                    continue
                    
                pair = tech_data['pair']
                indicators = tech_data['indicators']
                
                # RSI signals
                rsi_value = indicators.get('RSI_14', {}).get('value')
                rsi_signal = indicators.get('RSI_14', {}).get('signal')
                
                # MACD signals
                macd_signal = indicators.get('MACD_12_26_9', {}).get('signal')
                
                # Moving average signals
                sma20_signal = indicators.get('SMA_20', {}).get('signal')
                sma50_signal = indicators.get('SMA_50', {}).get('signal')
                
                # Generate combined signals
                signal_strength = 'Weak'
                signal_type = 'Hold'
                details = []
                
                # Bullish signals
                bullish_count = 0
                if rsi_signal == 'Oversold':
                    bullish_count += 1
                    details.append('RSI Oversold')
                if macd_signal == 'Bullish':
                    bullish_count += 1
                    details.append('MACD Bullish')
                if sma20_signal == 'Bullish' and sma50_signal == 'Bullish':
                    bullish_count += 1
                    details.append('MA Bullish Trend')
                
                # Bearish signals
                bearish_count = 0
                if rsi_signal == 'Overbought':
                    bearish_count += 1
                    details.append('RSI Overbought')
                if macd_signal == 'Bearish':
                    bearish_count += 1
                    details.append('MACD Bearish')
                if sma20_signal == 'Bearish' and sma50_signal == 'Bearish':
                    bearish_count += 1
                    details.append('MA Bearish Trend')
                
                # Determine signal
                if bullish_count >= 2:
                    signal_type = 'Buy'
                    signal_strength = 'Strong' if bullish_count >= 3 else 'Medium'
                elif bearish_count >= 2:
                    signal_type = 'Sell'
                    signal_strength = 'Strong' if bearish_count >= 3 else 'Medium'
                
                # Add macro context
                if vix_level > 25:
                    details.append(f'High VIX ({vix_level})')
                elif vix_level < 15:
                    details.append(f'Low VIX ({vix_level})')
                
                signals.append({
                    'pair': pair,
                    'signal': signal_type,
                    'strength': signal_strength,
                    'details': ' + '.join(details) if details else 'No clear signals',
                    'risk_sentiment': risk_sentiment
                })
                
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            
        return signals