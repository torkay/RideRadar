from django.shortcuts import render
from rest_framework import generics
from .serializers import VehicleSerializer
from .models import Vehicle

# Create your views here.
class VehicleView(generics.CreateAPIView):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer