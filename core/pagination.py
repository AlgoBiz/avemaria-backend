from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class for consistent API response formatting.
    Supports page_size override via query parameter.
    """
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request) or self.page_size,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

    def get_paginated_response_dict(self, data, extra=None):
        payload = {
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request) or self.page_size,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        }
        if extra:
            merged = dict(extra)
            merged.update(payload)
            return merged
        return payload


def paginate_response(items, request, serializer_class=None, context=None, page_size=15, extra=None):
    """
    Universal pagination helper function for both QuerySets and in-memory Python lists.
    Returns a DRF Response with consistent pagination metadata.
    """
    paginator = StandardResultsSetPagination()
    if page_size:
        paginator.page_size = page_size

    page = paginator.paginate_queryset(items, request)
    if page is not None:
        if serializer_class:
            serializer = serializer_class(page, many=True, context=context or {'request': request})
            serialized_data = serializer.data
        else:
            serialized_data = page
        return Response(paginator.get_paginated_response_dict(serialized_data, extra=extra))

    # Fallback if pagination is not active
    if serializer_class:
        serializer = serializer_class(items, many=True, context=context or {'request': request})
        serialized_data = serializer.data
    else:
        serialized_data = items

    res_dict = {
        'count': len(items) if hasattr(items, '__len__') else (items.count() if hasattr(items, 'count') else 0),
        'total_pages': 1,
        'current_page': 1,
        'page_size': page_size,
        'next': None,
        'previous': None,
        'results': serialized_data
    }
    if extra:
        merged = dict(extra)
        merged.update(res_dict)
        return Response(merged)
    return Response(res_dict)
