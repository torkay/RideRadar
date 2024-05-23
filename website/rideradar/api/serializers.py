from rest_framework import serializers
from .models import Vehicle

class VehicleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Vehicle
        fields = ("title", "price", "link", "img", "vendor", "added_at")