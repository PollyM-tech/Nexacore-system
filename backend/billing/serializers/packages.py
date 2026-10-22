from rest_framework import serializers
from billing.models import Package


class PackageSerializer(serializers.ModelSerializer):
    customer_count = serializers.IntegerField(read_only=True, default=0)
    radius_customer_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Package
        fields = ['id', 'name', 'package_type', 'speed', 'price', 'description', 'is_active', 'created_at', 'updated_at', 'customer_count', 'radius_customer_count']
        read_only_fields = ['created_at', 'updated_at']
