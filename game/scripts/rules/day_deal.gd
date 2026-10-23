class_name DayDeal
extends RefCounted
## Everything rolled up front for one day.

var day: int
var weather: String
var price_food: int
var price_firewood: int
var cheap_day: bool
var base_arrivals: int
var travelers: Array[DealtTraveler] = []
