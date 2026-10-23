from inn_sim.deal import deal_run
from inn_sim.params import params_from_defaults

P = params_from_defaults()


def _all_travelers(seeds):
    return [t for s in seeds for d in deal_run(P, s).days for t in d.travelers]


def test_same_seed_same_deal():
    assert deal_run(P, 7) == deal_run(P, 7)


def test_different_seeds_differ():
    assert deal_run(P, 1) != deal_run(P, 2)


def test_shape():
    d = deal_run(P, 3)
    assert len(d.days) == 7 and all(len(x.travelers) == 6 for x in d.days)
    assert all(3 <= x.base_arrivals <= 5 for x in d.days)
    assert [x.day for x in d.days] == [1, 2, 3, 4, 5, 6, 7]
    assert d.final_event in ("blizzard", "hungry_soldiers", "robbery")


def test_only_merchants_can_be_thieves():
    ts = _all_travelers(range(200))
    assert any(t.is_thief for t in ts)
    assert all(t.kind == "merchant" for t in ts if t.is_thief)


def test_only_wanderers_carry_news():
    ts = _all_travelers(range(200))
    assert all((t.news is not None) == (t.kind == "wanderer") for t in ts)


def test_news_tells_the_truth():
    for s in range(200):
        d = deal_run(P, s)
        for day in d.days:
            for t in day.travelers:
                if t.news is None:
                    continue
                topic, _, value = t.news.partition(":")
                if topic == "final":
                    assert value == d.final_event
                elif topic == "weather":
                    when, _, weather = value.partition("=")
                    assert int(when) == day.day + 1 and d.days[int(when) - 1].weather == weather
                else:
                    assert topic == "cheap"
                    later = [x.day for x in d.days if x.day > day.day and x.cheap_day]
                    assert value == (str(later[0]) if later else "none")


def test_only_nobles_have_tiers():
    ts = _all_travelers(range(200))
    assert all(t.noble_tier == 0 for t in ts if t.kind != "noble")
    assert {t.noble_tier for t in ts if t.kind == "noble"} == {0, 1, 2}


def test_weather_frequencies_roughly_match_params():
    days = [d for s in range(286) for d in deal_run(P, s).days]
    snow = sum(d.weather == "snow" for d in days) / len(days)
    cold = sum(d.weather == "cold" for d in days) / len(days)
    assert abs(snow - 0.15) <= 0.03 and abs(cold - 0.30) <= 0.04


def test_cheap_day_halves_firewood_price():
    days = [d for s in range(200) for d in deal_run(P, s).days]
    cheap = [d for d in days if d.cheap_day]
    assert cheap
    assert all(1 <= d.price_firewood <= round(2 * 1.25 * 0.5) for d in cheap)
    assert all(d.price_food >= 1 and d.price_firewood >= 1 for d in days)
