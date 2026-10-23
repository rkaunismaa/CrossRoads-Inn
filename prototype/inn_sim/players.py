"""Players: the rule-based careful player, the random baseline, and a scripted player for hand-play replay."""
import random

from inn_sim.model import Action, DayView, InnState, TravelerView
from inn_sim.rules import fire_need

Params = dict[str, float]


def _can_accept(state: InnState, view: TravelerView, params: Params) -> bool:
    if view.needs_room and state.occupied >= params["rooms"]:
        return False
    if view.needs_meal and state.food < params["food_per_meal"]:
        return False
    return True


def _known_final(state: InnState) -> str | None:
    for item in state.news:
        if item.startswith("final:"):
            return item.split(":", 1)[1]
    return None


def _cheap_today(state: InnState, day: DayView, params: Params) -> bool:
    # A cheap day shows in the price itself, or was announced by a wanderer.
    floor_price = params["price_firewood"] * (1 - params["price_jitter"])
    return day.price_firewood < floor_price or f"cheap:{day.day}" in state.news


class CarefulPlayer:
    """A simple, readable strategy a cautious human might follow."""

    def market(self, state: InnState, day: DayView, params: Params) -> tuple[int, int]:
        last_day = day.day == int(params["days"])
        final = _known_final(state)

        # 1. Firewood: enough for a full house tonight plus a small margin.
        full_house = fire_need(int(params["rooms"]), day.weather, params)
        wood_target = full_house + 2
        if _cheap_today(state, day, params):
            wood_target *= 2
        if last_day:
            blizzard_extra = full_house * (params["blizzard_mult"] - 1)
            if final == "blizzard":
                wood_target += blizzard_extra
            elif final is None:
                wood_target += blizzard_extra / 2

        # 2. Food: a meal for everyone arriving today, plus the hungry soldiers if they may come.
        food_target = day.arrivals * params["food_per_meal"]
        if last_day:
            if final == "hungry_soldiers":
                food_target += params["hungry_soldiers_food"]
            elif final is None:
                food_target += params["hungry_soldiers_food"] / 2

        # 3. Never spend into the coins needed for the remaining upkeep.
        days_left = int(params["days"]) - day.day
        budget = state.coins - (params["upkeep"] * days_left + 2)
        food = int(min(max(0, round(food_target) - state.food), max(0, budget) // day.price_food))
        budget -= food * day.price_food
        wood = int(min(max(0, round(wood_target) - state.firewood), max(0, budget) // day.price_firewood))
        return food, wood

    def decide(self, state: InnState, day: DayView, slot: int, view: TravelerView, params: Params) -> Action:
        # Never trust a merchant Bram is suspicious of.
        if view.kind_shown == "merchant" and view.hint:
            return "decline"
        # Only give a room if tonight's fire can still be paid for.
        if view.needs_room and state.firewood < fire_need(state.occupied + 1, day.weather, params):
            return "decline"
        # Feed a pilgrim only if the food still covers everyone yet to arrive.
        if view.kind_shown == "pilgrim":
            still_to_come = (day.arrivals - slot) * params["food_per_meal"]
            if state.food - params["food_per_meal"] < still_to_come:
                return "decline"
        # Haggle with the noble only while there is little goodwill to lose.
        if view.kind_shown == "noble":
            return "haggle_mid" if state.goodwill <= 2 else "accept"
        return "accept"


class RandomPlayer:
    """Baseline: uniform over legal choices."""

    def __init__(self, seed: int) -> None:
        self.rng = random.Random(seed)

    def market(self, state: InnState, day: DayView, params: Params) -> tuple[int, int]:
        food = self.rng.randint(0, state.coins // day.price_food)
        left = state.coins - food * day.price_food
        wood = self.rng.randint(0, left // day.price_firewood)
        return food, wood

    def decide(self, state: InnState, day: DayView, slot: int, view: TravelerView, params: Params) -> Action:
        choices: list[Action] = ["decline"]
        if _can_accept(state, view, params):
            choices.append("accept")
            if view.kind_shown == "noble":
                choices += ["haggle_mid", "haggle_high"]
        return self.rng.choice(choices)


class ScriptedPlayer:
    """Replays recorded choices: market keyed by day, decisions keyed by (day, slot)."""

    def __init__(self, market: dict[int, tuple[int, int]], decisions: dict[tuple[int, int], Action]) -> None:
        self.market_buys = market
        self.decisions = decisions
        self.defaulted: list[tuple[int, int]] = []  # arrived travelers with no recorded decision
        self.sheet_rows: dict[tuple[int, int], int] = {}  # (day, slot) -> HandPlay row, for warnings
        self.already_warned: set[tuple[int, int]] = set()  # bad cells already reported by read_decisions

    def market(self, state: InnState, day: DayView, params: Params) -> tuple[int, int]:
        return self.market_buys.get(day.day, (0, 0))

    def decide(self, state: InnState, day: DayView, slot: int, view: TravelerView, params: Params) -> Action:
        if (day.day, slot) not in self.decisions:
            self.defaulted.append((day.day, slot))
            return "decline"
        return self.decisions[(day.day, slot)]


class RecordingPlayer:
    """Wraps another player and records every choice, so a run can be replayed elsewhere."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.market_buys: dict[int, tuple[int, int]] = {}
        self.decisions: dict[tuple[int, int], Action] = {}

    def market(self, state: InnState, day: DayView, params: Params) -> tuple[int, int]:
        self.market_buys[day.day] = self.inner.market(state, day, params)
        return self.market_buys[day.day]

    def decide(self, state: InnState, day: DayView, slot: int, view: TravelerView, params: Params) -> Action:
        self.decisions[(day.day, slot)] = self.inner.decide(state, day, slot, view, params)
        return self.decisions[(day.day, slot)]
