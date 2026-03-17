from rest_framework.pagination import LimitOffsetPagination


class DefaultLimitOffsetPagination(LimitOffsetPagination):
    # Keep responses small by default; frontend can request a larger `limit` up to max_limit.
    default_limit = 50
    max_limit = 200

