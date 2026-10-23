class_name DayRunner
extends RefCounted
## Plays a dealt run one step at a time (morning, each traveler, night), keeping the same ledger
## as Python's play_run. The UI and the parity test both drive the game through this class.

var params: Dictionary
var deal: RunDeal
var state: InnState
var ledger: PackedStringArray = []
var day: int = 1  ## 1-based current day

var _count := 0  ## travelers who really arrive today
var _slot := 1  ## 1-based slot of the traveler at the counter
var _over := false
var _lost_on_day := 0
var _last_day: int


func _init(p: Dictionary, d: RunDeal) -> void:
	params = p
	deal = d
	state = InnRules.new_state(p)
	_last_day = int(p.days)


## Morning: pay upkeep and count today's arrivals. Returns false if the run is lost.
func begin_day() -> bool:
	InnRules.pay_upkeep(state, params)
	if state.lost:
		ledger.append("Day %d: could not pay upkeep, run lost" % day)
		_lost_on_day = day
		_over = true
		return false
	_count = InnRules.arrivals(state, day_deal(), params)
	state.walkout_yesterday = false
	_slot = 1
	return true


func day_deal() -> DayDeal:
	return deal.days[day - 1]


func arrivals_today() -> int:
	return _count


## Market buys (capped to what coins allow, food first), then the doors open.
func buy(food: int, firewood: int) -> void:
	InnRules.buy(state, day_deal(), food, firewood)
	ledger.append("Day %d: %s, %d travelers, coins %d food %d firewood %d"
		% [day, day_deal().weather, _count, state.coins, state.food, state.firewood])


func has_traveler() -> bool:
	return _slot <= _count


func slot() -> int:
	return _slot


func travelers_left() -> int:
	return maxi(0, _count - _slot + 1)


func current() -> DealtTraveler:
	return day_deal().travelers[_slot - 1]


func current_view() -> TravelerView:
	return InnRules.traveler_view(state, current(), params)


## Apply the player's choice for the traveler at the counter and move to the next one.
func decide(action: String) -> String:
	var view := current_view()
	var outcome := InnRules.serve(state, current(), action, params)
	ledger.append("Day %d slot %d: %s -> %s: %s" % [day, _slot, view.kind_shown, action, outcome])
	_slot += 1
	return outcome


## Night (and the final event on the last day). Returns the night notes.
func end_day() -> String:
	var final := deal.final_event if day == _last_day else ""
	var notes := InnRules.night(state, day_deal(), params, final)
	ledger.append("Day %d night: %s; now coins %d food %d firewood %d"
		% [day, notes, state.coins, state.food, state.firewood])
	if day == _last_day:
		ledger.append("End: %d coins vs debt %d: %s" % [state.coins, int(params.debt), "WIN" if _won() else "LOSS"])
		_over = true
	else:
		day += 1
	return notes


func is_over() -> bool:
	return _over


func _won() -> bool:
	return _lost_on_day == 0 and state.coins >= params.debt


## {won, end_coins, lost_on_day}; lost_on_day is 0 when the run was not lost early.
func result() -> Dictionary:
	return {"won": _over and _won(), "end_coins": state.coins, "lost_on_day": _lost_on_day}
