from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from common.audit import log_action
from common.viewsets import BaseModelViewSet
from workspace.delivery import deliver_communication
from workspace.models import (
    Approval,
    ApprovalStatus,
    ApprovalType,
    Communication,
    Document,
    Task,
    TaskStatus,
)
from workspace.serializers import (
    ApprovalSerializer,
    CommunicationSerializer,
    DocumentSerializer,
    TaskSerializer,
)


class DocumentViewSet(BaseModelViewSet):
    module = 'documents'
    audit_entity = 'Document'
    queryset = Document.objects.select_related('uploaded_by').all()
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['entity_type', 'entity_id', 'category', 'is_current']
    search_fields = ['name', 'entity_type', 'category']
    ordering_fields = ['created_at', 'name', 'version']
    ordering = ['-created_at']


class CommunicationViewSet(BaseModelViewSet):
    module = 'communications'
    audit_entity = 'Communication'
    queryset = Communication.objects.select_related('client', 'sent_by').all()
    serializer_class = CommunicationSerializer
    filterset_fields = [
        'client',
        'channel',
        'status',
        'related_entity_type',
        'related_entity_id',
    ]
    search_fields = ['subject', 'message', 'client__name']
    ordering_fields = ['created_at', 'sent_at', 'channel']
    ordering = ['-created_at']
    extra_permissions = {'send': 'communications:edit'}

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        communication = self.get_object()
        if communication.status == 'SENT':
            return Response(
                {'statusCode': 400, 'message': 'Communication has already been sent'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.data.get('message'):
            communication.message = request.data['message']
        if request.data.get('subject'):
            communication.subject = request.data['subject']
        delivered, error = deliver_communication(communication)
        if not delivered:
            communication.status = 'FAILED'
            communication.save(update_fields=['status', 'updated_at'])
            return Response(
                {'statusCode': 400, 'message': error},
                status=status.HTTP_400_BAD_REQUEST,
            )
        communication.status = 'SENT'
        communication.sent_at = timezone.now()
        communication.sent_by = request.user
        communication.save(
            update_fields=['status', 'sent_at', 'sent_by', 'subject', 'message', 'updated_at']
        )
        log_action(
            request,
            'UPDATE',
            'communications',
            'Communication',
            communication.id,
            f'Communication sent by {communication.channel}',
        )
        return Response(
            {
                'data': CommunicationSerializer(
                    communication, context={'request': request}
                ).data
            }
        )


class TaskViewSet(BaseModelViewSet):
    module = 'tasks'
    audit_entity = 'Task'
    queryset = Task.objects.select_related('assigned_to', 'created_by').all()
    serializer_class = TaskSerializer
    filterset_fields = ['assigned_to', 'status', 'priority', 'related_entity_type']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'status', 'created_at']
    ordering = ['due_date', '-priority']
    extra_permissions = {'complete': 'tasks:edit'}

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        if task.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
            return Response(
                {'statusCode': 400, 'message': f'Task is already {task.status.lower()}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = TaskStatus.DONE
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at', 'updated_at'])
        log_action(
            request, 'UPDATE', 'tasks', 'Task', task.id, 'Task completed'
        )
        return Response(
            {'data': TaskSerializer(task, context={'request': request}).data}
        )


class ApprovalViewSet(BaseModelViewSet):
    module = 'approvals'
    audit_entity = 'Approval'
    queryset = Approval.objects.select_related('requested_by', 'approver').all()
    serializer_class = ApprovalSerializer
    filterset_fields = ['status', 'type', 'entity_type', 'requested_by', 'approver']
    search_fields = ['comments', 'entity_type', 'entity_id']
    ordering_fields = ['requested_at', 'status', 'amount']
    ordering = ['-requested_at']
    extra_permissions = {'decide': 'approvals:approve'}

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        approval = self.get_object()
        decision = (request.data.get('status') or '').upper()
        if decision not in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
            return Response(
                {
                    'statusCode': 400,
                    'message': 'Decision must be APPROVED or REJECTED',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if approval.requested_by_id == request.user.id:
            return Response(
                {
                    'statusCode': 403,
                    'message': 'You cannot decide on your own approval request',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if approval.status != ApprovalStatus.PENDING:
            return Response(
                {
                    'statusCode': 400,
                    'message': 'This approval has already been decided',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        approval.status = decision
        approval.approver = request.user
        approval.decided_at = timezone.now()
        approval.comments = request.data.get('comments') or approval.comments
        approval.save(
            update_fields=[
                'status',
                'approver',
                'decided_at',
                'comments',
                'updated_at',
            ]
        )
        self._sync_entity(approval, decision)
        log_action(
            request,
            'APPROVE' if decision == ApprovalStatus.APPROVED else 'REJECT',
            'approvals',
            'Approval',
            approval.id,
            f'{approval.type} {decision.lower()}',
        )
        return Response(
            {
                'data': ApprovalSerializer(
                    approval, context={'request': request}
                ).data
            }
        )

    @action(detail=True, methods=['get'])
    def review(self, request, pk=None):
        approval = self.get_object()
        entity = None
        entity_available = False
        serializer_class = self._entity_serializer(approval.entity_type)
        if serializer_class:
            model = serializer_class.Meta.model
            try:
                instance = model.objects.get(pk=approval.entity_id)
            except (model.DoesNotExist, ValueError, TypeError):
                instance = None
            if instance is not None:
                entity = serializer_class(
                    instance, context={'request': request}
                ).data
                entity_available = True
        return Response(
            {
                'data': {
                    'approval': ApprovalSerializer(
                        approval, context={'request': request}
                    ).data,
                    'entity': entity,
                    'entity_available': entity_available,
                }
            }
        )

    def _entity_serializer(self, entity_type):
        from claims.models import Claim
        from claims.serializers import ClaimSerializer
        from crm.models import Client
        from crm.serializers import ClientSerializer
        from finance.models import (
            Commission,
            CreditDebitNote,
            Invoice,
            Payment,
            Remittance,
        )
        from finance.serializers import (
            CommissionSerializer,
            CreditDebitNoteSerializer,
            InvoiceSerializer,
            PaymentSerializer,
            RemittanceSerializer,
        )
        from operations.models import Endorsement, Policy, Quotation
        from operations.serializers import (
            EndorsementSerializer,
            PolicySerializer,
            QuotationSerializer,
        )

        mapping = {
            Client: ClientSerializer,
            Quotation: QuotationSerializer,
            Policy: PolicySerializer,
            Endorsement: EndorsementSerializer,
            Claim: ClaimSerializer,
            Commission: CommissionSerializer,
            Payment: PaymentSerializer,
            Invoice: InvoiceSerializer,
            CreditDebitNote: CreditDebitNoteSerializer,
            Remittance: RemittanceSerializer,
        }
        normalised = (entity_type or '').replace('_', '').replace(' ', '').lower()
        for model, serializer in mapping.items():
            if model.__name__.lower() == normalised:
                return serializer
        return None

    def _sync_entity(self, approval, decision):
        from claims.models import Claim, ClaimStatus
        from django.utils import timezone as tz
        from operations.models import Endorsement, EndorsementStatus

        if approval.type == ApprovalType.ENDORSEMENT:
            try:
                endorsement = Endorsement.objects.get(pk=approval.entity_id)
            except Endorsement.DoesNotExist:
                return
            endorsement.status = (
                EndorsementStatus.APPROVED
                if decision == ApprovalStatus.APPROVED
                else EndorsementStatus.REJECTED
            )
            endorsement.approved_by = approval.approver
            endorsement.approved_at = approval.decided_at or tz.now()
            endorsement.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        elif approval.type == ApprovalType.CLAIM_SETTLEMENT:
            Claim.objects.filter(pk=approval.entity_id).update(
                status=(
                    ClaimStatus.APPROVED
                    if decision == ApprovalStatus.APPROVED
                    else ClaimStatus.REJECTED
                )
            )
# 2026-11-11T15:06:09Z overdue fix
# 2026-11-11T15:06:09Z delete restriction
