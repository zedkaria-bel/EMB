from django.urls import path
from django.conf.urls import url
from .views import (
    home_view,
    prodSummary,
    prodDetails,
    EditProd,
    saleSummary,
    saleDetails,
    EditSale,
    trsSummary,
    trsDetails,
    EditTrs,
    tcrSummary,
    add_act_journ,
    AddAct,
    add_tcr,
    AddTcr,
    add_act_journ_man,
    AddActMan,
    AuditSummary,
    AuditDetails,
    add_tcr_man,
    AddTcrMan,
    ObjCapacitySummary,
    AddObjectifCap,
    TcrMan,
    set_capacity,
    add_cap_prod_imp,
    FlashImpressionSummary,
    FlashImpressionDetails,
    EditFlashImp,
    add_cap_prod_imp_man,
)

app_name = 'core'

urlpatterns = [
    path('', home_view, name = 'home-view'),
    path('summary/prod/', prodSummary.as_view(), name='prod-view'),
    path('summary/prod/details/<int:pk>/', prodDetails.as_view(), name = 'prod-details'),
    path('edit-prod/', EditProd.as_view(), name = 'edit-prod'),
    path('summary/sale/', saleSummary.as_view(), name='sale-view'),
    path('summary/sale/details/<int:pk>/', saleDetails.as_view(), name = 'sale-details'),
    path('edit-sale/', EditSale.as_view(), name = 'edit-sale'),
    path('summary/trs/', trsSummary.as_view(), name='trs-view'),
    path('summary/trs/details/<int:pk>/', trsDetails.as_view(), name = 'trs-details'),
    path('edit-trs/', EditTrs.as_view(), name = 'edit-trs'),
    path('summary/tcr/', tcrSummary.as_view(), name = 'tcr-view'),
    path('add-daily-activity/', add_act_journ, name = 'add-act-journ'),
    path('add-daily-activity/process-new-act/', AddAct.as_view(), name = 'process-new-act'),
    path('add-tcr/', add_tcr, name = 'add-tcr'),
    path('add-tcr/manual/', add_tcr_man, name = 'add-tcr-man'),
    path('edit-tcr/<int:year>/<int:month>/', TcrMan.as_view(), name = 'edit-tcr-man'),
    path('add-tcr/process-new-tcr/', AddTcr.as_view(), name = 'process-new-tcr'),
    path('add-daily-activity/add-manual/', add_act_journ_man, name = 'add-act-journ-manual'),
    path('add-daily-activity/process-new-act-manual/', AddActMan.as_view(), name = 'process-new-act-man'),
    path('audit-summary/', AuditSummary.as_view(), name = 'audit-summary'),
    path('audit-summary/audit-details/<int:pk>/', AuditDetails.as_view(), name = 'audit-details'),
    path('add-tcr/process-tcr-manual/', AddTcrMan.as_view(), name = 'process-new-tcr-man'),
    path('goals-summary/<str:mode>/', ObjCapacitySummary.as_view(), name = 'goals-summary'),
    path('process-goals/', AddObjectifCap.as_view(), name = 'process-goals'),
    path('set-capacity/', set_capacity, name = 'set-capacity'),
    path('add-cap-prod-imp/', add_cap_prod_imp, name = 'add-cap-prod-imp'),
    path('flash-impr-summary/', FlashImpressionSummary.as_view(), name = 'flash-impr-summary'),
    path('flash-impr-details/<int:pk>/', FlashImpressionDetails.as_view(), name = 'flash-impr-details'),
    path('edit-flash-imp/', EditFlashImp.as_view(), name = 'edit-flash-imp'),
    path('add-flash-imp-manual/', add_cap_prod_imp_man, name = 'add-flash-imp-manual'),
]