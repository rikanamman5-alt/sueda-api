import re
import math

LOCATION_COORDS = {
    # === TAWI-TAWI ===
    "bongao":                 {"lat": 5.0295, "lng": 119.7731},
    "bongao town":            {"lat": 5.0295, "lng": 119.7731},
    "sanga-sanga":            {"lat": 5.0737, "lng": 119.7853},
    "sanga sanga":            {"lat": 5.0737, "lng": 119.7853},
    "simunul":                {"lat": 4.9333, "lng": 119.8500},
    "panganlima":             {"lat": 4.9833, "lng": 119.9000},
    "languyan":               {"lat": 5.2667, "lng": 120.0833},
    "tandubas":               {"lat": 5.1333, "lng": 120.3500},
    "sapa-sapa":              {"lat": 5.0833, "lng": 120.0167},
    "sapa sapa":              {"lat": 5.0833, "lng": 120.0167},
    "sibutu":                 {"lat": 4.8500, "lng": 119.4667},
    "south ubian":            {"lat": 4.9000, "lng": 119.5500},
    "ubian":                  {"lat": 4.9000, "lng": 119.5500},
    "turtle islands":         {"lat": 6.0833, "lng": 118.3167},
    "mapun":                  {"lat": 6.9833, "lng": 118.5333},
    "cagayan de tawi-tawi":   {"lat": 6.9833, "lng": 118.5333},
    "balimbing":              {"lat": 5.0667, "lng": 119.9333},
    "paniongan":              {"lat": 5.0167, "lng": 119.9333},
    "taganak":                {"lat": 5.0833, "lng": 119.8500},

    # === METRO MANILA ===
    "manila":                 {"lat": 14.5995, "lng": 120.9842},
    "makati":                 {"lat": 14.5547, "lng": 121.0244},
    "quezon city":            {"lat": 14.6760, "lng": 121.0437},
    "taguig":                 {"lat": 14.5176, "lng": 121.0509},
    "pasig":                  {"lat": 14.5764, "lng": 121.0851},
    "pasay":                  {"lat": 14.5378, "lng": 120.9945},
    "mandaluyong":            {"lat": 14.5798, "lng": 121.0429},
    "san juan":               {"lat": 14.6018, "lng": 121.0358},
    "marikina":               {"lat": 14.6500, "lng": 121.1000},
    "paranaque":              {"lat": 14.4798, "lng": 120.9948},
    "las pinas":              {"lat": 14.4438, "lng": 120.9951},
    "muntinlupa":             {"lat": 14.4081, "lng": 121.0417},
    "caloocan":               {"lat": 14.6498, "lng": 120.9833},
    "malabon":                {"lat": 14.6650, "lng": 120.9589},
    "navotas":                {"lat": 14.6667, "lng": 120.9500},
    "valenzuela":             {"lat": 14.7000, "lng": 120.9833},

    # === LUZON ===
    "dagupan":                {"lat": 16.0438, "lng": 120.3365},
    "baguio":                 {"lat": 16.4023, "lng": 120.5960},
    "la union":               {"lat": 16.6100, "lng": 120.3200},
    "vigan":                  {"lat": 17.5703, "lng": 120.3898},
    "tuguegarao":             {"lat": 17.6149, "lng": 121.7240},
    "ilagan":                 {"lat": 17.1489, "lng": 121.8887},
    "santiago":               {"lat": 16.6887, "lng": 121.5489},
    "cabanatuan":             {"lat": 15.4890, "lng": 120.9678},
    "tarlac":                 {"lat": 15.4802, "lng": 120.5963},
    "pampanga":               {"lat": 15.1235, "lng": 120.6997},
    "angeles":                {"lat": 15.1458, "lng": 120.5886},
    "clark":                  {"lat": 15.1858, "lng": 120.5595},
    "bulacan":                {"lat": 14.8381, "lng": 120.8664},
    "malolos":                {"lat": 14.8447, "lng": 120.8116},
    "bataan":                 {"lat": 14.6833, "lng": 120.4500},
    "olongapo":               {"lat": 14.8248, "lng": 120.2826},
    "batangas":               {"lat": 13.7565, "lng": 121.0583},
    "lipa":                   {"lat": 13.9411, "lng": 121.1623},
    "lucena":                 {"lat": 13.9333, "lng": 121.6167},
    "cavite":                 {"lat": 14.2955, "lng": 120.8821},
    "dasmarinas":             {"lat": 14.3258, "lng": 120.9363},
    "imus":                   {"lat": 14.3942, "lng": 120.9399},
    "bacoor":                 {"lat": 14.4496, "lng": 120.9439},
    "laguna":                 {"lat": 14.2786, "lng": 121.4401},
    "san pablo":              {"lat": 14.0686, "lng": 121.3259},
    "sta rosa":               {"lat": 14.3137, "lng": 121.1115},
    "calamba":                {"lat": 14.1951, "lng": 121.1407},
    "biñan":                  {"lat": 14.3084, "lng": 121.0856},
    "rizal":                  {"lat": 14.5743, "lng": 121.1520},
    "antipolo":               {"lat": 14.5863, "lng": 121.1750},
    "naga":                   {"lat": 13.6191, "lng": 123.1815},
    "legazpi":                {"lat": 13.1391, "lng": 123.7438},
    "daet":                   {"lat": 14.1146, "lng": 122.9559},
    "virac":                  {"lat": 13.5780, "lng": 124.2304},
    "puerto princesa":        {"lat": 9.7396, "lng": 118.7353},
    "calapan":                {"lat": 13.3800, "lng": 121.1867},
    "baler":                  {"lat": 15.7584, "lng": 121.5603},

    # === VISAYAS ===
    "cebu":                   {"lat": 10.3157, "lng": 123.8854},
    "cebu city":              {"lat": 10.3157, "lng": 123.8854},
    "mandaue":                {"lat": 10.3309, "lng": 123.9371},
    "lapu-lapu":              {"lat": 10.3105, "lng": 123.9547},
    "lapu lapu":              {"lat": 10.3105, "lng": 123.9547},
    "talisay":                {"lat": 10.2460, "lng": 123.8302},
    "danao":                  {"lat": 10.5235, "lng": 123.7581},
    "toledo":                 {"lat": 10.3772, "lng": 123.6404},
    "bogo":                   {"lat": 10.0630, "lng": 124.0030},
    "iloilo":                 {"lat": 10.7202, "lng": 122.5621},
    "iloilo city":            {"lat": 10.7202, "lng": 122.5621},
    "bacolod":                {"lat": 10.6667, "lng": 122.9500},
    "silay":                  {"lat": 10.7973, "lng": 122.9774},
    "tacloban":               {"lat": 11.2433, "lng": 125.0047},
    "ormoc":                  {"lat": 11.0066, "lng": 124.6075},
    "roxas":                  {"lat": 11.5875, "lng": 122.7509},
    "kalibo":                 {"lat": 11.7067, "lng": 122.3637},
    "boracay":                {"lat": 11.9674, "lng": 121.9248},
    "dumaguete":              {"lat": 9.3069, "lng": 123.3060},
    "tagbilaran":             {"lat": 9.6550, "lng": 123.8530},
    "catbalogan":             {"lat": 11.7750, "lng": 124.8844},
    "maasin":                 {"lat": 10.1324, "lng": 124.8432},
    "siquijor":               {"lat": 9.2150, "lng": 123.5144},

    # === MINDANAO ===
    "davao":                  {"lat": 7.1907, "lng": 125.4553},
    "davao city":             {"lat": 7.1907, "lng": 125.4553},
    "davao del sur":          {"lat": 6.6500, "lng": 125.3500},
    "digos":                  {"lat": 6.7564, "lng": 125.3571},
    "tagum":                  {"lat": 7.4476, "lng": 125.8084},
    "panabo":                 {"lat": 7.3064, "lng": 125.6839},
    "mati":                   {"lat": 6.9497, "lng": 126.1972},
    "general santos":         {"lat": 6.1104, "lng": 125.1745},
    "gensan":                 {"lat": 6.1104, "lng": 125.1745},
    "koronadal":              {"lat": 6.5031, "lng": 124.8467},
    "tacurong":               {"lat": 6.6908, "lng": 124.6763},
    "kidapawan":              {"lat": 7.0093, "lng": 125.0895},
    "cotabato":               {"lat": 7.2167, "lng": 124.2500},
    "cotabato city":          {"lat": 7.2167, "lng": 124.2500},
    "zamboanga":              {"lat": 6.9083, "lng": 122.0750},
    "zamboanga city":         {"lat": 6.9083, "lng": 122.0750},
    "dipolog":                {"lat": 8.5880, "lng": 123.3409},
    "pagadian":               {"lat": 7.8277, "lng": 123.4370},
    "ozamiz":                 {"lat": 8.1466, "lng": 123.8457},
    "orocueta":               {"lat": 8.1840, "lng": 123.8420},
    "cagayan de oro":         {"lat": 8.4955, "lng": 124.6477},
    "cdo":                    {"lat": 8.4955, "lng": 124.6477},
    "iligan":                 {"lat": 8.2254, "lng": 124.2410},
    "malaybalay":             {"lat": 8.1500, "lng": 125.0833},
    "valencia":               {"lat": 7.9058, "lng": 125.0909},
    "butuan":                 {"lat": 8.9481, "lng": 125.5437},
    "surigao":                {"lat": 9.7833, "lng": 125.5000},
    "surigao del norte":      {"lat": 9.7833, "lng": 125.5000},
    "tandag":                 {"lat": 9.0771, "lng": 126.0829},
    "bislig":                 {"lat": 8.2100, "lng": 126.3158},
    "marawi":                 {"lat": 8.0000, "lng": 124.2833},
    "marawi city":            {"lat": 8.0000, "lng": 124.2833},

    # === SULU / BASILAN ===
    "jolo":                   {"lat": 6.0536, "lng": 121.0024},
    "patikul":                {"lat": 6.0840, "lng": 121.0980},
    "indanan":                {"lat": 5.9600, "lng": 121.0000},
    "siasi":                  {"lat": 5.5167, "lng": 120.8167},
    "isabela":                {"lat": 6.7028, "lng": 121.9724},
    "isabela city":           {"lat": 6.7028, "lng": 121.9724},
    "lamitan":                {"lat": 6.6500, "lng": 122.1333},
    "basilan":                {"lat": 6.6000, "lng": 122.0000},

    # === ARMM / BARMM ===
    "parang":                 {"lat": 7.3833, "lng": 124.2667},
    "jolo sulu":              {"lat": 6.0536, "lng": 121.0024},

    # === PALAWAN ===
    "el nido":                {"lat": 11.1943, "lng": 119.4050},
    "coron":                  {"lat": 11.9993, "lng": 120.2000},
    "brooke's point":         {"lat": 8.7833, "lng": 117.8333},
    "brookes point":          {"lat": 8.7833, "lng": 117.8333},
    "narra":                  {"lat": 9.2833, "lng": 118.4167},
    "roxas palawan":          {"lat": 10.3200, "lng": 119.3400},

    # === OTHER PROVINCIAL CAPITALS ===
    "lingayen":               {"lat": 16.0236, "lng": 120.2283},
    "balanga":                {"lat": 14.6761, "lng": 120.5361},
    "imus cavite":            {"lat": 14.3942, "lng": 120.9399},
    "boac":                   {"lat": 13.4464, "lng": 121.8394},
    "romblon":                {"lat": 12.5758, "lng": 122.2867},
    "jordan":                 {"lat": 10.6500, "lng": 122.6000},
}

