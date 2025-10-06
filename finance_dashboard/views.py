# finance_dashboard/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.core.cache import cache
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from finance_dashboard.services.forex_service import get_forex_data, get_macro_data
from finance_dashboard.services.macro_service import get_cot_data, get_us10y_yield, get_inflation_data
from .forms import TechnicalForm, MacroForm, TradeForm, PortfolioForm, InsightForm, InsightSearchForm
from .models import Portfolio, Trade, ForexPair, Insight
from django.db.models import Q
from django.core.paginator import Paginator
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.template.loader import render_to_string
from tenacity import retry, stop_after_attempt, wait_fixed
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ====================== Trang Home ======================

# Helper với retry
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))  # SỬA: stop_after_atempt -> stop_after_attempt
def _yf_last_and_change(symbol: str):
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2d", interval="1d")
    if not hist.empty:
        last = float(hist["Close"].iloc[-1])
        if len(hist) > 1:
            prev = float(hist["Close"].iloc[-2])
            change_pct = round(((last - prev) / prev) * 100, 2) if prev else None
        else:
            change_pct = None
        return {"last": last, "change": change_pct}
    raise ValueError(f"No data for {symbol}")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))  # SỬA: stop_after_atempt -> stop_after_attempt
def _yf_sparkline(symbol: str, points: int = 20):
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1mo", interval="1d")
    if not hist.empty:
        closes = hist["Close"].dropna().tail(points).astype(float).tolist()
        return closes if closes else None
    raise ValueError(f"No sparkline for {symbol}")

def get_symbol_data(symbol, timeout=1800):
    """Get cached symbol data with fallback"""
    key = f"symbol_{symbol}"  # SỬA: symbol_symbol! -> symbol_{symbol}
    data = cache.get(key)
    if data:
        return data
    try:
        data = _yf_last_and_change(symbol)
        cache.set(key, data, timeout=timeout)
        return data
    except Exception as e:
        logger.error(f"Error getting symbol data for {symbol}: {e}")
        return {"last": None, "change": None}

def get_multiple_chart_data(pairs=('EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD'), timeout=3600):  # SỬA: dấu ngoặc
    chart_data = {}
    for pair in pairs:
        cache_key = f"chart_data_{pair}"  # SỬA: chart_data_pair! -> chart_data_{pair}
        cached_data = cache.get(cache_key)
        if cached_data:
            chart_data[pair] = cached_data
            continue
        try:
            import yfinance as yf
            yf_symbol = pair + '=X' if not pair.endswith('=X') else pair
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="30d", interval="1d")
            if not hist.empty:
                decimals = 3 if 'JPY' in pair else 5
                values = [round(float(v), decimals) for v in hist["Close"].tolist()]
                data = {
                    "labels": [d.strftime("%Y-%m-%d") for d in hist.index],
                    "values": values,
                    "high": round(float(hist["High"].max()), decimals),
                    "low": round(float(hist["Low"].min()), decimals),
                    "volume": "High" if hist["Volume"].mean() > 1000000 else "Medium" if "Volume" in hist.columns else "N/A"
                }
                chart_data[pair] = data
                cache.set(cache_key, data, timeout=timeout)
            else:
                logger.error(f"No chart data for {pair}")
                chart_data[pair] = {
                    "labels": [],
                    "values": [],
                    "high": None,
                    "low": None,
                    "volume": "N/A"
                }
        except Exception as e:
            logger.error(f"Error getting chart data for {pair}: {e}")
            chart_data[pair] = {
                "labels": [],
                "values": [],
                "high": None,
                "low": None,
                "volume": "N/A"
            }
    return chart_data

