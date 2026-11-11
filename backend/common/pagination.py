import math

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class EnvelopePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 200

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request) or self.page_size
        total = self.page.paginator.count
        return Response(
            {
                'data': data,
                'meta': {
                    'page': self.page.number,
                    'pageSize': page_size,
                    'total': total,
                    'totalPages': math.ceil(total / page_size) if page_size else 0,
                },
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'data': schema,
                'meta': {
                    'type': 'object',
                    'properties': {
                        'page': {'type': 'integer'},
                        'pageSize': {'type': 'integer'},
                        'total': {'type': 'integer'},
                        'totalPages': {'type': 'integer'},
                    },
                },
            },
        }
# 2026-11-11T15:06:10Z pagination
