import os
from backend.config import PROJECT_ROOT

# Registry of bundled example gene sets that users can use to filter CpG sites
# instead of uploading their own gene list on the "Train your own gene set-specific
# aging clock" page. Add new entries here to expose more built-in gene sets in the UI.
EXAMPLE_GENESETS = {
    "genage_human_aging_genes": {
        "label": "GenAge human ageing-related genes (307 genes)",
        "description": (
            "Curated list of 307 human genes associated with ageing from the GenAge "
            "database (Human Ageing Genomic Resources, Build 21, Tacutu et al. 2018, "
            "Nucleic Acids Research). A ready-made gene set to try out gene "
            "set-specific clock training without uploading your own list."
        ),
        "genes_path": os.path.join(PROJECT_ROOT, "backend/data/example_genesets/genage_human_aging_genes.csv"),
    },
}


def list_example_genesets():
    """Returns the id -> {label, description} mapping for UI display."""
    return {
        geneset_id: {"label": info["label"], "description": info["description"]}
        for geneset_id, info in EXAMPLE_GENESETS.items()
    }


def get_example_geneset_path(geneset_id: str):
    """Returns the file path for a bundled example gene set id."""
    if geneset_id not in EXAMPLE_GENESETS:
        raise ValueError(f"Unknown example gene set: {geneset_id}")
    return EXAMPLE_GENESETS[geneset_id]["genes_path"]
