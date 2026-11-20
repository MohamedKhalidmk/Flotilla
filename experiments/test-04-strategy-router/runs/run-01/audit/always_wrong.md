# Test 04 pilot: questions every route got wrong

5 of 50 pilot questions; 30 route answers. Built by `always_wrong.py` from `failures.jsonl` (flotilla/failure_audit.py). Diagnosis by hand after reading every answer below.

| Cause (automatic, checked by hand) | Route answers |
|---|---|
| Verifier rejected a correct answer (option check accepted only A to D) | 23 |
| Qwen wrong | 6 |
| Qwen wrong in the majority (one sample was right) | 1 |

No failure here hit the token cap, and the grader matched every final answer correctly (single letters).

## mmlupro-2907 · gold E

**Question**

```text
In what ways are human beings not favorable for studies of inheritance?

A. Inability to conduct controlled breeding experiments
B. Human beings can control their breeding patterns
C. Humans have identical genetic makeup
D. All human traits are polygenic and not influenced by environment
E. Complex genes interaction, environmental control, long lifespan, small family sizes, ethical issues
F. Short lifespan prevents long-term study
G. Lack of genetic variation
H. Too many genes to analyze accurately
I. Humans are too complex to study
J. Human genes are not inheritable
```

**Diagnosis:** All six routes answered E, the gold answer. The verifier's valid_option check accepted only A to D (the item has no options list, and the check fell back to four letters), rejected E as invalid, and the retry had to choose from A to D, so every route ended on A.

| Route | Answers through the verifier | Final | Reasoning (end, trimmed) |
|---|---|---|---|
| Fast | E (reject) → A (accept); samples {'E': 1} | **A** | alse. Option E provides the standard, comprehensive list of difficulties associated with human genetics studies. ```json {"final_answer": "E", "confidence": 1.0, "sources": [], "tool_calls": []} ``` |
| Tools | E (reject) → A (accept); samples {'E': 1} | **A** | most complete and accurate list of reasons why humans are unfavorable for inheritance studies. ```json {"final_answer": "E", "confidence": 0.95, "sources": [], "tool_calls": ["constraint_check"]} ``` |
| Deep | E (reject) → A (accept); samples {'E': 1} | **A** | …. J false. So answer E. Need final JSON only? User says when done end with exactly one JSON block and nothing after it. final_answer one letter. So output JSON with final_answer "E", confidence maybe 0.95, sources empty, tool_calls empty. Ensure no extra text. |
| Deep+Tools | E (reject) → A (accept); samples {'E': 1} | **A** | …s is a multiple-choice question with one correct answer. E lists the standard reasons: complex gene interactions, environmental influence, long lifespan, small family size, ethical issues. Yes, E is the comprehensive answer. I'll answer E with high confidence. |
| Vote | E (reject) → A (accept); samples {'E': 5} | **A** | …nstraints, cannot do controlled breeding, environmental influences, complex traits. Option A is true but incomplete. E best comprehensive. Need final answer exactly one letter. JSON with final_answer "E", confidence maybe 0.95, sources empty, tool_calls empty. |
| Vote+Tools | E (reject) → A (accept); samples {'E': 5} | **A** | …. Option A is also partially correct, but E is more complete. The answer is E. Let me check the format: "final_answer is a single letter." So the answer is E. I don't think a tool is needed, but I could use constraint_check to verify the format. Let's do that. |

## mmlupro-3042 · gold H

**Question**

```text
In attempting to map out the climatic conditions of the biosphere, would a climatologist find it helpful to correspond withan ecologist who has mapped the vegetation formations orbiomes of the biosphere?

A. No, climatologists would find it more helpful to correspond with a geologist.
B. Yes, however, it would be more beneficial to collaborate with a meteorologist.
C. No, because the timescales on which vegetation formations change are too different from climatic shifts.
D. Yes, but the information would be redundant since climate data already includes vegetation patterns.
E. Yes, but only for specific types of vegetation.
F. No, as ecologists' mapping is too detailed for the broad scales used in climatology.
G. Yes, but only in areas where human activity has not altered the natural vegetation.
H. Yes, vegetation-formation mapping does provide a basis for climatic mapping.
I. No, because climatologists use satellite data exclusively for climatic mapping.
J. No, vegetation formations have no relation to climatic conditions.
```

**Diagnosis:** All six routes answered H, the gold answer. The verifier rejected H, the retry gave G, which was rejected too, and G was kept as the final answer. Same bug.

