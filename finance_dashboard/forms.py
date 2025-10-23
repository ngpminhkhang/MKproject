from django import forms
from .models import Portfolio, Trade, Insight
from finance_dashboard.models import ForexPair

# ===================== Phase 2 ================================

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
        label="Chon c3p Forex"
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
    symbol = forms.CharField(max_length=10, initial="EURUSD=x")
    indicators = forms.MultipleChoiceField(
        choices=[('sma','SMA'),('ema','EMA'),('rsi','RSI'),('macd','MACD')],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

class MacroForm(forms.Form):
    macro_type = forms.ChoiceField(
        choices=[('cot','COT Data'),('yield','Bond Yield'),('inflation','inflation')],
        initial='cot'
    )

# --- Phase 3 ---

SIDE_CHOICES = [("BUY", "BUY"), ("SELL", "SELL")]

TRADE_TYPE_CHOICES = [("Live", "Live"), ("Backtest", "Backtest")]

class TradeForm(forms.ModelForm):
    # Thêm field category để chọn loại tài sản
    category = forms.ChoiceField(
        choices=[
            ('currency', 'Currency'),
            ('stock', 'Stock'),
            ('other', 'Other')
        ],
        widget=forms.Select(attrs={'class': 'form-control form-control-sm', 'id': 'id_category'})
    )
    
    # Thêm field symbol với choices động
    symbol = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-control form-control-sm', 'id': 'id_symbol'})
    )

    class Meta:
        model = Trade
        # LOAI BỔ 'ref' khỏi fields
        fields = ['portfolio', 'symbol', 'side', 'entry', 'exit', 'stoploss', 'qty', 'date', 'trade_type', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control form-control-sm'}),
            'portfolio': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'side': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'entry': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.00001'}),
            'exit': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.00001'}),
            'stoploss': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.00001'}),
            'qty': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'trade_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            # LOAI BÖ widget cho 'ref'
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['portfolio'].queryset = Portfolio.objects.filter(user=user)
        
        # Set initial choices for symbol based on category - LÄY TÜ DATABASE
        self.fields['symbol'].choices = self.get_symbol_choices('currency')

    def get_symbol_choices(self, category):
        """Get symbol choices based on category - LÄY TÜ DATABASE"""
        if category == 'currency':
            # LÄY FOREX PAIRS TÜ DATABASE THAY VÌ HARD-CODED
            forex_pairs = ForexPair.objects.all().order_by('pair')
            if forex_pairs.exists():
                return [[pair.pair, pair.pair] for pair in forex_pairs]
            else:
                # Fallback nếu chưa có data
                return [
                    ('EURUSD', 'EUR/USD'),
                    ('GBPUSD', 'GBP/USD'),
                    ('USDJPY', 'USD/JPY'),
                    ('AUDUSD', 'AUD/USD'),
                    ('USDCAD', 'USD/CAD'),
                    ('USDCHF', 'USD/CHF'),
                    ('NZDUSD', 'NZD/USD'),
                ]
        elif category == 'stock':
            return [
                ('AAPL', 'Apple Inc.'),
                ('GOOGL', 'Alphabet Inc.'),
                ('MSFT', 'Microsoft Corp.'),
                ('TSLA', 'Tesla Inc.'),
                ('AMZN', 'Amazon.com Inc.'),
                ('NVDA', 'NVIDIA Corp.'),
                ('META', 'Meta Platforms Inc.'),
            ]
        else: # other
            return [
                ('BTCUSD', 'Bitcoin/USD'),
                ('ETHUSD', 'Ethereum/USD'),
                ('GOLD', 'Gold'),
                ('SILVER', 'Silver'),
            ]

class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ["name", "category", "symbol", "amount"]

class InsightForm(forms.ModelForm):
    class Meta:
        model = Insight
        fields = [
            'title', 'summary', 'category', 'result',
            'reason', 'analysis', 'lessons', 'metrics',
            'attached_file', 'attached_image'  # THÊM FIELD FILE
        ]
        widgets = {
            'metrics': forms.Textarea(attrs={'rows': 2}),
            'summary': forms.Textarea(attrs={'rows': 2}),
            'reason': forms.Textarea(attrs={'rows': 3}),
            'analysis': forms.Textarea(attrs={'rows': 3}),
            'lessons': forms.Textarea(attrs={'rows': 2}),
            # THÊM WIDGET CHO FILE UPLOAD
            'attached_file': forms.FileInput(attrs={'class': 'form-control'}),
            'attached_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].required = False

    # THÊM CLEAN METHOD ĐỂ VALIDATE FILE
    def clean(self):
        cleaned_data = super().clean()
        attached_file = cleaned_data.get('attached_file')
        attached_image = cleaned_data.get('attached_image')
        
        # Kiểm tra nếu upload cả file và image
        if attached_file and attached_image:
            raise forms.ValidationError("Chỉ có thể upload một file hoặc một ảnh, không upload cả hai.")
        
        # Kiểm tra kích thước file (ví dụ: max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        if attached_file and attached_file.size > max_size:
            raise forms.ValidationError("File quá lớn. Kích thước tối đa là 5MB.")
        if attached_image and attached_image.size > max_size:
            raise forms.ValidationError("Ảnh quá lớn. Kích thước tối đa là 5MB.")
        
        return cleaned_data

class InsightSearchForm(forms.Form):
    q = forms.CharField(label='Search', required=False)
    result = forms.ChoiceField(
        choices=[("", 'All results')] + Insight.RESULT_CHOICES,
        required=False
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

# --- Phase 4: Ref/Insight cho Trade ---

class TradeInsightForm(forms.Form):
    """Form dē gān hoặc tạo Insight cho Trade"""
    insight = forms.ModelChoiceField(
        queryset=Insight.objects.all(),
        required=False,
        label="Chpn Insight có sẵn"
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
    """Form dē loc trades theo loa!"""
    trade_type = forms.ChoiceField(
        choices=[("", 'All')] + TRADE_TYPE_CHOICES,
        required=False,
        label="Filter"  
    )

class GlobalSearchForm(forms.Form):
    q = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'placeholder': 'Search stock...',
            'class': 'form-control',
            'hx-get': '/finance_dashboard/search/',
            'hx-target': '#search-results',
            'hx-trigger': 'keyup changed delay:500ms, submit',
            'hx-swap': 'innerHTML'
        })
    )