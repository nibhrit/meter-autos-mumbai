# Eval Results

## Part A — Decision engine regression (deterministic)

**22/22 passed** — engine output matches independently re-derived RTO formula + documented confidence thresholds.


## Part B — NL assistant, arbitrary Mumbai routes (live Claude + geocoding)

The assistant now resolves any Mumbai pickup/drop (not just presets): Claude extracts the place names, deterministic code geocodes them, and a mis-named or non-Mumbai place fails to geocode and is refused rather than guessed. A match is 'correct' only if the right places resolved AND the no-auto-zone flag is right.

- **High-confidence precision (primary metric): 100%** (12/12) — of every trip the assistant resolved, how many were correct (right places + right zone call). A confidently-wrong answer is the failure mode this project exists to prevent.

- **Coverage (secondary): 100%** (12/12) — of queries with a real Mumbai pickup+drop, how many resolved correctly instead of punting.

- **Correct refusal rate: 100%** (6/6) — of vague / out-of-region / gibberish queries, how many it declined rather than guessing.


**Per-case detail:**

| Query | Should match | Resolved to | Outcome |
|---|---|---|---|
| auto from Andheri Station to Versova right now | True | Andheri Station Road, K/E Ward, Mumbai → Versova, K/W Ward, Mumbai | correct_match |
| BKC from Bandra at 6pm, surge is crazy | True | Bandra, Bandra West, Mumbai → BKC - Eastern Express Highway Road, H/E Ward, Mumbai | correct_match |
| auto from Lokhandwala to Nariman Point around 1am | True | Lokhandwala Complex, K/W Ward, Mumbai → Nariman Point, A Ward, Mumbai | correct_match |
| Kurla to Powai tonight | True | Kurla, L Ward, Mumbai → Powai, S Ward, Mumbai | correct_match |
| Dadar to Worli, is auto even an option | True | Dadar, G/N Ward → Worli, G/S Ward | correct_match |
| Ghatkopar to Chembur in the evening | True | Ghatkopar, N Ward, Mumbai → Chembur, M/W Ward, Mumbai | correct_match |
| Juhu to Andheri quick | True | Juhu, K/W Ward, Mumbai → Andheri, K/W Ward, Mumbai | correct_match |
| from Bandra all the way to Fort | True | Bandra, Bandra West, Mumbai → Fort, A Ward | correct_match |
| Goregaon to Malad during heavy rain, surge must be insane | True | Goregaon, P/S Ward, Mumbai → Malad, P/N Ward, Mumbai | correct_match |
| Colaba to Churchgate | True | Colaba, A Ward → Churchgate, A Ward | correct_match |
| Powai to Vikhroli after midnight | True | Powai, S Ward, Mumbai → Vikhroli, S Ward, Mumbai | correct_match |
| Mulund to Thane during rush hour | True | Mulund, T Ward, Mumbai → Thane | correct_match |
| how much to go from Delhi to Mumbai | False | *(refused)* | correct_refusal |
| best way from Mars to Jupiter | False | *(refused)* | correct_refusal |
| asdkjfh aksjdfh random gibberish query | False | *(refused)* | correct_refusal |
| auto from my house to the office | False | *(refused)* | correct_refusal |
| should I take an auto right now | False | *(refused)* | correct_refusal |
| from Bangalore to Chennai | False | *(refused)* | correct_refusal |