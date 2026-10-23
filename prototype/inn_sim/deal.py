"""Roll every random outcome of a run up front, so all players face the same run."""
import random

from inn_sim.model import FINAL_EVENTS, KINDS, DayDeal, DealtTraveler, FinalEvent, RunDeal, Weather


def _weather(rng: random.Random, params: dict[str, float]) -> Weather:
    u = rng.random()
    if u < params["p_snow"]:
        return "snow"
    if u < params["p_snow"] + params["p_cold"]:
        return "cold"
    return "normal"


def _price(rng: random.Random, base: float, jitter: float, factor: float = 1.0) -> int:
    return max(1, round(base * rng.uniform(1 - jitter, 1 + jitter) * factor))


def _noble_tier(rng: random.Random, params: dict[str, float]) -> int:
    u = rng.random()
    if u < params["p_noble_high"]:
        return 2
    if u < params["p_noble_mid"]:
        return 1
    return 0


def _news(rng: random.Random, day: int, days: list[dict], final_event: FinalEvent) -> str:
    topic = rng.choice(["weather", "cheap", "final"])
    if topic == "weather" and day < len(days):
        return f"weather:{day + 1}={days[day]['weather']}"
    if topic == "cheap":
        later = [d["day"] for d in days if d["day"] > day and d["cheap_day"]]
        return f"cheap:{later[0] if later else 'none'}"
    return f"final:{final_event}"


def deal_run(params: dict[str, float], seed: int) -> RunDeal:
    rng = random.Random(seed)
    jitter = params["price_jitter"]
    # Day facts first, so news can tell the truth about later days.
    days: list[dict] = []
    for day in range(1, int(params["days"]) + 1):
        weather = _weather(rng, params)
        cheap = rng.random() < params["p_cheap_day"]
        days.append({
            "day": day,
            "weather": weather,
            "price_food": _price(rng, params["price_food"], jitter),
            "price_firewood": _price(rng, params["price_firewood"], jitter,
                                     params["cheap_discount"] if cheap else 1.0),
            "cheap_day": cheap,
            "base_arrivals": rng.randint(int(params["travelers_min"]), int(params["travelers_max"])),
        })
    final_event: FinalEvent = rng.choice(FINAL_EVENTS)

    weights = [params[f"w_{k}"] for k in KINDS]
    slots = int(params["travelers_max"]) + 1
    dealt_days = []
    for d in days:
        travelers = []
        for _ in range(slots):
            kind = rng.choices(KINDS, weights)[0]
            is_thief = kind == "merchant" and rng.random() < params["thief_p"]
            hint_p = params["hint_accuracy"] if is_thief else params["hint_false_pos"]
            hint = kind == "merchant" and rng.random() < hint_p
            tier = _noble_tier(rng, params) if kind == "noble" else 0
            news = _news(rng, d["day"], days, final_event) if kind == "wanderer" else None
            travelers.append(DealtTraveler(kind, is_thief, hint, tier, news))
        dealt_days.append(DayDeal(travelers=tuple(travelers), **d))
    return RunDeal(seed, tuple(dealt_days), final_event)
