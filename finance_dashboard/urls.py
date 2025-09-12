from django.urls import path
from . import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(template_name='finance_dashboard/login.html'), name='login'),

    # Main pages
    path("", views.home, name="home"),
    path("analysis/", views.analysis, name="analysis"),
    path("analysis/ajax/", views.analysis_ajax, name="analysis_ajax"),
    path("portfolio/", views.portfolio, name="portfolio"),
    path("about/", views.about, name="about"),
    path('search/', views.search_view, name='search'),
    path('chart/<str:symbol>/', views.chart_view, name='chart'),

    # Details (truyền cặp tiền tệ, ví dụ EURUSD=X)
    path("details/", views.details, name="details"),
    path("details/<str:pair>/", views.details, name="details"),

    # Insights CRUD
    path("insights/", views.insights, name="insights"),
    path("insights/create/", views.create_insight, name="create_insight"),  
    path("insights/create/<int:portfolio_id>/", views.create_insight, name="create_insight_for_portfolio_simple"),  
    path("insights/edit/<int:insight_id>/", views.edit_insight, name="edit_insight"),
    path("insights/delete/<int:insight_id>/", views.delete_insight, name="delete_insight"),
    path("insights/search/", views.search_insights, name="search_insights"),
    path("insights/modal/<int:pk>/", views.insight_modal, name="insight_modal"),
    
    # Portfolio-specific insight creation
    path("portfolio/<int:portfolio_id>/create-insight/", views.create_insight_for_portfolio, name="create_insight_for_portfolio"),
    
    # Trade insight modal
    path("trade/<int:trade_id>/insight/", views.trade_insight_modal, name="trade_insight_modal"),
    
    # Trade filtering
    path("trades/filter/<str:trade_type>/", views.filter_trades, name="filter_trades"),
]
