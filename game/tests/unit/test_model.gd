extends GutTest


func _fixture(name: String) -> Dictionary:
	return JSON.parse_string(FileAccess.get_file_as_string("res://tests/fixtures/%s.json" % name))


func test_run_deal_from_fixture() -> void:
	var f := _fixture("careful_3")
	var deal := RunDeal.from_dict(f.deal)
	assert_eq(deal.seed, 3)
	assert_eq(deal.days.size(), 7)
	assert_eq(deal.days[0].travelers.size(), 6)
	assert_eq(deal.days[0].day, 1)
	assert_true(deal.final_event in ["blizzard", "hungry_soldiers", "robbery"])


func test_traveler_fields_and_missing_news() -> void:
	var deal := RunDeal.from_dict(_fixture("careful_3").deal)
	for d: DayDeal in deal.days:
		for t: DealtTraveler in d.travelers:
			if t.kind == "wanderer":
				assert_ne(t.news, "")
			else:
				assert_eq(t.news, "")
			assert_typeof(t.noble_tier, TYPE_INT)


func test_snapshot_lists_all_fields() -> void:
	var s := InnState.new(5, 6, 7)
	s.news.append("final:robbery")
	var snap := s.snapshot()
	for key in ["coins", "food", "firewood", "goodwill", "occupied", "thieves_tonight", "walkout_yesterday", "lost", "news"]:
		assert_true(snap.has(key), key)
	assert_eq(snap.coins, 5)
	assert_eq(snap.news, ["final:robbery"])


func test_snapshot_is_a_copy() -> void:
	var s := InnState.new(5, 6, 7)
	var snap := s.snapshot()
	s.news.append("x")
	assert_eq(snap.news, [])
