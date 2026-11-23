from django.contrib.auth.models import User
from rest_framework import serializers


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "is_staff", "date_joined")
        read_only_fields = fields
