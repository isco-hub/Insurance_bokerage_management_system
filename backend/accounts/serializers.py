from rest_framework import serializers

from accounts.models import AuditLog, Branch, Permission, Role, User


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            'id',
            'code',
            'name',
            'physical_address',
            'phone',
            'email',
            'is_active',
            'created_at',
            'updated_at',
        ]

    def validate_code(self, value):
        qs = Branch.objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A branch with this code already exists.')
        return value.upper()


class PermissionSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'module', 'action', 'code', 'description']


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(), many=True, required=False
    )
    permission_codes = serializers.SerializerMethodField()
    user_count = serializers.IntegerField(source='users.count', read_only=True)

    class Meta:
        model = Role
        fields = [
            'id',
            'code',
            'name',
            'description',
            'is_system',
            'permissions',
            'permission_codes',
            'user_count',
            'created_at',
            'updated_at',
        ]

    def get_permission_codes(self, obj):
        return sorted(
            f'{rp.permission.module}:{rp.permission.action}'
            for rp in obj.role_permissions.select_related('permission')
        )


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    role_name = serializers.CharField(source='role.name', read_only=True)
    role_code = serializers.CharField(source='role.code', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    full_name = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'employee_no',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'phone',
            'role',
            'role_name',
            'role_code',
            'branch',
            'branch_name',
            'is_active',
            'mfa_enabled',
            'failed_login_attempts',
            'locked_until',
            'is_locked',
            'must_change_password',
            'last_login_at',
            'permissions',
            'password',
            'date_joined',
            'updated_at',
        ]
        read_only_fields = ['last_login_at', 'date_joined', 'updated_at']

    def get_permissions(self, obj):
        return sorted(obj.permission_codes)

    def get_is_locked(self, obj):
        from django.utils import timezone

        return bool(obj.locked_until and obj.locked_until > timezone.now())

    def validate_email(self, value):
        if value:
            qs = User.objects.filter(email=value.lower())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('A user with this email already exists.')
        return value.lower() if value else value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': 'Password is required'})
        validated_data['email'] = validated_data['email'].lower()
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if 'email' in validated_data:
            validated_data['email'] = validated_data['email'].lower()
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user',
            'user_name',
            'user_email',
            'action',
            'module',
            'entity_type',
            'entity_id',
            'description',
            'metadata',
            'ip_address',
            'user_agent',
            'created_at',
        ]
# 2026-11-11T15:05:22Z branch serializer
# 2026-11-11T15:05:23Z unique email
# 2026-11-11T15:06:07Z branch serializer
