"""Plain data for a run. Dealt values are frozen; InnState changes as play goes."""
from dataclasses import dataclass
from typing import Literal

Kind = Literal["merchant", "pilgrim", "soldier", "noble", "wanderer"]
Weather = Literal["normal", "cold", "snow"]
FinalEvent = Literal["blizzard", "hungry_soldiers", "robbery"]

KINDS: tuple[Kind, ...] = ("merchant", "pilgrim", "soldier", "noble", "wanderer")
FINAL_EVENTS: tuple[FinalEvent, ...] = ("blizzard", "hungry_soldiers", "robbery")


@dataclass(frozen=True)
class DealtTraveler:
    kind: Kind  # the true kind; a thief is kind="merchant", is_thief=True
    is_thief: bool
    hint: bool
    noble_tier: int  # 0, 1 or 2: the highest ask the noble accepts
    news: str | None  # "weather:<day>=<weather>", "cheap:<day>|none" or "final:<event>"


@dataclass(frozen=True)
class DayDeal:
    day: int
    weather: Weather
    price_food: int
    price_firewood: int
    cheap_day: bool
    base_arrivals: int
    travelers: tuple[DealtTraveler, ...]


@dataclass(frozen=True)
class RunDeal:
    seed: int
    days: tuple[DayDeal, ...]
    final_event: FinalEvent
