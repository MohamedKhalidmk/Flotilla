import glob, json
from collections import Counter
from pathlib import Path
import pyarrow.parquet as pq
from my_method.graph_store import GraphStore, entity_id
labels = json.loads(Path("my_method/wikidata_property_labels.json").read_text())
d = GraphStore.load("results/checkpoints/shared_graphs/real_mh_262k_empty_start.json")
de = set(d.entities())
names, rel_names, n_all, n_rel = set(), set(), 0, 0
for f in sorted(glob.glob(str(Path.home() / "scratch/sgar/trex/*.parquet"))):
    t = pq.read_table(f, columns=["relation", "head", "tail"]).to_pydict()
    for r, h, tl in zip(t["relation"], t["head"], t["tail"]):
        n_all += 1
        e1, e2 = entity_id(h), entity_id(tl)
        names.add(e1); names.add(e2)
        if r in labels:
            n_rel += 1
            rel_names.add(e1); rel_names.add(e2)
print(f"T-REx triples {n_all:,} (on the 45 common properties: {n_rel:,}) | entities {len(names):,} (on those properties: {len(rel_names):,})")
print(f"document entities {len(de):,} | exact overlap, all of T-REx: {len(de & names):,} ({100*len(de & names)/len(de):.1f}%) | 45 properties only: {len(de & rel_names):,} ({100*len(de & rel_names)/len(de):.1f}%)")