def home(request):
    indices_symbols = {"DXY": "DX-Y.NYB", "SP500": "^GSPC", "US10Y": "^TNX", "Gold": "GC=F"}  # SỬA: AGSPC -> ^GSPC, ATNX -> ^TNX
    indices = {}
    for name, sym in indices_symbols.items():
        try:
            raw = get_symbol_data(sym)  # Sử dụng cached function
            if name == "US10Y":
                indices[name] = round(raw["last"] / 10, 2) if raw["last"] else None  # SỬA: row -> raw
            else:
                indices[name] = round(raw["last"], 2) if raw["last"] else None  # SỬA: row -> raw
        except Exception as e:
            logger.error(f"Error fetching {name}: {e}")
            indices[name] = None

    chart_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']
    symbols = [pair + "=X" for pair in chart_pairs]  # SỬA: symbol -> symbols

    forex_data = []
    for i, pair in enumerate(symbols):
        try:
            raw = get_symbol_data(pair)  # Sử dụng cached function
            history = _yf_sparkline(pair, points=20)
            decimals = 3 if 'JPY' in chart_pairs[i] else 5
            rounded_last = round(raw["last"], decimals) if raw["last"] is not None else None  # SỬA: row -> raw
            rounded_history = [round(v, decimals) for v in history] if history else []
            forex_data.append({
                "pair": chart_pairs[i],
                "last": rounded_last,
                "change": raw["change"],  # SỬA: row -> raw
                "history": json.dumps(rounded_history) if rounded_history else json.dumps([]),
            })
        except Exception as e:
            logger.error(f"Error fetching forex {chart_pairs[i]}: {e}")
            forex_data.append({
                "pair": chart_pairs[i],
                "last": None,
                "change": None,
                "history": json.dumps([]),
            })

    all_chart_data = get_multiple_chart_data(chart_pairs)
    chart = all_chart_data.get('EURUSD', {
        "labels": [], "values": [], "high": None, "low": None, "volume": "N/A"
    })

    vix_data = get_symbol_data("^VIX")
    risk_on = True if vix_data["last"] and vix_data["last"] < 20 else False
    vix = round(vix_data["last"], 2) if vix_data["last"] else None

    # ETF flows với retry
    etf_flows = []
    try:
        import yfinance as yf
        for etf in ["SPY", "TLT", "GLD"]:
            t = yf.Ticker(etf)
            h = t.history(period="5d", interval="1d")
            if not h.empty:
                last_row = h.iloc[-1]  # SỬA: lloc -> iloc
                approx_flow_m = float((last_row.get("Close", 0) - last_row.get("Open", 0)) * last_row.get("Volume", 0)) / 1_000_000.0
                etf_flows.append({"name": f"{etf}", "flow": round(approx_flow_m, 2)})  # SỬA: sửa cấu trúc list
    except Exception as e:
        logger.error(f"ETF flow error: {e}")
        etf_flows = [{"name": etf, "flow": None} for etf in ["SPY", "TLT", "GLD"]]  # SỬA: sửa cấu trúc list

    context = {
        "indices": indices,
        "forex_data": forex_data,
        "chart": chart,
        "all_chart_data": json.dumps({k: v for k, v in all_chart_data.items() if v}),  # Chỉ include non-None
        "risk_on": risk_on,
        "vix": vix,
        "gold": indices.get("Gold"),
        "us10y": indices.get("US10Y"),
        "etf_flows": etf_flows,
    }
    return render(request, "finance_dashboard/home.html", context)

# ====================== Trang Analysis ==============================

def analysis(request):
    from .services.analysis_service import AnalysisService  # SỬA: from_services -> from .services
    analysis_service = AnalysisService()

    # Get selected pair and indicator from request
    selected_pair = request.GET.get('pair', 'EURUSD')
    selected_indicator = request.GET.get('indicator', 'RSI_14')
    selected_macro = request.GET.get('macro', 'VIX')

    # Add =X suffix for yfinance if not present
    if not selected_pair.endswith('=X'):
        yf_pair = selected_pair + '=X'
    else:
        yf_pair = selected_pair
    selected_pair = selected_pair.replace('=X', '')

    # Fetch macro data
    macro_data = analysis_service.get_macro_data()

    # Forex pairs for technical analysis
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD']  # SỬA: symbol -> symbols
    symbol_yf = [pair + '=X' for pair in symbols]  # SỬA: symbol_yf -> symbol_yf

    # Get technical analysis for selected pair
    technical_data = analysis_service.get_technical_analysis(yf_pair)

    # Get gainers/losers data
    gainers_losers = analysis_service.get_forex_gainers_losers()

    # Generate signals and alerts - get technical data for all pairs
    technical_data_list = []
    for pair in symbol_yf:  # SỬA: symbol_vf -> symbol_yf
        tech_data = analysis_service.get_technical_analysis(pair)
        if tech_data:
            technical_data_list.append(tech_data)

    signals_alerts = analysis_service.generate_signals_alerts(macro_data, technical_data_list)

    # Prepare macro summary for table
    macro_summary = []
    for key, data in macro_data.items():
        if isinstance(data, dict) and 'value' in data and 'signal' in data:
            macro_summary.append({
                'name': key,
                'value': data['value'],
                'signal': data['signal']
            })

    context = {
        'macro_data': json.dumps(macro_data) if macro_data else '{}',
        'technical_data': json.dumps(technical_data) if technical_data else '{}',
        'macro_summary': macro_summary,
        'signals_alerts': signals_alerts,
        'gainers_losers': gainers_losers,
        'selected_pair': selected_pair,
        'selected_indicator': selected_indicator,
        'selected_macro': selected_macro,
        'symbols': symbols,  # SỬA: symbol -> symbols
        'forex_pairs': symbols,  # Thêm danh sách pairs cho Select Pair
        'available_indicators': ['SMA_20', 'SMA_50', 'RSI_14', 'MACD_12_26_9', 'BBU_20_2.0', 'STOCHk_14_3_3', 'ATRr_14'],
        'macro_indicators': list(macro_data.keys()) if macro_data else [],
        'macro_data_raw': macro_data,
        'technical_data_raw': technical_data
    }
    return render(request, "finance_dashboard/analysis.html", context)