| Route | Answers through the verifier | Final | Reasoning (end, trimmed) |
|---|---|---|---|
| Fast | H (reject) → G (reject); samples {'H': 1} | **G** | tions. Therefore, the most accurate statement is that vegetation mapping provides a basis for climatic mapping. ```json {"final_answer": "H", "confidence": 0.95, "sources": [], "tool_calls": []} ``` |
| Tools | H (reject) → G (reject); samples {'H': 1} | **G** | es provide a basis for climatic mapping. The correct answer is **H**. ```json {"final_answer": "H", "confidence": 0.95, "sources": [], "tool_calls": ["sympy", "python_exec", "constraint_check"]} ``` |
| Deep | H (reject) → G (reject); samples {'H': 1} | **G** | …s. H. Need final JSON only? User says when done, end with exactly one JSON block and nothing after it. final_answer one letter. So output JSON with final_answer "H", confidence maybe 0.95, sources empty, tool_calls empty. Need no extra text. Ensure valid JSON. |
| Deep+Tools | H (reject) → G (reject); samples {'H': 1} | **G** | …The answer is H. I'll provide the final answer directly. I don't think I need tools for this, but let me be thorough. Actually, I'll just give the answer since it's a clear conceptual question. Let me write my reasoning in plain text and then provide the JSON. |
| Vote | H (reject) → G (reject); samples {'H': 5} | **G** | …cology, terrestrial biomes are broad global areas with characteristic vegetation. Climate is major factor. Vegetation maps can help climate mapping. Option H exactly. Need final JSON. Need maybe confidence high. sources empty. tool_calls empty. final_answer H. |
| Vote+Tools | H (reject) → G (reject); samples {'H': 5} | **G** | …cipitation). Historically, climate classification (e.g., Koeppen) used vegetation as a guide. Therefore, mapping vegetation formations provides a basis for mapping climatic conditions. Answer: H. I can call constraint_check on the draft answer. Let me do that. |

## mmlupro-4099 · gold G

**Question**

```text
Assume all gases are perfect unless stated otherwise. Unless otherwise stated, thermodynamic data are for 298.15 K. Calculate the work needed for a $65 \mathrm{~kg}$ person to climb through $4.0 \mathrm{~m}$ on the surface of the Earth.

A. $1.5 \times 10^3 \mathrm{J}$
B. $3.5 \times 10^3 \mathrm{J}$
C. $1.8 \times 10^3$$\mathrm{J}$
D. $2.4 \times 10^3 \mathrm{J}$
E. $3.8 \times 10^3 \mathrm{J}$
F. $2.8 \times 10^3 \mathrm{J}$
G. $2.6 \times 10^3$$\mathrm{J}$
H. $3.2 \times 10^3$$\mathrm{J}$
I. $1.2 \times 10^3 \mathrm{J}$
J. $2.0 \times 10^3$$\mathrm{J}$
```

**Diagnosis:** All six routes answered G (65 kg x 9.8 m/s² x 4.0 m ≈ 2.5 × 10³ J, closest option G = 2.6 × 10³ J), the gold answer. The verifier rejected G and every retry moved to D. Same bug.

| Route | Answers through the verifier | Final | Reasoning (end, trimmed) |
|---|---|---|---|
| Fast | G (reject) → D (accept); samples {'G': 1} | **D** | $ rounded to 2 significant figures is $2.6 \times 10^3 \mathrm{~J}$. Therefore, Option G is the correct answer. ```json {"final_answer": "G", "confidence": 0.95, "sources": [], "tool_calls": []} ``` |
| Tools | G (reject) → D (accept); samples {'G': 1} | **D** | \times 10^3$. Let's double check if $g=10$ was intended. $65 \times 10 \times 4 = 2600 = 2.6 \times 10^3$. This matches Option G exactly. Therefore, the work needed is $2.6 \times 10^3 \mathrm{~J}$. |
| Deep | G (reject) → D (accept); samples {'G': 1} | **D** | …one end with exactly one JSON block and nothing after it. final_answer one letter. Need include confidence sources tool_calls. We can think in analysis. Ensure no extra text after JSON. final_answer: "G". confidence maybe 0.98. sources empty. tool_calls empty. |
| Deep+Tools | G (reject) → D (accept); samples {'G': 1} | **D** | …m set: the answer is 2.5 × 10^3 J. But since 2.5 isn't in the options, the intended answer is probably G (2.6×10^3) using g = 9.81. Let me calculate with sympy/python to confirm. 65 × 9.81 × 4 = 2550.6 → 2.6e3. So the answer is G. Let me run python to confirm. |
| Vote | G (reject) → D (accept); samples {'G': 5} | **D** | …osest. Maybe if g=10: 2600 J exactly G. So answer G. Need final with JSON only? User says when done, end with exactly one JSON block and nothing after it. final_answer one letter. Need include confidence etc. No sources. tool_calls empty. Ensure no extra text. |
| Vote+Tools | G (reject) → D (accept); samples {'G': 5} | **D** | …4.0 m = 65 × 39.2 = 2548 J ≈ 2.5 × 10³ J. Hmm, this isn't in the options. Let me calculate: 65 × 9.8 × 4 = 2548. Options: 2.6×10³ (G) is the closest. Maybe they used g = 9.8: 2548 ≈ 2.5e3. If g=10: 2600 → 2.6×10³. So the answer is G. Let me verify with python. |

## mmlupro-10772 · gold I

**Question**

