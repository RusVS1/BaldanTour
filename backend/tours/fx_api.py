import json
from datetime import datetime
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.utils.timezone import is_naive, make_aware
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


CBR_DAILY_JSON = "https://www.cbr-xml-daily.ru/daily_json.js"


class FxRatesSerializer(serializers.Serializer):
    source = serializers.CharField()
    fetched_at = serializers.DateTimeField()
    usd_to_rub = serializers.FloatField()
    eur_to_rub = serializers.FloatField()
    rub_to_usd = serializers.FloatField()
    rub_to_eur = serializers.FloatField()


def _parse_cbr_datetime(value: str) -> datetime:
    # Example: "2026-03-19T11:30:00+03:00"
    dt = datetime.fromisoformat(value)
    if is_naive(dt):
        dt = make_aware(dt)
    return dt


class RubFxRatesAPI(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = FxRatesSerializer

    def get(self, request):
        cached = cache.get("fx:rub:usd_eur")
        if cached:
            return Response(cached)

        try:
            req = Request(
                CBR_DAILY_JSON,
                headers={"User-Agent": "tour-aggregator/1.0"},
                method="GET",
            )
            with urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))

            usd_to_rub = float(payload["Valute"]["USD"]["Value"])
            eur_to_rub = float(payload["Valute"]["EUR"]["Value"])
            fetched_at = _parse_cbr_datetime(payload.get("Date") or payload.get("Timestamp"))

            data = {
                "source": "cbr-xml-daily",
                "fetched_at": fetched_at.isoformat(),
                "usd_to_rub": usd_to_rub,
                "eur_to_rub": eur_to_rub,
                "rub_to_usd": 1.0 / usd_to_rub if usd_to_rub else 0.0,
                "rub_to_eur": 1.0 / eur_to_rub if eur_to_rub else 0.0,
            }
            cache.set("fx:rub:usd_eur", data, timeout=60)
            return Response(data)
        except Exception as e:  # noqa: BLE001
            return Response(
                {"error": "fx_unavailable", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

