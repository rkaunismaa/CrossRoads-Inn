class_name DealtTraveler
extends RefCounted
## One dealt traveler. kind is the true kind: a thief is kind "merchant" with is_thief true.

var kind: String
var is_thief: bool
var hint: bool
var noble_tier: int  ## 0, 1 or 2: the highest ask the noble accepts
var news: String  ## "weather:<day>=<weather>", "cheap:<day>|none", "final:<event>", or "" for none


func _init(p_kind: String = "", p_is_thief: bool = false, p_hint: bool = false, p_noble_tier: int = 0,
		p_news: String = "") -> void:
	kind = p_kind
	is_thief = p_is_thief
	hint = p_hint
	noble_tier = p_noble_tier
	news = p_news
