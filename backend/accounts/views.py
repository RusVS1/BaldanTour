from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from tours.models import Favorite
from .forms import RegisterForm

# Create your views here.


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("tour_search")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related("tour")
        .order_by("-created_at")
    )
    return render(request, "accounts/profile.html", {"favorites": favorites})
