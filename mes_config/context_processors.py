from django.conf import settings


def timezone(request):
    return {"TIME_ZONE": settings.TIME_ZONE}
