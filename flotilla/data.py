"""Load datasets from the local Hugging Face download (compute nodes are offline).

`datasets.load_dataset("org/name")` asks the Hub even when the files were downloaded with
snapshot_download, and fails in offline mode. Loading the local snapshot folder works offline.
"""
from datasets import load_dataset
from huggingface_hub import snapshot_download


def local_path(repo: str) -> str:
    return snapshot_download(repo, repo_type="dataset", local_files_only=True)


def load(repo: str, config: str | None = None, split: str | None = None):
    return load_dataset(local_path(repo), name=config, split=split)
