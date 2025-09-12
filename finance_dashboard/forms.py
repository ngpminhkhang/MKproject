from django import forms
from .models import Portfolio, Trade, Insight
from finance_dashboard.models import ForexPair

# ===================== Phase 2 =====================
FOREX_CHOICES = [
    ("EURUSD=X", "EUR/USD"),
    ("GBPUSD=X", "GBP/USD"),
    ("USDJPY=X", "USD/JPY"),
    ("AUDUSD=X", "AUD/USD"),
    ("USDCAD=X", "USD/CAD"),
    ("USDCHF=X", "USD/CHF"),
    ("NZDUSD=X", "NZD/USD"),
]

INTERVAL_CHOICES = [
    ("1d", "1 Day"),
    ("1h", "1 Hour"),
    ("30m", "30 Minutes"),
    ("15m", "15 Minutes"),
    ("1wk", "1 Week"),
    ("1mo", "1 Month"),
]

class WatchlistFilterForm(forms.Form):
    pairs = forms.MultipleChoiceField(
        choices=FOREX_CHOICES,
        initial=["EURUSD=X", "GBPUSD=X", "USDJPY=X"],
        widget=forms.CheckboxSelectMultiple,
        label="Chọn cặp Forex"
    )
    interval = forms.ChoiceField(
        choices=INTERVAL_CHOICES,
        initial="1d",
        label="Khung thời gian"
    )
    rsi = forms.BooleanField(required=False, initial=True, label="RSI")
    macd = forms.BooleanField(required=False, initial=True, label="MACD")
    ma50 = forms.BooleanField(required=False, initial=True, label="MA(50)")
    ma200 = forms.BooleanField(required=False, initial=False, label="MA(200)")
    bb = forms.BooleanField(required=False, initial=False, label="Bollinger Bands")

class TechnicalForm(forms.Form):
    symbol = forms.CharField(max_length=10, initial="EURUSD=X")
    indicators = forms.MultipleChoiceField(
        choices=[('sma','SMA'),('ema','EMA'),('rsi','RSI'),('macd','MACD')],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

class MacroForm(forms.Form):
    macro_type = forms.ChoiceField(
        choices=[('cot','COT Data'),('yield','Bond Yield'),('inflation','Inflation')],
        initial='cot'
    )

# ===================== Phase 3 =====================
SIDE_CHOICES = [("BUY", "BUY"), ("SELL", "SELL")]
TRADE_TYPE_CHOICES = [("Live", "Live"), ("Backtest", "Backtest")]

class TradeForm(forms.ModelForm):
    class Meta:
        model = Trade
        fields = ['portfolio', 'forex_pair', 'side', 'entry', 'exit', 'stoploss', 'qty', 'date', 'trade_type', 'notes', 'ref']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['portfolio'].queryset = Portfolio.objects.filter(user=user)

class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ["forex_pair", "amount"]

class InsightForm(forms.ModelForm):
    class Meta:
        model = Insight
        fields = [
            'title', 'summary', 'category', 'result', 
            'reason', 'analysis', 'lessons', 'metrics', 'portfolio_ref'
        ]
        widgets = {
            'portfolio_ref': forms.HiddenInput(),
            'metrics': forms.Textarea(attrs={'rows': 2}),
            'summary': forms.Textarea(attrs={'rows': 2}),
            'reason': forms.Textarea(attrs={'rows': 3}),
            'analysis': forms.Textarea(attrs={'rows': 3}),
            'lessons': forms.Textarea(attrs={'rows': 2}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].required = False  # Làm optional để match modal subset

class InsightSearchForm(forms.Form):
    q = forms.CharField(label='Search', required=False)
    result = forms.ChoiceField(
        choices=[('', 'All results')] + Insight.RESULT_CHOICES, required=False
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

# ===================== Phase 4: Ref/Insight cho Trade =====================
class TradeInsightForm(forms.Form):
    """Form để gắn hoặc tạo Insight cho Trade"""
    insight = forms.ModelChoiceField(
        queryset=Insight.objects.all(),
        required=False,
        label="Chọn Insight có sẵn"
    )
    new_title = forms.CharField(
        max_length=200,
        required=False,
        label="Hoặc tạo Insight mới (nhập tiêu đề)"
    )

    def clean(self):
        cleaned_data = super().clean()
        insight = cleaned_data.get("insight")
        new_title = cleaned_data.get("new_title")
        if not insight and not new_title:
            raise forms.ValidationError("Bạn phải chọn Insight hoặc nhập tiêu đề mới.")
        return cleaned_data

class TradeFilterForm(forms.Form):
    """Form để lọc trades theo loại"""
    trade_type = forms.ChoiceField(
        choices=[('', 'All')] + TRADE_TYPE_CHOICES,
        required=False,
        label="Filter"
    )
class GlobalSearchForm(forms.Form):
    q = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'placeholder': 'Search stock...',
            'class': 'form-control',
            'hx-get': '/finance_dashboard/search/',
            'hx-target': '#search-results',
            'hx-trigger': 'keyup changed delay:500ms, submit',
            'hx-swap': 'innerHTML'
        })
    )