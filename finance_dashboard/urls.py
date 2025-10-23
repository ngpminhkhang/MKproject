from django.urls import path, include  # THÊM include
from . import views
from django.contrib.auth.views import LoginView


urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(template_name='finance_dashboard/login.html'), name='login'),
    
    # Main pages
    path('', views.home, name='home'),
    path("analysis/", views.analysis, name="analysis"),
    path("analysis/ajax/", views.analysis_ajax, name="analysis_ajax"),
    path("portfolio/", views.portfolio, name="portfolio"),
    path("about/", views.about, name="about"),
    path('search/', views.search_view, name='search'),
    path('chart/<str:symbol>/', views.chart_view, name='chart'),  # SỬA: st: → str:
    path("details/<str:symbol>/", views.details, name="details"),
    
    # Insights CRUD
    path("insights/", views.insights, name="insights"),
    path("insight/create/", views.create_insight, name="create_insight"),
    path("insight/create/<int:portfolio_id>/", views.create_insight_for_portfolio, name="create_insight_for_portfolio"),
    path("insight/edit/<int:insight_id>/", views.edit_insight, name="edit_insight"),
    path("insight/delete/<int:insight_id>/", views.delete_insight, name="delete_insight"),  # SỬA: insights.delete → insight/delete
    path("insight/search/", views.search_insights, name="search_insights"),
    path("insight/modal/<int:pk>/", views.insight_modal, name="insight_modal"),
    path("insight/<int:pk>/", views.insight_modal, name="insight_model"),  # THÊM DÒNG NÀY
    
    # Trade insight creation
    path("trade/create-insight/", views.create_insight_from_trade, name="create_insight_from_trade"),
    
    # Portfolio-specific insight creation
    path("portfolio/<int:portfolio_id>/create-insight/", views.create_insight_for_portfolio, name="create_insight_for_portfolio"),
    
    # Trade insight modal
    path("trade/<int:trade_id>/insight/", views.trade_insight_modal, name="trade_insight_modal"),
    
    # Trade CRUD
    path("trade/<int:trade_id>/edit/", views.edit_trade, name="edit_trade"),
    path("trade/<int:trade_id>/delete/", views.delete_trade, name="delete_trade"),
    
    # Trade filtering - SỬA: st: → str:
    path("trades/filter/<str:trade_type>/", views.filter_trades, name="filter_trades"),
    
    # AJAX endpoints
    path("get-symbol-choices/", views.get_symbol_choices, name="get_symbol_choices"),
]