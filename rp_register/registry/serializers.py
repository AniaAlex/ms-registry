from rest_framework import serializers

from .models import RegisteredEntity


class RegisteredEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RegisteredEntity
        fields = "__all__"
