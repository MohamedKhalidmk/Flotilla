# Test 04 run-01: questions every route got wrong

5 of 50 questions; six routes each. For each: the question, the gold answer, every route's answer through the verifier (first answer, verdict, final), and the diagnosis made by hand. Built by `always_wrong.py` from `failures.jsonl` and `diagnosis.json`.

| Diagnosis | Questions |
|---|---|
| verifier bug | 4 |
| model wrong | 1 |

## Verifier bug (4)

### mmlupro-2907 · science_mc · gold: E

<details open><summary>Question</summary>

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

</details>

**Diagnosis (verifier bug):** All six routes answered E, the gold. The verifier's option check accepted only A to D (the item has no options list) and rejected E; every retry ended on A.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | E (reject) → A (accept) | A |
| Tools | E (reject) → A (accept) | A |
| Deep | E (reject) → A (accept) | A |
| Deep+Tools | E (reject) → A (accept) | A |
| Vote | E (reject) → A (accept) | A |
| Vote+Tools | E (reject) → A (accept) | A |

### mmlupro-3042 · science_mc · gold: H

<details open><summary>Question</summary>

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

</details>

**Diagnosis (verifier bug):** All six routes answered H, the gold. The verifier rejected H; the retry gave G, also rejected, and G was kept.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | H (reject) → G (reject) | G |
| Tools | H (reject) → G (reject) | G |
| Deep | H (reject) → G (reject) | G |
| Deep+Tools | H (reject) → G (reject) | G |
| Vote | H (reject) → G (reject) | G |
| Vote+Tools | H (reject) → G (reject) | G |

### mmlupro-3393 · science_mc · gold: G

<details open><summary>Question</summary>

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

</details>

**Diagnosis (verifier bug):** Deep, Deep+Tools, Vote and Vote+Tools answered G, the gold, and the verifier rejected it; their retries moved to D. Fast and Tools (thinking off) answered D on the first try, which is Qwen being wrong on those two routes.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | D (accept) | D |
| Tools | D (accept) | D |
| Deep | G (reject) → D (accept) | D |
| Deep+Tools | G (reject) → D (accept) | D |
| Vote | G (reject) → D (accept) | D |
| Vote+Tools | G (reject) → D (accept) | D |

### mmlupro-4099 · science_mc · gold: G

<details open><summary>Question</summary>

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

</details>

**Diagnosis (verifier bug):** All six routes answered G (65 kg x 9.8 m/s^2 x 4.0 m = 2.5 x 10^3 J, closest option G = 2.6 x 10^3 J), the gold. The verifier rejected G and every retry moved to D.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | G (reject) → D (accept) | D |
| Tools | G (reject) → D (accept) | D |
| Deep | G (reject) → D (accept) | D |
| Deep+Tools | G (reject) → D (accept) | D |
| Vote | G (reject) → D (accept) | D |
| Vote+Tools | G (reject) → D (accept) | D |

## Model wrong (1)

### mmlupro-10772 · science_mc · gold: I

<details open><summary>Question</summary>

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

</details>

**Diagnosis (model wrong):** Five routes answered C on the first try and kept it; gold is I. Only Tools first answered I, which the verifier rejected (same bug), and one Vote+Tools sample said I but lost the vote. Mostly Qwen is wrong.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | C (accept) | C |
| Tools | I (reject) → C (accept) | C |
| Deep | C (accept) | C |
| Deep+Tools | C (accept) | C |
| Vote | C (accept) | C |
| Vote+Tools | C (accept) | C |

