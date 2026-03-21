from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef
from django.shortcuts import redirect, render

from .filters import TourFilter
from .models import Favorite, Tour


def tour_search(request):
    qs = Tour.objects.all().prefetch_related("amenities")

    if request.user.is_authenticated:
        favorite_subq = Favorite.objects.filter(user=request.user, tour=OuterRef("pk"))
        qs = qs.annotate(is_favorite=Exists(favorite_subq))

    tour_filter = TourFilter(request.GET, queryset=qs)
    filtered = tour_filter.qs.order_by("price_value", "id")

    paginator = Paginator(filtered, 30)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "tours/search.html",
        {"filter": tour_filter, "page": page},
    )


@login_required
def favorite_add(request, tour_id: int):
    Favorite.objects.get_or_create(user=request.user, tour_id=tour_id)
    return redirect(request.META.get("HTTP_REFERER") or "tour_search")


@login_required
def favorite_remove(request, tour_id: int):
    Favorite.objects.filter(user=request.user, tour_id=tour_id).delete()
    return redirect(request.META.get("HTTP_REFERER") or "tour_search")
