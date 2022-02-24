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
    path('add-tcr/process-new-tcr/', AddTcr.as_view(), name = 'process-new-tcr'),
    path('add-daily-activity/add-manual/', add_act_journ_man, name = 'add-act-journ-manual'),
    path('add-daily-activity/process-new-act-manual/', AddActMan.as_view(), name = 'process-new-act-man'),
    path('audit-summary/', AuditSummary.as_view(), name = 'audit-summary'),
    path('audit-summary/audit-details/<int:pk>/', AuditDetails.as_view(), name = 'audit-details'),
]