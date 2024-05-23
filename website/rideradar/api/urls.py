from django.urls import path
from .views import VehicleView

urlpatterns = [
    path("Home", VehicleView.as_view()),
]