# AJAX endpoint for dynamic analysis updates
def analysis_ajax(request):
    """AJAX endpoint for updating analysis data without page reload"""
    if request.method == 'GET':
        from .services.analysis_service import AnalysisService
        analysis_service = AnalysisService()

        # Get parameters
        pair = request.GET.get('pair', 'EURUSD')
        indicator = request.GET.get('indicator', 'RSI_14')
        macro_indicator = request.GET.get('macro', 'VIX')
        logger.info(f"AJAX request - pair: {pair}, indicator: {indicator}")

        # Add =X suffix for yfinance if not present
        if not pair.endswith('=X'):  # SỬA: ; -> :
            yf_pair = pair + '=X'
        else:
            yf_pair = pair
            pair = pair.replace('=X', '')
        
        response_data = {}
        try:
            # Get technical data if pair is requested
            if pair:
                logger.info(f"Fetching technical data for {yf_pair}")
                technical_data = analysis_service.get_technical_analysis(yf_pair)
                if technical_data:
                    logger.info(f"Technical data retrieved successfully for {yf_pair}")
                    response_data['technical'] = technical_data
                    response_data['success'] = True
                else:
                    logger.warning(f"No technical data available for {yf_pair}")
                    response_data['error'] = f'No technical data available for {pair}'
                    response_data['success'] = False

            # Get macro data if macro indicator is requested
            if macro_indicator:
                try:
                    macro_data = analysis_service.get_macro_data()
                    response_data['macro'] = {
                        'indicator': macro_indicator,
                        'data': macro_data.get(macro_indicator, {}),
                        'full_data': macro_data
                    }
                except Exception as macro_error:
                    logger.error(f"Error fetching macro data: {macro_error}")  # SỬA: {macro_error} -> {macro_error}

            # Generate updated signals for Signals & Alerts tab
            if pair and response_data.get('success', False):
                try:
                    symbol_yf = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'USDCHF=X', 'AUDUSD=X']
                    technical_data_list = []
                    for symbol in symbol_yf:
                        tech_data = analysis_service.get_technical_analysis(symbol)
                        if tech_data:
                            technical_data_list.append(tech_data)
                    macro_data = analysis_service.get_macro_data()
                    signals_alerts = analysis_service.generate_signals_alerts(macro_data, technical_data_list)
                    response_data['signals'] = signals_alerts
                except Exception as signals_error:
                    logger.error(f"Error generating signals: {signals_error}")  # SỬA: {signals_error} -> {signals_error}

        except Exception as e:
            logger.error(f"Error in analysis_ajax: {e}")  # SỬA: {e} -> {e}
            response_data = {
                'error': f'Server error: {str(e)}',
                'success': False
            }

        logger.info(f"AJAX response: {list(response_data.keys())}")  # SỬA: response_data.keys() -> list(response_data.keys())
        return JsonResponse(response_data)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)  # SỬA: thiếu dấu '

# ====================== Trang Details ======================

def details(request, symbol=None):
    """
    Hiển thị chi tiết cho một symbol cụ thể (forex, stock, other).
    """
    # --- Lấy danh sách trades liên quan đến symbol ---
    trades = Trade.objects.filter(symbol=symbol).order_by("-date") if symbol else []

    # --- Tính các metrics cơ bản ---
    if symbol and trades.exists():
        # Tính toán metrics từ trades
        total_trades = trades.count()
        
        winning_trades = 0
        losing_trades = 0
        total_pnl = 0
        
        for trade in trades:
            pnl_value = float(trade.pnl)
            total_pnl += pnl_value
            if pnl_value > 0:
                winning_trades += 1
            elif pnl_value < 0:
                losing_trades += 1

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

        metrics = {
            "Symbol": symbol,
            "Total Trades": total_trades,
            "Win Rate": f"{win_rate:.1f}%",
            "Total PnL": f"{total_pnl:.2f}",
            "Average PnL": f"{avg_pnl:.2f}",
            "Winning Trades": winning_trades,
            "Losing Trades": losing_trades,
        }
    else:
        metrics = {
            "Symbol": symbol or "N/A",
            "Total Trades": 0,
            "Win Rate": "0%",
            "Total PnL": "0.00",
            "Average PnL": "0.00",
            "Winning Trades": 0,
            "Losing Trades": 0,
        }

    # --- Tạo chart data (giả lập hoặc real data) ---
    try:
        # Thử lấy real chart data
        real_data = get_real_chart_data(symbol)
        if real_data:
            chart_data = real_data['chart_data']
            labels = chart_data['labels'][-30:]  # Lấy 30 ngày gần nhất
            values = chart_data['values'][-30:]
        else:
            # Fallback: tạo chart giả lập
            labels = [(datetime.now() - timedelta(days=x)).strftime("%Y-%m-%d") for x in range(30)][::-1]
            base_value = 1.1 if 'USD' in symbol else 100.0
            values = [base_value + (0.001 * np.random.randn()) for _ in range(30)]
    except Exception as e:
        logger.error(f"Error generating chart data for {symbol}: {e}")
        # Fallback đơn giản
        labels = []
        values = []

    # --- Chuẩn bị context cho template ---
    context = {
        "trades": trades,
        "metrics": metrics,
        "labels": labels,
        "values": values,
        "symbol": symbol or "N/A",
        "label": f"Details for {symbol}" if symbol else "No Symbol Available",
        "safe_id": symbol.replace("/", "_").replace(" ", "_").replace("=", "_") if symbol else "default",
    }
    return render(request, "finance_dashboard/details.html", context)

# ====================== Trang Insights ====================

