from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class for consistent API response formatting.
    Supports page_size override via query parameter.
    """
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100
