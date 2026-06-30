# Eval Results

## Part A — Decision engine regression (deterministic)

**22/22 passed** — engine output matches independently re-derived RTO formula + documented confidence thresholds.


## Part B — NL assistant route matching (live Claude calls)

- **High-confidence precision (primary metric): 100%** (15/15) — of all routes the assistant matched, how many were correct. This is the number that matters: a wrong high-confidence match is the failure mode that breaks trust.

- **Coverage (secondary): 100%** (15/15) — of queries with a real matching route, how many it successfully matched instead of punting.

- **Correct refusal rate: 100%** (6/6) — of out-of-scope queries, how many it correctly declined rather than guessing.


**Per-case detail:**

| Query | Expected | Actual | Outcome |
|---|---|---|---|
| auto from Andheri Station to Versova | andheri_versova | andheri_versova | correct_match |
| should I book a cab from Bandra station to BKC right now | bandra_bkc | bandra_bkc | correct_match |
| Kurla to Powai at night | kurla_powai | kurla_powai | correct_match |
| going from Andheri to Borivali, what's cheaper | andheri_borivali | andheri_borivali | correct_match |
| Goregaon to Malad, quick trip | goregaon_malad | goregaon_malad | correct_match |
| Vile Parle to the airport terminal 2 | vileparle_airport | vileparle_airport | correct_match |
| Mulund to Thane during rush hour | mulund_thane | mulund_thane | correct_match |
| Powai to Chembur tonight | powai_chembur | powai_chembur | correct_match |
| Dadar to Worli, is auto even an option | dadar_worli | dadar_worli | correct_match |
| CST to Colaba quick | cst_colaba | cst_colaba | correct_match |
| from Bandra all the way to Fort | bandra_fort | bandra_fort | correct_match |
| Andheri Station to Versova during heavy rain, surge must be insane | andheri_versova | andheri_versova | correct_match |
| I'm near Kurla railway station going towards Powai | kurla_powai | kurla_powai | correct_match |
| evening commute Mulund to Thane around 7pm | mulund_thane | mulund_thane | correct_match |
| after midnight ride from Powai to Chembur | powai_chembur | powai_chembur | correct_match |
| best way from Mars to Jupiter | *(no match)* | *(no match)* | correct_refusal |
| auto from my house to the office | *(no match)* | *(no match)* | correct_refusal |
| how much to go from Delhi to Mumbai | *(no match)* | *(no match)* | correct_refusal |
| asdkjfh aksjdfh random gibberish query | *(no match)* | *(no match)* | correct_refusal |
| from Churchgate to Marine Drive | *(no match)* | *(no match)* | correct_refusal |
| from Andheri to some random unknown place XYZ123 | *(no match)* | *(no match)* | correct_refusal |