def insights(request):
    form = InsightSearchForm(request.GET or None)
    insights_qs = Insight.objects.order_by('-date')

    if form.is_valid():
        q = form.cleaned_data.get('q')
        result = form.cleaned_data.get('result')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        # THÊM FILTER CATEGORY
        category = request.GET.get('category', '')
        
        if q:
            insights_qs = insights_qs.filter(
                Q(title__icontains=q) |
                Q(summary__icontains=q) |
                Q(reason__icontains=q) |
                Q(analysis__icontains=q) |
                Q(lessons__icontains=q) |
                Q(tags__icontains=q)
            )

        # FILTER THEO CATEGORY
        if category and category != "All":
            insights_qs = insights_qs.filter(category=category)

        if result:
            insights_qs = insights_qs.filter(result=result)

        if date_from:
            insights_qs = insights_qs.filter(date__gte=date_from)

        if date_to:
            insights_qs = insights_qs.filter(date__lte=date_to)

    # Phân trang
    paginator = Paginator(insights_qs, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'form': form,
        'page_obj': page_obj,
        'insight_form': InsightForm(),
    }

    return render(request, "finance_dashboard/insights.html", context)

def about(request):
    return render(request, "finance_dashboard/about.html")

# ====================== Trang Portfolio ============================


def portfolio(request):
    trade_type_filter = request.GET.get("type", "All")
    
    # Xử lý cho cả user đã login và khách
    if request.user.is_authenticated:
        portfolios = Portfolio.objects.filter(user=request.user).prefetch_related("trades")
        if not portfolios.exists():
            messages.warning(request, "No portfolios found. Please create a portfolio first.")
    else:
        # CHO KHÁCH: Hiển thị portfolio public với xử lý lỗi
        try:
            # Thử filter theo is_public=True
            portfolios = Portfolio.objects.filter(is_public=True).prefetch_related("trades")
            if not portfolios.exists():
                portfolios = Portfolio.objects.none()
                messages.info(request, "No public portfolios available. Log in to create your own portfolio.")
        except Exception as e:
            # Nếu field is_public chưa có, hiển thị thông báo và portfolio rỗng
            logger.warning(f"is_public field not available: {e}")
            portfolios = Portfolio.objects.none()
            messages.info(request, "Public portfolios feature is not available yet. Please log in to view your portfolios.")

    # Xử lý form POST (chỉ cho user đã login)
    if request.method == "POST":
        if request.user.is_authenticated:
            trade_form = TradeForm(request.POST, user=request.user)
            if trade_form.is_valid():
                trade = trade_form.save(commit=False)
                trade.symbol = trade_form.cleaned_data.get('symbol')
                trade.save()
                messages.success(request, "Trade added successfully!")
                return redirect("portfolio")
            else:
                logger.error(f"Trade form errors: {trade_form.errors}")
                messages.error(request, f"Error adding trade: {trade_form.errors.as_text()}")
        else:
            messages.error(request, "You must be logged in to add a trade.")
            return redirect('login')  # Redirect đến login page
    else:
        # GET request - khởi tạo form
        trade_form = TradeForm(user=request.user if request.user.is_authenticated else None)

    # Tính toán analytics chỉ khi có portfolios
    if portfolios:
        analytics_data = compute_portfolio_analytics(portfolios)
    else:
        analytics_data = {}

    # Chuẩn bị trades theo filter
    for p in portfolios:
        trades = p.trades.all()
        if trade_type_filter != "All":
            trades = trades.filter(trade_type=trade_type_filter)
        p.filtered_trades = trades

    # Gán trade.ref_insight cho template
    for portfolio in portfolios:
        for trade in portfolio.filtered_trades:
            trade.ref_insight = None
            if trade.ref and 'Insight #' in trade.ref:
                try:
                    insight_id = trade.ref.replace('Insight #', '').strip()
                    # CHỈ LẤY INSIGHT NẾU insight_id LÀ SỐ
                    if insight_id.isdigit():
                        trade.ref_insight = Insight.objects.filter(id=int(insight_id)).first()
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing insight ID from ref '{trade.ref}': {e}")
                    trade.ref_insight = None

    return render(
        request,
        "finance_dashboard/portfolio.html",
        {
            "trade_form": trade_form,
            "portfolios": portfolios,
            "analytics_data": analytics_data,
            "insight_form": InsightForm(),
            "active_tab": trade_type_filter,
        },
    )

def compute_portfolio_analytics(portfolios):
    analytics_data = []

    if not portfolios.exists():
        analytics_data.append({
            "total_trades": 0,
            "win_rate": 0,
            "expectancy": 0,
            "net_pnl": 0,
            "max_drawdown": 0,
            "avg_risk": 0,
        })
        return analytics_data

    for portfolio in portfolios:
        trades = portfolio.trades.all().order_by("date")
        total_trades = trades.count()

        if total_trades > 0:
            pnl_list = [float(t.pnl or 0) for t in trades]
            wins = [p for p in pnl_list if p > 0]
            losses = [p for p in pnl_list if p < 0]

            net_pnl = sum(pnl_list)
            win_rate = (len(wins) / total_trades * 100) if total_trades else 0
            expectancy = (np.mean(wins) if wins else 0) - (np.mean(losses) if losses else 0)

            equity = float(portfolio.amount)
            peak = equity
            max_dd = 0.0
            for p in pnl_list:
                equity += p
                peak = max(peak, equity)
                dd = (equity - peak) / peak if peak != 0 else 0.0
                if dd < max_dd:
                    max_dd = dd

            risks = [float(t.risk) for t in trades if t.risk is not None]
            avg_risk = float(np.mean(risks)) if risks else 0.0

            analytics = {
                "total_trades": total_trades,
                "win_rate": round(win_rate, 2),
                "expectancy": round(expectancy, 2),
                "net_pnl": round(net_pnl, 2),
                "max_drawdown": round(max_dd * 100, 2),
                "avg_risk": round(avg_risk, 2),
            }
        else:
            analytics = {
                "total_trades": 0,
                "win_rate": 0,
                "expectancy": 0,
                "net_pnl": 0,
                "max_drawdown": 0,
                "avg_risk": 0,
            }

        analytics_data.append(analytics)

    return analytics_data

