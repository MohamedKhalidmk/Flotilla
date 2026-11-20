"""test-05 table: GRAFT with a base graph under the documents, from runs/run-01/{overlap,graft_runs,base_graph_reports}.
Rows still running carry status "running" and empty result cells (filled from a later run, never by hand)."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _common import write_table

R = HERE / "runs" / "run-01"
R2 = HERE / "runs" / "run-02"  # RoG Haiku-linking result, full T-REx base build report (run-01 stays as it was)
def summ(prefix: str) -> dict:
    return json.loads(sorted((R / "graft_runs").glob(prefix + "_2*"))[-1].joinpath("summary.json").read_text())
c_real, d_real = summ("exp_c_real_mh_262k_ans256"), summ("exp_d_extend_real_mh_262k_ans256")
c_free = summ("exp_c_fake_mh_262k_base_eig")
def summ2(prefix: str) -> dict:
    return json.loads(sorted((R2 / "graft_runs").glob(prefix + "_2*"))[-1].joinpath("summary.json").read_text())
rog_real, rog_free = summ2("exp_c_real_mh_262k_ans256_rog_link_build_eig"), summ2("exp_c_fake_mh_262k_rog_link_eig")
lk = rog_real["build_info"]["writer"]["linking"]
rog_link = round(lk["matched_base"] / (lk["matched_base"] + lk["new"] + lk["new_no_reply"]), 4)
full_kept = json.loads((R2 / "base_graph_reports" / "trex_full_base.json.report.json").read_text())["kept"]
ov = {k: json.loads((R / "overlap" / f"{k}.json").read_text()) for k in ("rog_base", "trex_base")}
txt = (R / "overlap" / "trex_full_exact_overlap.txt").read_text()
full_facts = int(re.search(r"on the 45 common properties: ([\d,]+)\)", txt).group(1).replace(",", ""))
full_ents = int(re.search(r"on those properties: ([\d,]+)\)", txt).group(1).replace(",", ""))
full_share = float(re.search(r"45 properties only: [\d,]+ \(([\d.]+)%\)", txt).group(1)) / 100
acc = lambda s: s["accuracy"]["mh"]["mean"] / 100
gold = lambda s: s["answer_in_retrieved"]["mh"]
rows = [
    {"variant": "Mode C, empty start (baseline; gold: EiG free check, accuracy: GOAt real run)", "base_source": "none", "base_facts": 0, "doc_entities_exact_overlap": None,
     "haiku_link_share": None, "gold_in_final_facts_free": gold(c_free), "accuracy_real": acc(c_real), "status": "done"},
    {"variant": "Experiment D, synthetic start (Nov 13)", "base_source": "made-up world", "base_facts": 400,
     "doc_entities_exact_overlap": None, "haiku_link_share": None, "gold_in_final_facts_free": None,
     "gold_in_final_facts_real": gold(d_real), "accuracy_real": acc(d_real), "status": "done"},
    {"variant": "RoG base (Freebase, SubgraphRAG sets)", "base_source": "RoG-WebQSP/CWQ", "base_facts": ov["rog_base"]["base_facts"],
     "doc_entities_exact_overlap": ov["rog_base"]["doc_entities_shared_share"], "haiku_link_share": rog_link,
     "gold_in_final_facts_free": gold(rog_free), "gold_in_final_facts_real": gold(rog_real), "accuracy_real": acc(rog_real),
     "status": "done (run-02): not adopted"},
    {"variant": "T-REx core (most-linked entities)", "base_source": "Wikidata via T-REx", "base_facts": ov["trex_base"]["base_facts"],
     "doc_entities_exact_overlap": ov["trex_base"]["doc_entities_shared_share"], "haiku_link_share": None,
     "gold_in_final_facts_free": None, "accuracy_real": None, "status": "not built further (overlap too low)"},
    {"variant": "T-REx full (45 common properties)", "base_source": "Wikidata via T-REx", "base_facts": full_kept,
     "doc_entities_exact_overlap": round(full_share, 4), "haiku_link_share": None, "gold_in_final_facts_free": None,
     "accuracy_real": None, "status": "base built (run-02); Haiku-linking build + 3 repeats running"},
]
for r in rows:
    r.setdefault("gold_in_final_facts_real", None)
cols = ["variant", "base_source", "base_facts", "doc_entities_exact_overlap", "haiku_link_share", "gold_in_final_facts_free",
        "gold_in_final_facts_real", "accuracy_real", "status"]
write_table(HERE, "table", [{c: r[c] for c in cols} for r in rows],
            "GRAFT on FactConsolidation MH 262K (100 questions), mode C, Haiku 5.5 answers. Overlap = share of the documents' "
            "entities that already exist in the base graph by exact name.")
print("ok", full_facts, full_ents)
