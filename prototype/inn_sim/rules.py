"""The game rules. The only place they live: hand play, careful and random players all run through here."""
from inn_sim.model import Action, DayDeal, DealtTraveler, InnState, Kind, TravelerView

# What each kind needs: (room, meal)
NEEDS: dict[Kind, tuple[bool, bool]] = {
    "merchant": (True, True),
    "pilgrim": (False, True),
    "soldier": (True, False),
    "noble": (True, False),
    "wanderer": (False, True),
}


def new_state(params: dict[str, float]) -> InnState:
    return InnState(
        coins=int(params["start_coins"]),
        food=int(params["start_food"]),
        firewood=int(params["start_firewood"]),
        goodwill=int(params["start_goodwill"]),
    )


def _add_goodwill(state: InnState, amount: int, params: dict[str, float]) -> None:
    state.goodwill = max(0, min(int(params["goodwill_cap"]), state.goodwill + amount))


def _with_goodwill(pay: float, state: InnState, params: dict[str, float]) -> int:
    return round(pay * (1 + state.goodwill * params["goodwill_pay_bonus"]))


def pay_upkeep(state: InnState, params: dict[str, float]) -> None:
    upkeep = int(params["upkeep"])
    if state.coins < upkeep:
        state.lost = True
    else:
        state.coins -= upkeep


def buy(state: InnState, day: DayDeal, food: int, firewood: int) -> None:
    """Buy as much as coins allow, food first."""
    food_bought = min(max(0, food), state.coins // day.price_food)
    state.food += food_bought
    state.coins -= food_bought * day.price_food
    wood_bought = min(max(0, firewood), state.coins // day.price_firewood)
    state.firewood += wood_bought
    state.coins -= wood_bought * day.price_firewood


def arrivals(state: InnState, day: DayDeal, params: dict[str, float]) -> int:
    count = day.base_arrivals
    if state.goodwill >= params["goodwill_arrival_threshold"]:
        count += 1
    if state.walkout_yesterday:
        count -= 1
    return max(0, min(count, len(day.travelers)))


def traveler_view(state: InnState, t: DealtTraveler, params: dict[str, float]) -> TravelerView:
    room, meal = NEEDS[t.kind]
    if t.kind == "noble":
        offer = int(params["noble_offer"])
    elif t.kind == "wanderer":
        offer = 0
    else:
        offer = _with_goodwill(params[f"pay_{t.kind}"], state, params)
    return TravelerView(t.kind, t.hint, offer, room, meal)


def serve(state: InnState, t: DealtTraveler, action: Action, params: dict[str, float]) -> str:
    """Apply one decision. Anything that can't be done counts as a decline."""
    if action == "decline":
        return "declined"
    if action != "accept" and t.kind != "noble":
        return "declined (can't haggle)"
    room, meal = NEEDS[t.kind]
    meal_cost = int(params["food_per_meal"])
    if room and state.occupied >= int(params["rooms"]):
        return "declined (no room)"
    if meal and state.food < meal_cost:
        return "declined (no food)"

    if t.kind == "noble" and action != "accept":
        tier_needed = 1 if action == "haggle_mid" else 2
        if t.noble_tier < tier_needed:
            _add_goodwill(state, -int(params["walkout_goodwill_loss"]), params)
            state.walkout_yesterday = True
            return "noble walked out"
        pay = int(params["noble_mid"] if action == "haggle_mid" else params["noble_high"])
    else:
        pay = traveler_view(state, t, params).offer

    if room:
        state.occupied += 1
    if meal:
        state.food -= meal_cost
    state.coins += pay
    if t.kind == "pilgrim":
        _add_goodwill(state, int(params["pilgrim_goodwill"]), params)
    if t.kind == "wanderer" and t.news:
        state.news.append(t.news)
    if t.is_thief:
        state.thieves_tonight += 1
    return f"accepted +{pay}"