# ================= CRUD cho Insight ==========================

@login_required
def create_insight(request, portfolio_id=None):
    """
    Tao insight chung (trang Insights). Nếu truyền portfolio_id, sẽ gán insight.portfolio_ref.
    """
    if request.method == "GET":
        # Trả về form create
        form = InsightForm()
        context = {
            'form': form
        }
        
        # LUÔN trả về modal template cho HTMX
        return render(request, "finance_dashboard/partials/create_insight_modal.html", context)
    
    elif request.method == "POST":
        if request.user.is_authenticated:
            form = InsightForm(request.POST, request.FILES)
            if form.is_valid():
                insight = form.save(commit=False)
                # KHÔNG gán portfolio_ref nếu tạo từ trang Insights (độc lập)
                # Chỉ gán portfolio_ref nếu có portfolio_id
                if portfolio_id:
                    insight.portfolio_ref = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
                insight.save()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True})
                messages.success(request, "Insight created successfully!")
                return redirect("insights")
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': form.errors.as_text()})
                messages.error(request, f"Error creating insight: {form.errors.as_text()}")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': 'You must be logged in to create an insight.'})
            messages.error(request, "You must be logged in to create an insight.")
            return redirect("insights")

@login_required
def create_insight_for_portfolio(request, portfolio_id):
    """
    View phục vụ modal "Add Insight for <portfolio>" trong portfolio.html hiện tại.
    - Gán insight.portfolio_ref = portfolio
    - Gán portfolio.ref_insight = insight (để hiển thị Linked Insight)
    - Hỗ trợ AJAX (trả JSON) và fallback redirect.
    """
    if request.method == "POST":
        if not request.user.is_authenticated:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': 'You must be logged in to create an insight.'})
            messages.error(request, "You must be logged in to create an insight.")
            return redirect("portfolio")

        portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
        form = InsightForm(request.POST)

        if form.is_valid():
            insight = form.save(commit=False)
            insight.portfolio_ref = portfolio
            insight.save()

            # Link ngược lại để Portfolio có "Linked Insight"
            portfolio.ref_insight = insight
            portfolio.save(update_fields=["ref_insight"])  # SỬA: uodate_fields -> update_fields

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'insight_id': insight.id})
            messages.success(request, "Insight created successfully for portfolio!")
            return redirect("portfolio")
        else:
            logger.error(f"Insight form errors: {form.errors}")  # SỬA: ) -> )
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors.as_text()})
            messages.error(request, f"Error creating insight: {form.errors.as_text()}")  # SỬA: ) -> )
            return redirect("portfolio")

    # GET không hỗ trợ tạo, quay lại trang portfolio
    return redirect("portfolio")

@login_required
def edit_insight(request, insight_id):
    insight = get_object_or_404(Insight, id=insight_id)
    
    if request.method == "GET":
        # Trả về form edit
        form = InsightForm(instance=insight)
        context = {
            'insight': insight,
            'form': form
        }
        
        # LUÔN trả về modal template cho HTMX
        return render(request, "finance_dashboard/partials/edit_insight_modal.html", context)
    
    elif request.method == "POST":
        form = InsightForm(request.POST, request.FILES, instance=insight)
        
        if form.is_valid():
            # Xử lý remove attachment nếu được chọn
            if request.POST.get('remove_attachment') == 'true':
                if insight.attached_image:
                    insight.attached_image.delete(save=False)
                    insight.attached_image = None
                if insight.attached_file:
                    insight.attached_file.delete(save=False)
                    insight.attached_file = None
            
            # Lưu form
            form.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            
            messages.success(request, "Insight updated successfully!")
            return redirect("insights")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors.as_text()})
            
            messages.error(request, "Error updating insight.")
            return redirect("insights")

@login_required
def delete_insight(request, insight_id):
    insight = get_object_or_404(Insight, id=insight_id)
    
    if request.method == "POST":
        # Xóa file đính kèm trước khi xóa insight
        if insight.attached_image:
            insight.attached_image.delete(save=False)
        if insight.attached_file:
            insight.attached_file.delete(save=False)
            
        insight.delete()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        messages.success(request, "Insight deleted successfully!")
        return redirect("insights")
    
    return JsonResponse({'success': False, 'errors': 'Invalid request method'})

