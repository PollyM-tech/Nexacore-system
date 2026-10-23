from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import PlanViewSet, BatchViewSet, VoucherViewSet, SessionViewSet, Summary, PublicPurchase, PurchaseStatus, SaleViewSet, PurchaseViewSet

router = DefaultRouter()
router.register('plans', PlanViewSet)
router.register('batches', BatchViewSet)
router.register('vouchers', VoucherViewSet)
router.register('sessions', SessionViewSet)
router.register('sales', SaleViewSet)
router.register('purchases', PurchaseViewSet)
urlpatterns = [path('', include(router.urls)), path('summary/', Summary.as_view()),
               path('public/<uuid:public_id>/', PublicPurchase.as_view()), path('purchase-status/', PurchaseStatus.as_view())]
