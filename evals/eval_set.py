"""
Two distinct eval sets, because the two halves of this system have
different kinds of uncertainty:

  - DECISION_CASES tests the deterministic engine (fare math + confidence
    calibration). There's no model uncertainty here — it's regression
    testing against an independently re-derived formula, to catch
    calculation/threshold bugs, not to measure "accuracy" in the ML sense.

  - NL_CASES tests the one place real uncertainty exists: can Claude
    correctly map a messy human sentence to the right preset route (or
    correctly refuse when it shouldn't guess). This is where a precision
    metric actually means something.
"""

# (route_id, time_of_day, surge) -> nothing pre-computed; run_evals.py derives
# expected confidence/direction independently from the published tariff +
# documented thresholds and checks decision.py's actual output against it.
DECISION_CASES = [
    ("andheri_versova", "day", 1.0),
    ("andheri_versova", "day", 1.3),
    ("andheri_versova", "day", 1.5),
    ("andheri_versova", "night", 1.0),
    ("bandra_bkc", "day", 1.0),
    ("bandra_bkc", "day", 1.5),
    ("bandra_bkc", "night", 1.0),
    ("kurla_powai", "day", 1.0),
    ("kurla_powai", "night", 1.0),
    ("kurla_powai", "night", 1.5),
    ("andheri_borivali", "day", 1.0),
    ("andheri_borivali", "day", 2.0),
    ("goregaon_malad", "day", 1.0),
    ("vileparle_airport", "day", 1.0),
    ("vileparle_airport", "night", 1.3),
    ("mulund_thane", "day", 1.0),
    ("powai_chembur", "day", 1.0),
    ("powai_chembur", "night", 1.0),
    ("dadar_worli", "day", 1.0),       # zone-restricted
    ("dadar_worli", "day", 1.5),       # zone-restricted + surge
    ("cst_colaba", "day", 1.0),        # zone-restricted
    ("bandra_fort", "night", 1.3),     # zone-restricted + night + surge
]

# NL cases. Since the assistant now handles ARBITRARY Mumbai routes (geocoded),
# it no longer matches preset IDs. A case is:
#   {query, should_match, expect_zone (bool|None), expect_in_labels (substrings)}
# - should_match=True  -> a real Mumbai pickup+drop the assistant should resolve.
# - should_match=False -> vague / out-of-region / gibberish it should REFUSE.
# - expect_zone: if set, the resolved trip must (True) / must not (False) be
#   flagged as no-auto-zone. Verifies the point-in-polygon check via the NL path.
# - expect_in_labels: substrings that must appear in the resolved origin+dest
#   labels (loose sanity check that the right places were geocoded).
NL_CASES = [
    {"query": "auto from Andheri Station to Versova right now", "should_match": True,
     "expect_zone": False, "expect_in_labels": ["andheri", "versova"]},
    {"query": "BKC from Bandra at 6pm, surge is crazy", "should_match": True,
     "expect_zone": False, "expect_in_labels": ["bandra", "bkc"]},
    {"query": "auto from Lokhandwala to Nariman Point around 1am", "should_match": True,
     "expect_zone": True, "expect_in_labels": ["lokhandwala", "nariman"]},
    {"query": "Kurla to Powai tonight", "should_match": True,
     "expect_zone": False, "expect_in_labels": ["kurla", "powai"]},
    {"query": "Dadar to Worli, is auto even an option", "should_match": True,
     "expect_zone": True, "expect_in_labels": ["dadar", "worli"]},
    {"query": "Ghatkopar to Chembur in the evening", "should_match": True,
     "expect_zone": False, "expect_in_labels": ["ghatkopar", "chembur"]},
    {"query": "Juhu to Andheri quick", "should_match": True,
     "expect_zone": False, "expect_in_labels": ["juhu", "andheri"]},
    {"query": "from Bandra all the way to Fort", "should_match": True,
     "expect_zone": True, "expect_in_labels": ["bandra", "fort"]},
    {"query": "Goregaon to Malad during heavy rain, surge must be insane", "should_match": True,
     "expect_zone": False, "expect_in_labels": ["goregaon", "malad"]},
    {"query": "Colaba to Churchgate", "should_match": True,
     "expect_zone": True, "expect_in_labels": ["colaba", "churchgate"]},
    {"query": "Powai to Vikhroli after midnight", "should_match": True,
     "expect_zone": False, "expect_in_labels": ["powai", "vikhroli"]},
    {"query": "Mulund to Thane during rush hour", "should_match": True,
     "expect_zone": False, "expect_in_labels": ["mulund", "thane"]},

    {"query": "how much to go from Delhi to Mumbai", "should_match": False},
    {"query": "best way from Mars to Jupiter", "should_match": False},
    {"query": "asdkjfh aksjdfh random gibberish query", "should_match": False},
    {"query": "auto from my house to the office", "should_match": False},
    {"query": "should I take an auto right now", "should_match": False},
    {"query": "from Bangalore to Chennai", "should_match": False},
]