def search_insights(request):
    """
    Search nội trang cho trang Insights (HTML).
    Trả về HTML của partials/_insight_list.html, có phần trang (6 items/trang).
    """
    logger.debug("Request GET params: %s", request.GET)

    q = request.GET.get("q", "")
    category = request.GET.get("category", "")
    result = request.GET.get("result", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    insights_qs = Insight.objects.order_by('-date')

    if q:
        insights_qs = insights_qs.filter(
            Q(title__icontains=q) |
            Q(summary__icontains=q) |
            Q(reason__icontains=q) |
            Q(analysis__icontains=q) |
            Q(lessons__icontains=q) |
            Q(tags__icontains=q)
        )

    if category:
        insights_qs = insights_qs.filter(category=category)
    if result:
        insights_qs = insights_qs.filter(result=result)
    if date_from:
        insights_qs = insights_qs.filter(date__gte=date_from)
    if date_to:
        insights_qs = insights_qs.filter(date__lte=date_to)

    paginator = Paginator(insights_qs, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    html = render_to_string(
        "finance_dashboard/partials/_insight_list.html",
        {"page_obj": page_obj},
        request=request
    )
    return HttpResponse(html)

def insight_modal(request, pk):
    """
    Trả về chi tiết Insight để hiển thị trong modal
    """
    insight = get_object_or_404(Insight, pk=pk)
    
    is_htmx = request.headers.get("HX-Request") == 'true' or request.META.get("HTTP_HX_REQUEST") == 'true'
    
    if is_htmx:
        return render(request, "finance_dashboard/partials/insight_modal.html", {"insight": insight})
    else:
        # Fallback: redirect to insights page với highlight
        return redirect(f"{reverse('insights')}?highlight={insight.id}")

    if is_htmx:
        # Dùng modal đã có sẵn ở portfolio có class show + display:block để hiển thị ngay
        return render(request, "finance_dashboard/partials/insight_modal.html", {"insight": insight})  # SỬA: trade_insight_modal -> insight_modal
    else:
        # Fallback: trang chi tiết đầy đủ (nếu có)
        return render(request, "finance_dashboard/insights.html", {"insight": insight})

# ====================== TRADES - INSIGHT MODAL (tuỳ chọn) ====================

@login_required
def trade_insight_modal(request, trade_id):
    """
    Mở modal để gắn/chỉnh Insight cho 1 Trade.
    Template: finance_dashboard/partials/trade_insight_modal.html
    Cơ chế:
    - Nếu portfolio đã có ref_insight thì load insight để edit.
    - Khi lưu, gán insight cho portfolio (ref_insight) và set trade.ref = "Insight #<id>"
    - Hỗ trợ AJAX (XHR) trả JSON.
    """
    trade = get_object_or_404(Trade, id=trade_id, portfolio__user=request.user)  # SỬA: portfolio_user -> portfolio__user

    # Nếu portfolio đã có linked insight thì edit, ngược lại tạo mới
    existing_insight = trade.portfolio.ref_insight if hasattr(trade.portfolio, "ref_insight") else None

    if request.method == "POST":
        form = InsightForm(request.POST, instance=existing_insight)
        if form.is_valid():
            insight = form.save(commit=False)
            insight.portfolio_ref = trade.portfolio
            insight.save()

            # Link back
            trade.portfolio.ref_insight = insight
            trade.portfolio.save(update_fields=["ref_insight"])

            trade.ref = f"Insight #{insight.id}"  # SỬA: Insight -> insight
            trade.save(update_fields=["ref"])

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # SỬA: Wi++{ -> With
                return JsonResponse({'success': True, 'insight_id': insight.id})
            messages.success(request, "Insight saved successfully!")
            return redirect("portfolio")
        else:
            # Return errors for AJAX or fallback
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors.as_text()})
            messages.error(request, "Error saving insight.")
            return redirect("portfolio")
    else:
        form = InsightForm(instance=existing_insight)  # SỬA: instance-existing_insight -> instance=existing_insight

    # Nếu là HTMX/XHR request, trả partial modal để inject vào DOM
    is_htmx = request.headers.get('HX-Request') == 'true' or request.META.get('HTTP_HX_REQUEST') == 'true' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    context = {
        "trade": trade,
        "form": form,
        "insight": existing_insight,
    }

    if is_htmx:
        return render(request, "finance_dashboard/partials/trade_insight_modal.html", context)
    else:
        # fallback: render a page containing modal (or redirect)
        return render(request, "finance_dashboard/trade_insight_page.html", context)

# ====================== TRADES FILTER (ALL / LIVE / BACKTEST) ====================

def filter_trades(request, trade_type=None):
    """
    Lọc trades theo loại: Live / Backtest / All (optional endpoint nếu bạn muốn hook với HTMX).
    Template gợi ý: finance_dashboard/partials/trade_table.html
    """
    trades = Trade.objects.all().order_by("-date")
    if trade_type in ["Live", "Backtest"]:
        trades = trades.filter(trade_type=trade_type)
    return render(request, "finance_dashboard/partials/trade_table.html", {"trades": trades})