LOCATION_FEES = {
    ("bongao", "sanga-sanga"): {"min": 50, "max": 90},
    ("bongao", "simunul"): {"min": 70, "max": 120},
    ("bongao", "panganlima"): {"min": 60, "max": 100},
    ("bongao", "languyan"): {"min": 80, "max": 150},
    ("bongao", "tandubas"): {"min": 80, "max": 140},
    ("bongao", "sapa-sapa"): {"min": 60, "max": 110},
    ("bongao", "sibutu"): {"min": 100, "max": 180},
    ("bongao", "south ubian"): {"min": 90, "max": 160},
    ("bongao", "turtle islands"): {"min": 120, "max": 200},
    ("bongao", "mapun"): {"min": 150, "max": 250},
    ("sanga-sanga", "simunul"): {"min": 40, "max": 70},
    ("sanga-sanga", "languyan"): {"min": 50, "max": 90},
    ("sanga-sanga", "tandubas"): {"min": 50, "max": 90},
    ("sanga-sanga", "sapa-sapa"): {"min": 40, "max": 70},
    ("simunul", "sapa-sapa"): {"min": 30, "max": 60},
    ("simunul", "languyan"): {"min": 40, "max": 80},
    ("languyan", "tandubas"): {"min": 30, "max": 60},
    ("languyan", "sapa-sapa"): {"min": 50, "max": 90},
}

