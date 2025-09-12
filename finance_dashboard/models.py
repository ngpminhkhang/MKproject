from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


# ===================== Phase 2 =====================
class ForexPair(models.Model):
    pair = models.CharField(max_length=10, unique=True)  # Ví dụ: EURUSD
    current_rate = models.DecimalField(max_digits=12, decimal_places=5, null=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pair

    class Meta:
        ordering = ["pair"]
        verbose_name_plural = "Forex Pairs"


class MacroData(models.Model):
    indicator = models.CharField(max_length=50)  # Ví dụ: GDP, Inflation
    value = models.DecimalField(max_digits=10, decimal_places=2)
    country = models.CharField(max_length=50)
    date = models.DateField()

    def __str__(self):
        return f"{self.indicator} - {self.country} - {self.date}"

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Macro Data"


# ===================== Phase 3 =====================
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
    portfolio_ref = models.ForeignKey("Portfolio", on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.TextField(blank=True, default="")  # đổi sang TextField cho linh hoạt

    # Các trường thêm
    content = models.TextField(blank=True, null=True)
    author = models.CharField(max_length=100, blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Insights"


class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)  # tên Portfolio
    forex_pair = models.ForeignKey("ForexPair", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    date_added = models.DateTimeField(auto_now_add=True)

    # Giữ lại entry_price + ref_insight (có ích cho backtest/ghi chú)
    entry_price = models.DecimalField(max_digits=10, decimal_places=5, blank=True, null=True)
    ref_insight = models.ForeignKey(
        Insight, on_delete=models.SET_NULL, null=True, blank=True, related_name="portfolios"
    )

    def __str__(self):
        return f"{self.name} ({self.forex_pair.pair})"

    @property
    def max_drawdown(self):
        """Tính Max Drawdown dựa trên equity curve từ trades"""
        trades = self.trades.order_by("date")
        if not trades.exists():
            return 0

        equity = Decimal(self.amount)
        peak = equity
        max_dd = Decimal("0")

        for t in trades:
            equity += Decimal(str(t.pnl))
            peak = max(peak, equity)
            dd = (peak - equity) / peak  # ddrawdown dương
            max_dd = max(max_dd, dd)

        return round(max_dd * 100, 2)  # Trả về %

    class Meta:
        ordering = ["-date_added"]
        verbose_name_plural = "Portfolios"


class Trade(models.Model):
    SIDE_CHOICES = [("BUY", "BUY"), ("SELL", "SELL")]
    TYPE_CHOICES = [("Live", "Live"), ("Backtest", "Backtest")]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="trades")
    forex_pair = models.ForeignKey("ForexPair", on_delete=models.CASCADE)
    side = models.CharField(max_length=10, choices=SIDE_CHOICES)
    entry = models.DecimalField(max_digits=12, decimal_places=5)  # entry price duy nhất
    exit = models.DecimalField(max_digits=12, decimal_places=5)
    stoploss = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    qty = models.IntegerField(default=10000)
    date = models.DateField()
    trade_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    notes = models.TextField(blank=True)
    ref = models.CharField(max_length=50, blank=True)

    @property
    def pnl(self):
        """PNL theo entry → exit"""
        direction = Decimal("1") if self.side == "BUY" else Decimal("-1")
        return round(direction * (self.exit - self.entry) * Decimal(self.qty), 2)

    @property
    def risk(self):
        """Số tiền rủi ro nếu dính stoploss"""
        if not self.stoploss:
            return None
        direction = Decimal("1") if self.side == "BUY" else Decimal("-1")
        return round(direction * (self.stoploss - self.entry) * Decimal(self.qty), 2)

    def __str__(self):
        return f"{self.portfolio.name} - {self.forex_pair.pair} - {self.side}"

    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Trades"
