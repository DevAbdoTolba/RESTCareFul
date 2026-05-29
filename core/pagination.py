"""
Shared pagination — owned by `core`, imported by any slice that lists data.

The appointment-history UI wants "10 rows per month, then load 5 more on
click", so page size is client-controllable (`?page_size=`) within a sane cap
instead of the project-wide default of 20. Centralising it here means every
list endpoint paginates the same way and the frontend learns one contract.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """`?page=` + `?page_size=` (default 10, hard cap 50)."""

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