DEFAULT_FEE_PER_KM = 15.0
BASE_FEE = 30.0


class DeliveryFeeService:

    @staticmethod
    def normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9\s]", "", text.strip().lower())

    @staticmethod
    def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlng / 2) ** 2
        )
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _round_down(n: float, to: float) -> float:
        return math.floor(n / to) * to

    @staticmethod
    def _round_up(n: float, to: float) -> float:
        return math.ceil(n / to) * to

    @staticmethod
    def _round_nearest(n: float, to: float) -> float:
        return round(n / to) * to

    @staticmethod
    def _lookup_coords(name: str) -> dict | None:
        normalized = DeliveryFeeService.normalize(name)
        if normalized in LOCATION_COORDS:
            return LOCATION_COORDS[normalized]
        for key, coords in LOCATION_COORDS.items():
            if normalized in key or key in normalized:
                return coords
        words = normalized.split()
        if len(words) > 1:
            for w in words:
                if len(w) > 2:
                    for key, coords in LOCATION_COORDS.items():
                        if w in key or key in w:
                            return coords
        return None

    @staticmethod
    def compute_ai_fee(
        origin: str = "",
        destination: str = "",
        distance_km: float | None = None,
        origin_lat: float | None = None,
        origin_lng: float | None = None,
        dest_lat: float | None = None,
        dest_lng: float | None = None,
    ) -> dict:
        computed_distance = False

        if distance_km is not None and distance_km > 0:
            pass
        elif all(v is not None for v in [origin_lat, origin_lng, dest_lat, dest_lng]):
            distance_km = DeliveryFeeService.haversine(
                origin_lat, origin_lng, dest_lat, dest_lng
            )
            computed_distance = True
        else:
            orig_coords = DeliveryFeeService._lookup_coords(origin)
            dest_coords = DeliveryFeeService._lookup_coords(destination)
            if orig_coords and dest_coords:
                distance_km = DeliveryFeeService.haversine(
                    orig_coords["lat"], orig_coords["lng"],
                    dest_coords["lat"], dest_coords["lng"],
                )
                computed_distance = True

        if distance_km is not None and distance_km > 0:
            fee = max(BASE_FEE + (distance_km * 10), 50.0)
            min_fee = max(DeliveryFeeService._round_down(fee - 10, 5), 30.0)
            max_fee = DeliveryFeeService._round_up(fee + 10, 5)
            suggested = max(DeliveryFeeService._round_nearest(fee, 5), 50.0)
            return {
                "origin": origin.strip(),
                "destination": destination.strip(),
                "distance_km": round(distance_km, 2),
                "fee_min": int(min_fee),
                "fee_max": int(max_fee),
                "suggested_fee": int(suggested),
                "source": f"ai_distance{'*' if computed_distance else ''}",
            }

        return DeliveryFeeService.suggest_fee(origin, destination)

    @staticmethod
    def suggest_fee(origin: str, destination: str) -> dict:
        orig = DeliveryFeeService.normalize(origin)
        dest = DeliveryFeeService.normalize(destination)

        direct = LOCATION_FEES.get((orig, dest))
        if direct:
            return {
                "origin": origin.strip(),
                "destination": destination.strip(),
                "fee_min": direct["min"],
                "fee_max": direct["max"],
                "suggested_fee": (direct["min"] + direct["max"]) // 2,
                "source": "location_matrix",
            }

        reverse = LOCATION_FEES.get((dest, orig))
        if reverse:
            return {
                "origin": origin.strip(),
                "destination": destination.strip(),
                "fee_min": reverse["min"],
                "fee_max": reverse["max"],
                "suggested_fee": (reverse["min"] + reverse["max"]) // 2,
                "source": "location_matrix_reverse",
            }

        for (a, b), fee in LOCATION_FEES.items():
            if orig in a or orig in b or dest in a or dest in b:
                if orig in a or orig in b:
                    other = b if orig in a else a
                    combined = f"{dest} {other}"
                else:
                    other = a if dest in b else b
                    combined = f"{orig} {other}"

                word_overlap = len(set(combined.split()) & set(dest.split() if orig in a else orig.split()))
                if word_overlap >= 1:
                    return {
                        "origin": origin.strip(),
                        "destination": destination.strip(),
                        "fee_min": fee["min"],
                        "fee_max": fee["max"],
                        "suggested_fee": (fee["min"] + fee["max"]) // 2,
                        "source": "partial_match",
                    }

        return {
            "origin": origin.strip(),
            "destination": destination.strip(),
            "fee_min": int(BASE_FEE),
            "fee_max": int(BASE_FEE + 120),
            "suggested_fee": int(BASE_FEE + 60),
            "source": "estimated",
        }

    @staticmethod
    def calculate_by_distance(distance_km: float) -> dict:
        fee = BASE_FEE + (distance_km * DEFAULT_FEE_PER_KM)
        return {
            "distance_km": round(distance_km, 2),
            "fee": round(fee, 2),
            "base_fee": BASE_FEE,
            "per_km_rate": DEFAULT_FEE_PER_KM,
        }
