"""test-04 LongMemEval judge check: a seeded random sample of judge verdicts, printed with the question, the gold answer,
the route's answer and the judge's verdict, for checking by hand against the gold (the brief: 50 verdicts, stop below
90% agreement). The hand verdicts are written next to the sample as a JSON file and the agreement is computed from it.

    python experiments/test-04-strategy-router/judge_check.py sample --items LME.jsonl --verdicts V.jsonl --out S.jsonl [--n 50]
    python experiments/test-04-strategy-router/judge_check.py agree --sample S.jsonl --hand HAND.json
HAND.json: {"<item_id>|<route>": true/false, ...} (true = the answer is right by the gold, the official rubric applied).
"""
import argparse
import json
import random

SEED = 20261121


def sample(a) -> None:
    items = {json.loads(l)["item_id"]: json.loads(l) for l in open(a.items)}
    rows = [json.loads(l) for l in open(a.verdicts)]
    rng = random.Random(SEED)
    pick = rng.sample(rows, min(a.n, len(rows)))
    with open(a.out, "w") as f:
        for v in pick:
            it = items[v["item_id"]]
            f.write(json.dumps({"key": f"{v['item_id']}|{v['route']}", "question_type": it["question_type"],
                                "abstention": it.get("abstention"), "question": it["question"], "gold": it["answer"],
                                "answer": v.get("answer"), "judge_correct": v["correct"], "judge_reply": v.get("judge_reply")},
                               ensure_ascii=False) + "\n")
    print(f"{len(pick)} verdicts -> {a.out}")


def agree(a) -> None:
    rows = [json.loads(l) for l in open(a.sample)]
    hand = json.load(open(a.hand))
    missing = [r["key"] for r in rows if r["key"] not in hand]
    if missing:
        raise SystemExit(f"{len(missing)} sampled verdicts have no hand verdict, e.g. {missing[:3]}")
    same = [r for r in rows if bool(hand[r["key"]]) == bool(r["judge_correct"])]
    diff = [r for r in rows if r not in same]
    out = {"n": len(rows), "agree": len(same), "agreement": round(len(same) / len(rows), 4),
           "judge_yes_hand_no": [r["key"] for r in diff if r["judge_correct"]],
           "judge_no_hand_yes": [r["key"] for r in diff if not r["judge_correct"]]}
    print(json.dumps(out, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--items", required=True)
    s.add_argument("--verdicts", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--n", type=int, default=50)
    g = sub.add_parser("agree")
    g.add_argument("--sample", required=True)
    g.add_argument("--hand", required=True)
    a = ap.parse_args()
    {"sample": sample, "agree": agree}[a.cmd](a)


if __name__ == "__main__":
    main()
