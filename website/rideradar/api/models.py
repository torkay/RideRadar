from django.db import models

# Create your models here.
class Vehicle(models.Model):
    title = models.CharField(max_length=50)
    price = models.IntegerField(null=False, default=0)
    link = models.CharField(max_length=200)
    img = models.CharField(max_length=200)
    vendor = models.CharField(max_length=20)
    added_at = models.DateTimeField(auto_now_add=True)