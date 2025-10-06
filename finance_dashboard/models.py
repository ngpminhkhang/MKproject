from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

# --- Phase 2 ---
class ForexPair(models.Model):
    pair = models.CharField(max_length=10, unique=True) # Vi du: EURUSD
    current_rate = models.DecimalField(max_digits=12, decimal_places=5, null=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pair

    class Meta:
        ordering = ["pair"]
        verbose_name_plural = "Forex Pairs"
    
    # THÊM METHOD ĐỂ HIỂN THỊ TÊN ĐẸP HƠN (tùy chọn)
    @property
    def display_name(self):
        """Hiển thị tên đẹp hơn, ví dụ: EURUSD -> EUR/USD"""
        if len(self.pair) == 6:
            return f"{self.pair[:3]}/{self.pair[3:]}"
        return self.pair

class MacroData(models.Model):
    indicator = models.CharField(max_length=50) # Vi du: GDP, Inflation
    value = models.DecimalField(max_digits=10, decimal_places=2)
    country = models.CharField(max_length=50)
    date = models.DateField()

    def __str__(self):
        return f"{self.indicator} - {self.country} - {self.date}"
    
    class Meta:
        ordering = ["date"]  
        verbose_name_plural = "Macro Data"  

# --- Phase 3 ---  
class Insight(models.Model):
    CATEGORY_CHOICES = [
        ("currency", "Currency"),
        ("stock", "Stock"),
        ("summary", "Summary"),
        ("other", "Other"),
    ]

    RESULT_CHOICES = [
        ("positive", "Positive"),
        ("negative", "Negative"),
        ("neutral", "Neutral"),
    ]

    title = models.CharField(max_length=200)
    summary = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="other")
    date = models.DateTimeField(auto_now_add=True)
    result = models.CharField(max_length=10, choices=RESULT_CHOICES, default="neutral")
    reason = models.TextField(blank=True)
    analysis = models.TextField(blank=True)
    lessons = models.TextField(blank=True)
    metrics = models.JSONField(blank=True, null=True)
    portfolio_ref = models.ForeignKey("Portfolio", on_delete=models.SET_NULL, null=True, blank=True, related_name="insights")
    tags = models.TextField(blank=True, default="")
    content = models.TextField(blank=True, null=True)
    author = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # THÊM FIELD MỚI CHO FILE UPLOAD
    attached_file = models.FileField(upload_to='insight_attachments/%Y/%m/%d/', blank=True, null=True)
    attached_image = models.ImageField(upload_to='insight_images/%Y/%m/%d/', blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Insights"

    # THÊM PROPERTY ĐỂ KIỂM TRA LOẠI FILE
    @property
    def has_attachment(self):
        return bool(self.attached_file or self.attached_image)
    
    @property
    def is_image(self):
        if self.attached_image:
            return True
        if self.attached_file:
            return self.attached_file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
        return False

    @property
    def file_name(self):
        if self.attached_file:
            return self.attached_file.name.split('/')[-1]
        if self.attached_image:
            return self.attached_image.name.split('/')[-1]
        return None

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-date"]  
        verbose_name_plural = "Insights"

class Portfolio(models.Model):
    CATEGORY_CHOICES = [
        ("currency", "Currency"),
        ("stock", "Stock"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="currency")
    symbol = models.CharField(max_length=20, blank=True, null=True) # EURUSD, AAPL, BTCUSD...
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    date_added = models.DateTimeField(auto_now_add=True)
    
    # THÊM FIELD is_public VÀO PORTFOLIO
    is_public = models.BooleanField(default=False)  # Thêm dòng này
    
    # THÊM FIELD ref_insight VÀO PORTFOLIO
    ref_insight = models.ForeignKey(Insight, on_delete=models.SET_NULL, null=True, blank=True, related_name="portfolio_references")

    def __str__(self):
        return f"{self.name} {self.symbol or ''}"

    @property
    def max_drawdown(self):
        """Tinh Max Drawdown dựa trên equity curve từ trades"""
        from decimal import Decimal
        trades = self.trades.order_by("date")
        if not trades.exists():
            return 0

        equity = Decimal(self.amount)
        peak = equity
        max_dd = Decimal("0")

        for t in trades:
            equity += Decimal(str(t.pnl))
            peak = max(peak, equity)
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)

        return round(max_dd * 100, 2)

    class Meta:
        ordering = ["date_added"]
        verbose_name_plural = "Portfolios"

class Trade(models.Model):
    SIDE_CHOICES = [("BUY", "BUY"), ("SELL", "SELL")]
    TYPE_CHOICES = [("Live", "Live"), ("Backtest", "Backtest")]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="trades")
    symbol = models.CharField(max_length=20, blank=True, null=True) # <- dői túr ForeignKey sang CharField
    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    entry = models.DecimalField(max_digits=12, decimal_places=5) # entry price duy nhất
    exit = models.DecimalField(max_digits=12, decimal_places=5)
    stoploss = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    qty = models.IntegerField(default=10000)
    date = models.DateField()
    trade_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    notes = models.TextField(blank=True)
    ref = models.CharField(max_length=50, blank=True)
    
    # THÊM FIELD ref_insight VÀO TRADE
    ref_insight = models.ForeignKey(Insight, on_delete=models.SET_NULL, null=True, blank=True, related_name="trade_references")

    @property
    def pnl(self):
        """PNL theo entry → exit"""
        direction = Decimal("1") if self.side == "BUY" else Decimal("-1")
        return round(direction * (self.exit - self.entry) * Decimal(self.qty), 2)

    @property
    def risk(self):
        """Ső tiền rủi ro nếu dính stoploss"""
        if not self.stoploss:
            return None
        direction = Decimal("1") if self.side == "BUY" else Decimal("-1")
        return round(direction * (self.stoploss - self.entry) * Decimal(self.qty), 2)

    def __str__(self):
        return f"{self.portfolio.name} - {self.symbol} - {self.side}"
    
    class Meta:
        ordering = ["date"]
        verbose_name_plural = "Trades"