```text
Give a list of the character set used inPL/I. Also define the term'variable', and explain what is meant by an 'assign-ment statement'.

A. 70 different characters, variable is constant, assignment statement assigns a variable to a value
B. 50 different characters, variable can't vary, assignment statement assigns a variable to a function
C. 85 different characters, variable is a label for a value, assignment statement updates the value of a variable without changing the label
D. 90 different characters, variable is a fixed point in memory, assignment statement creates a new variable
E. 65 different characters, variable holds temporary data, assignment statement links two variables
F. 55 different characters, variable can change type, assignment statement copies a function's output to a variable
G. 75 different characters, variable represents a specific type, assignment statement changes the type of a variable
H. 80 different characters, variable is a function, assignment statement assigns a function to a variable
I. 60 different characters, variable can vary, assignment statement assigns a value to a variable
J. 100 different characters, variable is a placeholder, assignment statement transfers data from one variable to another
```

**Diagnosis:** Five routes answered C on the first try and kept it: Qwen is wrong (it reads the question as asking about the PL/I character set size and picks the 'label for a value' wording). Only Tools first answered I, the gold answer, which the verifier rejected (same bug); one Vote+Tools sample also said I but lost the vote.

| Route | Answers through the verifier | Final | Reasoning (end, trimmed) |
|---|---|---|---|
| Fast | C (accept) | **C** | Option C is the intended answer based on the specific character count and the precise definition of assignment. ```json {"final_answer": "C", "confidence": 0.95, "sources": [], "tool_calls": []} ``` |
| Tools | I (reject) → C (accept); samples {'I': 1} | **C** | ```json {"final_answer": "I", "confidence": 0.7, "sources": [], "tool_calls": ["python_exec", "sympy"]} ``` |
| Deep | C (accept) | **C** | …no sources. tool_calls empty. final JSON. Double-check if PL/I character set count could be 90? Option D has 90 but variable fixed point in memory wrong. H 80 variable function wrong. J 100 placeholder maybe. C best. Let's maybe include confidence 0.85. final. |
| Deep+Tools | C (accept) | **C** | …lly, I recall that some PL/I textbooks describe the character set as having a specific number of characters. Without knowing the exact textbook, I'll rely on the quality of the definitions. C has the best conceptual definition. I'll go with C. Final answer: C. |
| Vote | C (accept); samples {'C': 5} | **C** | …'variable', and explain what is meant by an 'assign-ment statement'." It's likely from a quiz where answer C summarizes. Need final letter C. Need ensure final JSON format exactly. final_answer one letter. confidence maybe 0.9. sources empty. tool_calls empty. |
| Vote+Tools | C (accept); samples {'C': 3, 'I': 2} | **C** | …6 + 26 + 10 + 23 = 85. This is plausible! So the answer is C. Let me confirm: C. 85 different characters, a variable is a label for a value, an assignment statement updates the value of a variable without changing the label. Yes, I'm confident the answer is C. |

## mmlupro-3393 · gold G

**Question**

```text
Which of the following characteristics is predicted for an early-successional plant community?

A. High detrital biomass
B. High number of predatory species
C. High presence of fully matured plant species
D. High frequency of R-selected species
E. High rates of soil nutrient depletion
F. High diversity of plant species
G. High ratios of primary production to standing-crop biomass
H. High frequency of K-selected species
I. Low rates of photosynthesis
J. High niche divergence among co-occurring species
```

**Diagnosis:** Deep, Deep+Tools, Vote and Vote+Tools answered G, the gold answer, and the verifier rejected it (same bug); their retries moved to D. Fast and Tools (thinking off) answered D on the first try, which is Qwen being wrong: high R-selected frequency is a plausible distractor.

| Route | Answers through the verifier | Final | Reasoning (end, trimmed) |
|---|---|---|---|
| Fast | D (accept) | **D** | nd low competition, allowing them to colonize and reproduce quickly. Therefore, Option D is the correct answer. ```json {"final_answer": "D", "confidence": 0.95, "sources": [], "tool_calls": []} ``` |
| Tools | D (accept) | **D** | ures of early succession: - Rapid growth - High reproductive rate - Short lifespan - High dispersal - Low competitive ability These are r-selected traits. Therefore, D is the most appropriate answer. |
| Deep | G (reject) → D (accept); samples {'G': 1} | **D** | …ncluded P/B ratio. r/K selection was later. The phrase "predicted" might be from "successional model predicts that early successional communities will have high P/B ratios". So G. I will final G with confidence 0.65. Need JSON exactly. Ensure no trailing text. |
| Deep+Tools | G (reject) → D (accept); samples {'G': 1} | **D** | …as the answer, because it's the most specific and technical characteristic of early succession. The P/B ratio is a classic metric that distinguishes early from late succession. Final answer: G. Confidence: 0.7. Let me use constraint_check to verify the format. |
| Vote | G (reject) → D (accept); samples {'G': 4, 'D': 1} | **D** | …al JSON valid. final_answer: "G". confidence: maybe 0.72 due to D ambiguity. But if answer is D, confidence low. Could set 0.7. The instruction: confidence probability final_answer is correct. I'd set 0.75. Need no extra text after JSON. final only JSON block. |
| Vote+Tools | G (reject) → D (accept); samples {'G': 5} | **D** | …might be a distractor if the test maker is thinking of r/K in a different context... no, that doesn't make sense. You know what, let me just commit to G. It's a classic, defensible answer for early-successional plant communities. Let me write the final answer. |

