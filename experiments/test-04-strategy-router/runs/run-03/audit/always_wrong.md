# Test 04 run-03: questions every route got wrong

17 of 1450 questions; six routes each. For each: the question, the gold answer, every route's answer through the verifier (first answer, verdict, final), and the diagnosis made by hand. Built by `always_wrong.py` from `failures.jsonl` and `diagnosis.json`.

| Diagnosis | Questions |
|---|---|
| grader bug | 1 |
| wrong gold | 10 |
| model wrong | 6 |

## Grader bug (1)

### math-train-precalculus-663 · math · gold: \begin{pmatrix} -2/3 \\ 2/3 \\ 1/3 \end{pmatrix}

<details open><summary>Question</summary>

```text
Find a unit vector that is orthogonal to both $\begin{pmatrix} 1 \\ 1 \\ 0 \end{pmatrix}$ and $\begin{pmatrix} 1 \\ 0 \\ 2 \end{pmatrix}.$
```

</details>

**Diagnosis (grader bug):** Answers (2/3, -2/3, -1/3): a unit vector orthogonal to both, the negative of the gold (-2/3, 2/3, 1/3). Both are correct; the grader accepts only the gold's sign.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | \begin{pmatrix} 2/3 \\ -2/3 \\ -1/3 \end… (accept) | \begin{pmatrix} 2/3 \\ -2/3 \\ -1/3 \end{pmatrix} |
| Tools | \begin{pmatrix} 2/3 \\ -2/3 \\ -1/3 \end… (accept) | \begin{pmatrix} 2/3 \\ -2/3 \\ -1/3 \end{pmatrix} |
| Deep | (2/3, -2/3, -1/3) (accept) | (2/3, -2/3, -1/3) |
| Deep+Tools | \left(\frac{2}{3}, -\frac{2}{3}, -\frac{… (accept) | \left(\frac{2}{3}, -\frac{2}{3}, -\frac{1}{3}\right) |
| Vote | (2/3, -2/3, -1/3) (accept) | (2/3, -2/3, -1/3) |
| Vote+Tools | (2/3, -2/3, -1/3) (accept) | (2/3, -2/3, -1/3) |

## Wrong gold (10)

### gsm8k-train-1464 · math · gold: 868000

<details open><summary>Question</summary>

```text
During the outbreak of the coronavirus, a company had to ramp up its toilet paper production three times more to cover the increased demand. If the company was producing 7000 toilet paper per day, calculate its total toilet paper production during March of 2020 after increasing its production.
```

</details>

**Diagnosis (wrong gold):** 'Three times more' read as 3 x 7000 x 31 = 651,000 by every route; the gold 868,000 uses 4 x 7000 x 31. The wording is ambiguous; Qwen's reading is the common one.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | 651000 (accept) | 651000 |
| Tools | 651000 (accept) | 651000 |
| Deep | 651000 (accept) | 651000 |
| Deep+Tools | 651000 (accept) | 651000 |
| Vote | 651000 (accept) | 651000 |
| Vote+Tools | 651000 (accept) | 651000 |

### gsm8k-train-2338 · math · gold: 30

<details open><summary>Question</summary>

```text
A bottle can hold 2 cups of water. How many cups of water are needed to fill up 10 whole bottles and 5 half-capacity bottles?
```

</details>

**Diagnosis (wrong gold):** 10 bottles x 2 cups + 5 half bottles x 1 cup = 25 cups. Every route answered 25; the gold says 30.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | 25 (accept) | 25 |
| Tools | 25 (accept) | 25 |
| Deep | 25 (accept) | 25 |
| Deep+Tools | 25 (accept) | 25 |
| Vote | 25 (accept) | 25 |
| Vote+Tools | 25 (accept) | 25 |

### gsm8k-train-2882 · math · gold: 4

<details open><summary>Question</summary>

```text
Dexter and Jay are using a gallon of white paint to paint the walls. Dexter used 3/8 of the gallon of paint while Jay used 5/8 of a gallon of paint. If a gallon is equal to 4 liters, how many liters of paint were left from Dexter and Jay combined?
```

</details>

**Diagnosis (wrong gold):** Dexter used 3/8 and Jay 5/8 of one gallon, so nothing is left: every route answered 0. The gold 4 (litres) assumes each had a gallon, which the question does not say.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | 0 (accept) | 0 |
| Tools | 0 (accept) | 0 |
| Deep | 0 (accept) | 0 |
| Deep+Tools | 0 (accept) | 0 |
| Vote | 0 (accept) | 0 |
| Vote+Tools | 0 (accept) | 0 |

### gsm8k-train-3588 · math · gold: 30

<details open><summary>Question</summary>

```text
A group of bedbugs infested an old mattress. Every day, the number of bedbugs would triple. After four days, there were 810 bedbugs burrowing into the mattress. How many bedbugs did the group start with?
```

</details>

**Diagnosis (wrong gold):** Tripling each day for four days: start x 3^4 = 810, start = 10 (every route). The gold 30 uses three triplings.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | 10 (accept) | 10 |
| Tools | 10 (accept) | 10 |
| Deep | 10 (accept) | 10 |
| Deep+Tools | 10 (accept) | 10 |
| Vote | 10 (accept) | 10 |
| Vote+Tools | 10 (accept) | 10 |

### gsm8k-train-5436 · math · gold: 55

<details open><summary>Question</summary>

```text
Wendy has 5 facial products she puts on in the morning and she waits 5 minutes between each product.  She also spends an additional 30 minutes putting on her make-up.  How much time does it take her to put on her "full face?"
```

</details>

**Diagnosis (wrong gold):** 5 products with 5 minutes between each: 4 waits = 20 minutes + 30 = 50 (every route). The gold 55 counts 5 waits; ambiguous at best.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | 50 (accept) | 50 |
| Tools | 50 (accept) | 50 |
| Deep | 50 minutes (accept) | 50 minutes |
| Deep+Tools | 50 (accept) | 50 |
| Vote | 50 minutes (accept) | 50 minutes |
| Vote+Tools | 50 (accept) | 50 |

### lcb-abc337_e · code · gold: the task's stdin/stdout tests

<details open><summary>Question</summary>

```text
This is an interactive problem (a type of problem where your program interacts with the judge program through Standard Input and Output).
There are N bottles of juice, numbered 1 to N. It has been discovered that exactly one of these bottles has gone bad. Even a small sip of the spoiled juice will cause stomach upset the next day.
Takahashi must identify the spoiled juice by the next day. To do this, he decides to call the minimum necessary number of friends and serve them some of the N bottles of juice. He can give any number of bottles to each friend, and each bottle of juice can be given to any number of friends.
Print the number of friends to call and how to distribute the juice, then receive information on whether each friend has an upset stomach the next day, and print the spoiled bottle's number.

Input/Output

This is an interactive problem (a type of problem where your program interacts with the judge program through Standard Input and Output).
Before the interaction, the judge secretly selects an integer X between 1 and N as the spoiled bottle's number. The value of X is not given to you. Also, the value of X may change during the interaction as long as it is consistent with the constraints and previous outputs.
First, the judge will give you N as input.
N

You should print the number of friends to call, M, followed by a newline.
M

Next, you should perform the following procedure to print M outputs.
For i = 1, 2, \ldots, M, the i-th output should contain the num
[… cut at 1,500 characters]
```

</details>

**Diagnosis (wrong gold):** An interactive problem (the program must talk to a judge). The stored stdin/stdout tests cannot judge it, so no answer can pass; Qwen's programs answered with fixed outputs.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | no answer (reject) → import sys def main(): n = int(sys.stdin… (accept) | import sys def main(): n = int(sys.stdin.readline().strip()) # Find minimum M such that 2^M >= n m = 0 while (1 << m) < n: m += 1 # Print M print(m) sys.stdout.… |
| Tools | import sys import math def solve(): n = … (accept) | import sys import math def solve(): n = int(sys.stdin.readline().strip()) # Minimum number of friends: ceil(log2(n)) if n == 1: m = 0 else: m = math.ceil(math.l… |
| Deep | no answer (reject) → import sys try: import select except Exc… (accept) | import sys try: import select except Exception: select = None def bottles_for(n, m, i): bit = m - 1 - i if n == 2: if bit == 0: return [1] return [] return [b f… |
| Deep+Tools | import sys def main(): def tokens(): for… (accept) | import sys def main(): def tokens(): for line in sys.stdin: for tok in line.split(): yield tok it = tokens() try: n_tok = next(it) except StopIteration: return … |
| Vote | import sys def main(): line = sys.stdin.… (accept) | import sys def main(): line = sys.stdin.readline() if not line: return parts = line.strip().split() if not parts: return n = int(parts[0]) extra = parts[1:] m =… |
| Vote+Tools | import sys def main(): line = sys.stdin.… (accept) | import sys def main(): line = sys.stdin.readline() if not line: return parts = line.split() if not parts: return N = int(parts[0]) pending = parts[1:] if N <= 1… |

### mmlupro-2879 · science_mc · gold: F

<details open><summary>Question</summary>

```text
In a simple ecosystem there exists a field of clover. Mice eat theclover and skunks eat the mice. The skunks are in turn eatenby wolves. According to the ten percent rule of ecologicalefficiency, how much energy would a wolf receive fromthe original clover plants?

A. 0.01 calories
B. 5 calories
C. 100 calories
D. 0.1 calories
E. 50 calories
F. 10 calories
G. 1,000 calories
H. 500 calories
I. 25 calories
J. 1 calorie
```

</details>

**Diagnosis (wrong gold):** The question never says how much energy the clover holds. Clover to mice to skunks to wolves is three 10% steps, so the wolf gets 0.1% of it. The gold 10 calories assumes 10,000 calories; every route assumed 1,000 and answered J (1 calorie). The item cannot be answered from its text.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | J (accept) | J |
| Tools | J (accept) | J |
| Deep | J (accept) | J |
| Deep+Tools | J (accept) | J |
| Vote | J (accept) | J |
| Vote+Tools | J (accept) | J |

### mmlupro-3700 · science_mc · gold: B

<details open><summary>Question</summary>

```text
Consider a kinetic experiment in which the chemical re-action is accompanied by a temperature change. Using the Heisenberg uncertainty principle, calculate the uncertainty in a simultaneous measurement of time and temperature.

A. ∆T ∆t ≤ h/4π
B. ∆T ∆t \geq h/c
C. ∆T ∆t = h^2/c^2
D. ∆T ∆t = h/c
E. ∆T ∆t \geq 2πh
F. ∆T ∆t \geq h^2/c
G. ∆T ∆t ≤ h/c
H. ∆T ∆t \geq hc
I. ∆T ∆t \geq h/4π
J. ∆T ∆t = kT^2
```

</details>

**Diagnosis (wrong gold):** With E = kT, Heisenberg gives dT dt >= h/(4 pi k); no option has the k. The gold B, h/c, has the wrong units (h/c is not energy x time / temperature). Every route picked I (h/4 pi), the closest form. The item is broken.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | I (accept) | I |
| Tools | I (accept) | I |
| Deep | I (accept) | I |
| Deep+Tools | I (accept) | I |
| Vote | I (accept) | I |
| Vote+Tools | I (accept) | I |

### mmlupro-9344 · science_mc · gold: I

<details open><summary>Question</summary>

```text
A spherical light bulb 2 inches in diameter is imaged by a steel ball bearing located 20 inches away from the bulb. If the ball bearing is 1inch in diameter, where is the image of the light bulb and what is its diameter?

A. 0.1 inches in diameter, located at a distance of 0.49 in. beneath the surface of the ball bearing
B. 0.1 inches in diameter, located at a distance of 10 inches away from the ball bearing
C. 0.05 inches in diameter, located at a distance of 2 in. above the surface of the ball bearing
D. 2 inches in diameter, located at the same position as the light bulb
E. 0.05 inches in diameter, located at a distance of 1 in. beneath the surface of the ball bearing
F. 0.1 inches in diameter, located at a distance of 1 in. above the surface of the ball bearing
G. 1 inch in diameter, located at a distance of 20 inches away from the ball bearing
H. 0.05 inches in diameter, located at a distance of 0.49 in. above the surface of the ball bearing
I. 0.05 inches in diameter, located at a distance of 0.49 in. beneath the surface of the ball bearing
J. 0.025 inches in diameter, located at a distance of 0.25 in. beneath the surface of the ball bearing
```

</details>

**Diagnosis (wrong gold):** A 1-inch ball is a convex mirror with radius 0.5 in and focal length 0.25 in. An object 20 in away images 0.247 in behind the surface, magnification 0.0123, so the 2-inch bulb's image is about 0.025 in: option J, every route's answer. The gold I (0.05 in, 0.49 in) uses the diameter as the radius.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | J (accept) | J |
| Tools | J (accept) | J |
| Deep | J (accept) | J |
| Deep+Tools | J (accept) | J |
| Vote | J (accept) | J |
| Vote+Tools | J (accept) | J |

### mmlupro-9752 · science_mc · gold: A

<details open><summary>Question</summary>

```text
From the indices of refraction given below, calculate the rotation of the plane of polarization for violet light \lambda = 396.0 nm, in a quartz plate cut perpendicular to the optic axis and 1 mm thick. [\lambda / (396.0 nm)] [n_R/ (1.55610)] [n_L/ (1.55821)] (Refractive Indices for Quartz)

A. 50 degrees
B. 90 degrees
C. 45 degrees
D. 30 degrees
E. 120 degrees
F. 150 degrees
G. 75 degrees
H. 60 degrees
I. 135 degrees
J. 100 degrees
```

</details>

**Diagnosis (wrong gold):** Rotation = pi d (n_L - n_R) / lambda = pi x 1 mm x 0.00211 / 396 nm = 16.7 rad = 959 degrees, which is 59 degrees modulo 180: option H (60), the answer of five routes (Vote answered E). The gold A (50 degrees) does not follow from the given indices.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | H (accept) | H |
| Tools | H (accept) | H |
| Deep | H (accept) | H |
| Deep+Tools | H (accept) | H |
| Vote | E (accept) | E |
| Vote+Tools | H (accept) | H |

## Model wrong (6)

### aime-2002-II-4 · math · gold: 803

<details open><summary>Question</summary>

```text
Patio blocks that are hexagons $1$ unit on a side are used to outline a garden by placing the blocks edge to edge with $n$ on each side. The diagram indicates the path of blocks around the garden when $n=5$ . AIME 2002 II Problem 4.gif If $n=202$ , then the area of the garden enclosed by the path, not including the path itself, is $m\left(\sqrt3/2\right)$ square units, where $m$ is a positive integer. Find the remainder when $m$ is divided by $1000$ .
```

</details>

**Diagnosis (model wrong):** Answers 627, 412, 601, 421 and 203 (Deep and Vote hit the 32,768-token cap); gold 803. Deep+Tools even claimed 601 is the official answer. Qwen is wrong.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | 627 (accept) | 627 |
| Tools | no answer (reject) → 412 (accept) | 412 |
| Deep | no answer (reject) → no answer (reject) | no answer |
| Deep+Tools | 601 (accept) | 601 |
| Vote | 203 (accept) | 203 |
| Vote+Tools | 421 (accept) | 421 |

### gsm8k-train-5520 · math · gold: 2100

<details open><summary>Question</summary>

```text
John's new computer cost $1500.  He needs to get a monitor and other peripherals that cost 1/5 that much.  He also wants to upgrade the $300 video card in the base computer with one that costs twice as much.  How much did he spend?
```

</details>

**Diagnosis (model wrong):** All routes answered 2400 = 1500 + 300 + 600, counting the old $300 card as a purchase. Gold 2100 = 1500 + 300 + (600 - 300): the upgrade costs the difference. Qwen is wrong.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | 2400 (accept) | 2400 |
| Tools | 2400 (accept) | 2400 |
| Deep | 2400 (accept) | 2400 |
| Deep+Tools | 2400 (accept) | 2400 |
| Vote | 2400 (accept) | 2400 |
| Vote+Tools | 2400 (accept) | 2400 |

### mmlupro-3035 · science_mc · gold: F

<details open><summary>Question</summary>

```text
A biology student from Nebraska, vacationing at a Virginia beach, observes that the level of activity of a fiddler crab changes with the cycle of the tides. When he brings some crabs back with him to Nebraska, he notices that a similar activity cycle is shown, yet there are no ocean beaches for miles. Explain.

A. The level of activity is influenced by the ocean tides only
B. The activity cycle is a genetic trait that persists regardless of the crabs' habitat
C. The crabs' internal biological clocks are set to the tidal patterns they experienced in Virginia and continue on the same cycle
D. Changes in barometric pressure in Nebraska are influencing the crabs' activity levels
E. The level of activity is regulated by the crab's diet
F. The crucial determinant of the level of activity of the crab is not the presence of the tides, but the gravitational pull of the moon
G. The crabs are responding to the light cycles of day and night rather than the tides
H. The crabs have adapted to a freshwater rhythmic cycle that mimics ocean tides
I. The crabs are maintaining their Virginia activity schedule out of habit
J. The level of activity is being influenced by the temperature fluctuations in their new environment
```

</details>

**Diagnosis (model wrong):** Every route answered C on the first try and the verifier accepted it; gold is F. Qwen is wrong.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | C (accept) | C |
| Tools | C (accept) | C |
| Deep | C (accept) | C |
| Deep+Tools | C (accept) | C |
| Vote | C (accept) | C |
| Vote+Tools | C (accept) | C |

### mmlupro-3282 · science_mc · gold: D

<details open><summary>Question</summary>

```text
Both Mr. and Mrs. Brown suffer from anautosomalrecessive condition that makes them anemic. Mr. Brown has one amino acid substitution in the \beta-chain of his hemoglobin molecules and Mrs. Brown has a similar defect in her \alpha-chain. Neither Betsy norBoopsy, their children, are anemic. Explain.

A. Only one parent can pass the disorder to the children
B. Both parents will definitely pass the disorder to their children
C. Both children inherited a different form of anemia that is not detectable at their current age.
D. Both parents have a homozygous trait but may or may not pass the disorder to their children
E. The children cannot be carriers since they are not anemic.
F. The children have a 50% chance of being carriers and a 25% chance of being affected.
G. The disorder can only be inherited from the mother.
H. Neither of the parents can pass the disorder to their children
I. The children are anemic but show no symptoms due to a modifier gene.
J. Each child will inherit the disorder, but it will remain dormant until adulthood.
```

</details>

**Diagnosis (model wrong):** Each parent is homozygous for a defect in a different gene (beta and alpha chain), so each child gets one bad copy of each gene and is a carrier, not anemic. The gold D (homozygous, may or may not pass the disorder) fits; every route answered B (both will definitely pass the disorder), which contradicts the healthy children.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | B (accept) | B |
| Tools | B (accept) | B |
| Deep | B (accept) | B |
| Deep+Tools | B (accept) | B |
| Vote | B (accept) | B |
| Vote+Tools | B (accept) | B |

### mmlupro-7767 · science_mc · gold: F

<details open><summary>Question</summary>

```text
Does the following series $\sum_{i=0}^{\infty} \frac{n^2 ln(n)}{n!}$ converge?

A. It oscillates between values and does not settle
B. 2.0
C. -0.5
D. It converges to e (Euler's number)
E. -1.0
F. 1.0
G. It diverges to infinity
H. 0.0
I. It does not converge
J. It converges conditionally, not absolutely
```

</details>

**Diagnosis (model wrong):** Tools, Deep, Vote and Vote+Tools answered D, Fast answered I, gold is F. Qwen is wrong; Deep+Tools and Vote+Tools also hit the token cap once.

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | D (accept) | D |
| Tools | D (accept) | D |
| Deep | D (accept) | D |
| Deep+Tools | D (accept) | D |
| Vote | D (accept) | D |
| Vote+Tools | D (accept) | D |

### rlvrif-5343 · instruction · gold: no gold answer: graded by the instruction checker

<details open><summary>Question</summary>

```text
At the end of your response, please explicitly add a postscript starting with Before I forget: Calculate the sum of the first 100 positive integers and explain the process in 4 sentences
```

</details>

**Diagnosis (model wrong):** Asks for a postscript starting with 'Before I forget:' at the end. Deep and Vote put 'Before I forget:' at the very start, the others left it out. Qwen did not follow the rule (the checker's P.S.-only bug also applies, but no answer would pass a correct check).

| Route | First answer → verdict | Final answer |
|---|---|---|
| Fast | no answer (reject) → 5050 (reject) | 5050 |
| Tools | 5050 (reject) → 5050 (reject) | 5050 |
| Deep | 5050 (reject) → Before I forget: We identify the first 1… (reject) | Before I forget: We identify the first 100 positive integers as 1 through 100. We use the formula n(n+1)/2 for the sum of the first n positive integers. Substit… |
| Deep+Tools | 5050 (reject) → 5050 (reject) | 5050 |
| Vote | Before I forget: The sum of the first 10… (reject) → Before I forget: Calculate the sum of th… (reject) | Before I forget: Calculate the sum of the first 100 positive integers by pairing 1 with 100, 2 with 99, and so on. Each pair adds to 101, and there are 50 pairs… |
| Vote+Tools | 5050 (reject) → 5050 (reject) | 5050 |