def get_real_search_data(symbol, symbol_type='forex'):
    """Get real data for search results using yfinance"""
    try:
        import yfinance as yf
        # Add proper suffix for yfinance
        if symbol_type == 'forex' and not symbol.endswith('=X'):
            yf_symbol = symbol + '=X'
        else:
            yf_symbol = symbol

        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="5d", interval="1d")
        if not hist.empty:
            last = float(hist["Close"].iloc[-1])
            if len(hist) > 1:
                prev = float(hist["Close"].iloc[-2])
                change = round(((last - prev) / prev) * 100, 2) if prev else 0  # SỬA: thiếu dấu )
            else:
                change = 0

            history = hist["Close"].astype(float).tolist()[-5:]  # Last 5 days

            # Estimate volume category based on recent volume
            avg_volume = hist["Volume"].mean() if "Volume" in hist.columns else 0
            if avg_volume > 1000000:
                volume = 'High'
            elif avg_volume > 100000:
                volume = 'Medium'
            else:
                volume = 'Low'

            return {
                'last': round(last, 4 if symbol_type == 'forex' else 2),
                'change': change,
                'history': history,
                'volume': volume
            }
    except Exception as e:
        logger.warning("Real search data error for %s: %s", symbol, e)

    # Fallback data
    return {
        'last': 0.0,
        'change': 0.0,
        'history': [0.0] * 5,
        'volume': 'N/A'
    }

def search_view(request):
    query = request.GET.get('query', '').upper()

    # Define supported symbols
    forex_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
    stock_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META']
    results = []

    if query:
        # Search forex pairs
        for symbol in forex_symbols:
            if query in symbol:
                data = get_real_search_data(symbol, 'forex')
                results.append({
                    'pair': symbol,
                    'data': data,
                    'type': 'Forex'
                })

        # Search stocks
        for symbol in stock_symbols:
            if query in symbol:
                data = get_real_search_data(symbol, 'stock')
                results.append({
                    'pair': symbol,
                    'data': data,
                    'type': 'Stock'
                })

    html = render_to_string('finance_dashboard/search_results.html', {'results': results, 'query': query})
    return HttpResponse(html)

def get_real_chart_data(symbol):
    """Get real chart data using yfinance"""
    try:
        import yfinance as yf
        # Determine if it's forex or stock
        forex_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
        is_forex = symbol in forex_symbols

        # Add proper suffix for yfinance
        if is_forex and not symbol.endswith('=X'):
            yf_symbol = symbol + '=X'
        else:
            yf_symbol = symbol

        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="30d", interval="1d")
        if not hist.empty:
            labels = [d.strftime("%Y-%m-%d") for d in hist.index]
            values = hist["Close"].astype(float).tolist()
            high = float(hist["High"].max())
            low = float(hist["Low"].min())

            # Get current price and change
            last = float(hist["Close"].iloc[-1])
            if len(hist) > 1:
                prev = float(hist["Close"].iloc[-2])
                change = round(((last - prev) / prev) * 100, 2) if prev else 0  # SỬA: thiếu dấu )
            else:
                change = 0

            # Estimate volume category
            avg_volume = hist["Volume"].mean() if "Volume" in hist.columns else 0
            if avg_volume > 1000000:
                volume = 'High'
            elif avg_volume > 100000:
                volume = 'Medium'
            else:
                volume = 'Low'

            return {
                'chart_data': {
                    'labels': labels,
                    'values': values,
                    'high': round(high, 4 if is_forex else 2),
                    'low': round(low, 4 if is_forex else 2),
                    'volume': volume
                },
                'details': {
                    'last': round(last, 4 if is_forex else 2),
                    'change': change,
                    'history': values[-5:],  # Last 5 days
                    'volume': volume
                }
            }
    except Exception as e:
        logger.warning("Real chart data error for %s: %s", symbol, e)
    return None

def chart_view(request, symbol):
    real_data = get_real_chart_data(symbol)
    if not real_data:
        return HttpResponse('<div class="alert alert-danger mt-3">Chart not available for this symbol.</div>')

    html = render_to_string('finance_dashboard/chart_fragment.html', {
        'symbol': symbol,
        'chart_data': real_data['chart_data'],
        'details': real_data['details']
    })
    return HttpResponse(html)

def get_symbol_choices(request):
    """AJAX endpoint để lấy symbol choices theo category - LẤY TỪ DATABASE"""
    category = request.GET.get('category', 'currency')
    
    if category == 'currency':
        # LẤY FOREX PAIRS TỪ DATABASE
        forex_pairs = ForexPair.objects.all().order_by('pair')
        if forex_pairs.exists():
            choices = [(pair.pair, pair.pair) for pair in forex_pairs]
        else:
            # Fallback nếu chưa có data
            choices = [
                ('EURUSD', 'EUR/USD'),
                ('GBPUSD', 'GBP/USD'), 
                ('USDJPY', 'USD/JPY'), 
                ('AUDUSD', 'AUD/USD'), 
                ('USDCAD', 'USD/CAD'), 
                ('USDCHF', 'USD/CHF'), 
                ('NZDUSD', 'NZD/USD'),
            ]
    elif category == 'stock':
        choices = [
            ('AAPL', 'Apple Inc.'),
            ('GOOGL', 'Alphabet Inc.'),
            ('MSFT', 'Microsoft Corp.'),
            ('TSLA', 'Tesla Inc.'),
            ('AMZN', 'Amazon.com Inc.'),
            ('NVDA', 'NVIDIA Corp.'),
            ('META', 'Meta Platforms Inc.'),
        ]
    else:  # other
        choices = [
            ('BTCUSD', 'Bitcoin/USD'),
            ('ETHUSD', 'Ethereum/USD'),
            ('GOLD', 'Gold'),
            ('SILVER', 'Silver'),
        ]

    return JsonResponse({'choices': choices})

