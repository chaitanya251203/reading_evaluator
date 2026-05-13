# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.alignment_service import align_words, _clean_word, _is_match

# Test 1: punctuation stripping
print("है। vs है:", _is_match("है।", "है"))
print("होमवर्क vs होमवर्क:", _is_match("होमवर्क", "होमवर्क"))
print("दोस्तों vs दोस्तों:", _is_match("दोस्तों", "दोस्तों"))
print("खेलना vs खेलना:", _is_match("खेलना", "खेलना"))
print("करता vs करते:", _is_match("करता", "करते"))

# Test 2: full passage alignment
exp = "राम एक छोटा लड़का है वह रोज सुबह जल्दी उठता है और स्कूल जाता है".split()
spk = "राम एक छोटा लड़का है वह रोज सुबह जल्दी उठता है और स्कूल जाता है".split()
r = align_words(exp, spk)
print(f"\nPerfect match: {r['correct_count']}/{len(exp)} correct, {r['wrong_count']} wrong")

# Test 3: slightly different transcript
spk2 = "राम एक छोटा लड़का है वह रोज सुबह जल्दी उठता है और स्कूल जाता".split()
r2 = align_words(exp, spk2)
print(f"Missing last word: {r2['correct_count']}/{len(exp)} correct, {r2['wrong_count']} wrong")
print("Statuses:", r2['statuses'])
