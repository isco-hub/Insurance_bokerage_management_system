import mimetypes
import os

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from workspace.models import (
    Approval,
    ApprovalStatus,
    Communication,
    Document,
    Task,
    TaskStatus,
)


class DocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(
        source='uploaded_by.full_name', read_only=True
    )
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id',
            'entity_type',
            'entity_id',
            'name',
            'category',
            'file',
            'file_url',
            'file_name',
            'mime_type',
            'size',
            'version',
            'is_current',
            'uploaded_by',
            'uploaded_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'mime_type',
            'size',
            'version',
            'is_current',
            'uploaded_by',
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if not obj.file:
            return None
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url

    def get_file_name(self, obj):
        return os.path.basename(obj.file.name) if obj.file else None

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        uploaded = validated_data.get('file')
        if not validated_data.get('name') and uploaded:
            validated_data['name'] = uploaded.name
        if uploaded:
            validated_data['size'] = uploaded.size
            validated_data['mime_type'] = (
                uploaded.content_type
                or mimetypes.guess_type(uploaded.name)[0]
                or ''
            )
        if user and user.is_authenticated:
            validated_data['uploaded_by'] = user
        with transaction.atomic():
            existing = Document.objects.filter(
                entity_type=validated_data.get('entity_type'),
                entity_id=validated_data.get('entity_id'),
                name=validated_data.get('name'),
            )
            version = (existing.order_by('-version').values_list('version', flat=True).first() or 0) + 1
            existing.update(is_current=False)
            validated_data['version'] = version
            validated_data['is_current'] = True
            return super().create(validated_data)


class CommunicationSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    sent_by_name = serializers.CharField(
        source='sent_by.full_name', read_only=True
    )

    class Meta:
        model = Communication
        fields = [
            'id',
            'client',
            'client_name',
            'channel',
            'subject',
            'message',
            'related_entity_type',
            'related_entity_id',
            'sent_at',
            'status',
            'sent_by',
            'sent_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['sent_by']

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            validated_data['sent_by'] = user
        if validated_data.get('status') == 'SENT' and not validated_data.get('sent_at'):
            validated_data['sent_at'] = timezone.now()
        return super().create(validated_data)


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(
        source='assigned_to.full_name', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.full_name', read_only=True
    )
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id',
            'title',
            'description',
            'assigned_to',
            'assigned_to_name',
            'related_entity_type',
            'related_entity_id',
            'due_date',
            'priority',
            'status',
            'created_by',
            'created_by_name',
            'completed_at',
            'is_overdue',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_by', 'completed_at']

    def get_is_overdue(self, obj):
        return bool(
            obj.due_date
            and obj.due_date < timezone.localdate()
            and obj.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
        )

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            validated_data['created_by'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        status = validated_data.get('status', instance.status)
        if status == TaskStatus.DONE and not instance.completed_at:
            validated_data['completed_at'] = timezone.now()
        if status != TaskStatus.DONE:
            validated_data['completed_at'] = None
        return super().update(instance, validated_data)


class ApprovalSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(
        source='requested_by.full_name', read_only=True
    )
    approver_name = serializers.CharField(
        source='approver.full_name', read_only=True
    )

    class Meta:
        model = Approval
        fields = [
            'id',
            'type',
            'entity_type',
            'entity_id',
            'amount',
            'requested_by',
            'requested_by_name',
            'approver',
            'approver_name',
            'status',
            'comments',
            'requested_at',
            'decided_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'requested_by',
            'approver',
            'status',
            'decided_at',
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            validated_data['requested_by'] = user
        validated_data['status'] = ApprovalStatus.PENDING
        return super().create(validated_data)