@login_required
def edit_trade(request, trade_id):
    """Edit trade - chỉ cho user đã login"""
    trade = get_object_or_404(Trade, id=trade_id, portfolio__user=request.user)
    
    if request.method == "POST":
        try:
            # Cập nhật thông tin trade
            trade.symbol = request.POST.get('symbol')
            trade.side = request.POST.get('side')
            trade.entry = request.POST.get('entry')
            trade.exit = request.POST.get('exit')
            trade.stoploss = request.POST.get('stoploss') or None
            trade.qty = request.POST.get('qty')
            trade.trade_type = request.POST.get('trade_type', 'Live')
            trade.date = request.POST.get('date') or trade.date
            
            # Xử lý portfolio nếu có thay đổi
            portfolio_id = request.POST.get('portfolio')
            if portfolio_id:
                portfolio = get_object_or_404(Portfolio, id=portfolio_id, user=request.user)
                trade.portfolio = portfolio
            
            trade.save()
            
            messages.success(request, "Trade updated successfully!")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
                
        except Exception as e:
            logger.error(f"Error updating trade: {e}")
            messages.error(request, f"Error updating trade: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
    
    # Nếu là GET request, redirect về portfolio
    return redirect('portfolio')

@login_required
def delete_trade(request, trade_id):
    """Xóa trade - chỉ cho user đã login"""
    trade = get_object_or_404(Trade, id=trade_id, portfolio__user=request.user)
    
    if request.method == "POST":
        trade.delete()
        messages.success(request, "Trade deleted successfully!")
    
    return redirect('portfolio')

@login_required
def create_insight_from_trade(request):
    """Tạo insight từ trade và liên kết với trade đó - HỖ TRỢ FILE UPLOAD"""
    if request.method == 'POST':
        trade_id = request.POST.get('trade_id')
        try:
            trade = Trade.objects.get(id=trade_id, portfolio__user=request.user)
            
            # Tạo insight mới
            insight = Insight(
                title=request.POST.get('title'),
                summary=request.POST.get('summary'),
                category=request.POST.get('category'),
                result=request.POST.get('result'),
                reason=request.POST.get('reason'),
                analysis=request.POST.get('analysis'),
                lessons=request.POST.get('lessons'),
                portfolio_ref=trade.portfolio
            )
            
            # Xử lý file upload
            if 'attached_image' in request.FILES:
                insight.attached_image = request.FILES['attached_image']
            elif 'attached_file' in request.FILES:
                insight.attached_file = request.FILES['attached_file']
            
            # Tự động điền metrics từ trade nếu được chọn
            if request.POST.get('auto_fill_metrics'):
                metrics = {
                    'symbol': trade.symbol,
                    'side': trade.side,
                    'entry': float(trade.entry),
                    'exit': float(trade.exit),
                    'stoploss': float(trade.stoploss) if trade.stoploss else None,
                    'quantity': float(trade.qty),
                    'pnl': float(trade.pnl) if trade.pnl else 0,
                    'trade_type': trade.trade_type,
                    'date': trade.date.strftime("%Y-%m-%d")
                }
                insight.metrics = metrics
            
            insight.save()
            
            # Liên kết insight với trade
            trade.ref_insight = insight
            trade.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 
                    'insight_id': insight.id,
                    'has_attachment': insight.has_attachment,
                    'file_name': insight.file_name
                })
            
            messages.success(request, "Insight created successfully and linked to trade!")
            return redirect('portfolio')
            
        except Trade.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': ['Trade not found']})
            messages.error(request, "Trade not found.")
            return redirect('portfolio')
    
    return JsonResponse({'success': False, 'errors': ['Invalid request']})

def link_trade_to_insight(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        trade_id = request.POST.get('trade_id')
        insight_id = request.POST.get('insight_id')
        
        try:
            trade = Trade.objects.get(id=trade_id)
            insight = Insight.objects.get(id=insight_id)
            
            trade.ref_insight = insight
            trade.save()
            
            return JsonResponse({'success': True})
            
        except (Trade.DoesNotExist, Insight.DoesNotExist):
            return JsonResponse({'success': False, 'errors': ['Trade or Insight not found']})
    
    return JsonResponse({'success': False, 'errors': ['Invalid request']})

def portfolio_view(request):
    if request.user.is_authenticated:
        # Logic cho user đã đăng nhập
        portfolios = Portfolio.objects.filter(user=request.user)
        # ... các xử lý khác
    else:
        # Logic cho khách - có thể hiển thị portfolio mẫu hoặc public
        portfolios = Portfolio.objects.filter(is_public=True)
        # Hoặc portfolios = Portfolio.objects.none() nếu không có public data
    
    context = {
        'portfolios': portfolios,
        # ... other context
    }
    return render(request, 'portfolio.html', context)