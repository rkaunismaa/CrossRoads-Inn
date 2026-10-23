"""The game rules. The only place they live: hand play, careful and random players all run through here."""
import math
from dataclasses import dataclass
from typing import Protocol

from inn_sim.model import (Action, DayDeal, DayView, DealtTraveler, FinalEvent, InnState, Kind, RunDeal,
                           TravelerView, Weather)

# What each kind needs: (room, meal)
NEEDS: dict[Kind, tuple[bool, bool]] = {
    "merchant": (True, True),
    "pilgrim": (False, True),
    "soldier": (True, False),
    "noble": (True, False),
    "wanderer": (False, True),
}


def describe_news(news: str) -> str:
    """Plain words for a news item, for ledgers and hand play."""
    topic, _, value = news.partition(":")
    if topic == "weather":
        when, _, weather = value.partition("=")
        return f"day {when} will be {weather}"
    if topic == "cheap":
        return "no cheap firewood days ahead" if value == "none" else f"firewood is cheap on day {value}"
    return f"the final night brings: {value.replace('_', ' ')}"


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
    if t.is_thief:
        state.thieves_tonight += 1
    if t.kind == "wanderer" and t.news:
        state.news.append(t.news)
        return f"accepted +{pay}, news: {describe_news(t.news)}"
    return f"accepted +{pay}"


def fire_need(occupied: int, weather: Weather, params: dict[str, float], blizzard: bool = False) -> int:
    mult = {"normal": 1.0, "cold": params["mult_cold"], "snow": params["mult_snow"]}[weather]
    if blizzard:
        mult *= params["blizzard_mult"]
    return math.ceil((params["fire_base"] + params["fire_per_room"] * occupied) * mult)


def night(state: InnState, day: DayDeal, params: dict[str, float], final_event: FinalEvent | None) -> str:
    """Burn firewood, let thieves steal, then apply the final-night event if there is one."""
    notes = []
    need = fire_need(state.occupied, day.weather, params, blizzard=final_event == "blizzard")
    if state.firewood >= need:
        state.firewood -= need
        notes.append(f"burned {need} firewood")
    else:
        deficit = need - state.firewood
        state.firewood = 0
        state.coins = max(0, state.coins - deficit * int(params["shortage_coin_per_unit"]))
        _add_goodwill(state, -int(params["shortage_goodwill"]), params)
        notes.append(f"short {deficit} firewood")
    for _ in range(state.thieves_tonight):
        stolen = math.floor(state.coins * params["thief_steal_frac"])
        state.coins -= stolen
        notes.append(f"thief stole {stolen}")
    if final_event == "hungry_soldiers":
        want = int(params["hungry_soldiers_food"])
        short = max(0, want - state.food)
        state.food = max(0, state.food - want)
        state.coins = max(0, state.coins - short * int(params["final_food_penalty"]))
        notes.append(f"hungry soldiers, {short} food short")
    elif final_event == "robbery":
        if state.goodwill >= params["robbery_safe_goodwill"]:
            notes.append("robbery stopped by goodwill")
        else:
            taken = math.floor(state.coins * params["robbery_frac"])
            state.coins -= taken
            notes.append(f"robbery took {taken}")
    elif final_event == "blizzard":
        notes.append("blizzard")
    state.occupied = 0
    state.thieves_tonight = 0
    return ", ".join(notes)


class Player(Protocol):
    def market(self, state: InnState, day: DayView, params: dict[str, float]) -> tuple[int, int]: ...

    def decide(self, state: InnState, day: DayView, slot: int, view: TravelerView,
               params: dict[str, float]) -> Action: ...


@dataclass(frozen=True)
class RunResult:
    won: bool
    end_coins: int  # coins held before paying the debt (or when the run was lost)
    lost_on_day: int | None
    ledger: tuple[str, ...]


@dataclass
class Progress:
    """A run played up to some day: used by daily hand play to stop between days."""
    state: InnState
    ledger: list[str]
    lost_on_day: int | None
    arrivals: dict[int, int]  # day -> travelers who really arrived


def play_days(params: dict[str, float], deal: RunDeal, player: Player, through_day: int) -> Progress:
    state = new_state(params)
    progress = Progress(state, [], None, {})
    ledger = progress.ledger
    last_day = int(params["days"])
    for day in deal.days[:through_day]:
        pay_upkeep(state, params)
        if state.lost:
            ledger.append(f"Day {day.day}: could not pay upkeep, run lost")
            progress.lost_on_day = day.day
            return progress
        count = arrivals(state, day, params)
        progress.arrivals[day.day] = count
        state.walkout_yesterday = False
        view = DayView(day.day, day.weather, day.price_food, day.price_firewood, count)
        food, wood = player.market(state, view, params)
        buy(state, day, food, wood)
        ledger.append(f"Day {day.day}: {day.weather}, {count} travelers, "
                      f"coins {state.coins} food {state.food} firewood {state.firewood}")
        for slot, t in enumerate(day.travelers[:count], start=1):
            tv = traveler_view(state, t, params)
            action = player.decide(state, view, slot, tv, params)
            ledger.append(f"Day {day.day} slot {slot}: {tv.kind_shown} -> {action}: {serve(state, t, action, params)}")
        final = deal.final_event if day.day == last_day else None
        outcome = night(state, day, params, final)
        ledger.append(f"Day {day.day} night: {outcome}; now coins {state.coins} food {state.food} "
                      f"firewood {state.firewood}")
    return progress


def play_run(params: dict[str, float], deal: RunDeal, player: Player) -> RunResult:
    progress = play_days(params, deal, player, int(params["days"]))
    state, ledger = progress.state, progress.ledger
    if progress.lost_on_day is not None:
        return RunResult(False, state.coins, progress.lost_on_day, tuple(ledger))
    won = state.coins >= params["debt"]
    ledger.append(f"End: {state.coins} coins vs debt {int(params['debt'])}: {'WIN' if won else 'LOSS'}")
    return RunResult(won, state.coins, None, tuple(ledger))
