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

# Each NL case: (query, expected_route_id_or_None)
# expected_route_id is None for queries the assistant should REFUSE to match
# (out-of-scope city, gibberish, no real route) rather than guess at.
NL_CASES = [
    ("auto from Andheri Station to Versova", "andheri_versova"),
    ("should I book a cab from Bandra station to BKC right now", "bandra_bkc"),
    ("Kurla to Powai at night", "kurla_powai"),
    ("going from Andheri to Borivali, what's cheaper", "andheri_borivali"),
    ("Goregaon to Malad, quick trip", "goregaon_malad"),
    ("Vile Parle to the airport terminal 2", "vileparle_airport"),
    ("Mulund to Thane during rush hour", "mulund_thane"),
    ("Powai to Chembur tonight", "powai_chembur"),
    ("Dadar to Worli, is auto even an option", "dadar_worli"),
    ("CST to Colaba quick", "cst_colaba"),
    ("from Bandra all the way to Fort", "bandra_fort"),
    ("Andheri Station to Versova during heavy rain, surge must be insane", "andheri_versova"),
    ("I'm near Kurla railway station going towards Powai", "kurla_powai"),
    ("evening commute Mulund to Thane around 7pm", "mulund_thane"),
    ("after midnight ride from Powai to Chembur", "powai_chembur"),
    ("best way from Mars to Jupiter", None),
    ("auto from my house to the office", None),
    ("how much to go from Delhi to Mumbai", None),
    ("asdkjfh aksjdfh random gibberish query", None),
    ("from Churchgate to Marine Drive", None),
    ("from Andheri to some random unknown place XYZ123", None),
]
