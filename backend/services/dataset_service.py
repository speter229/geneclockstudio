import pandas as pd
import os
import gc
from backend.config import PROJECT_ROOT  # Import PROJECT_ROOT

# Gives the dataset information for the given dataset name
def get_dataset_info(dataset_name: str):
    try:
        if dataset_name == "GSE40279":
            dataset_path = os.path.join(PROJECT_ROOT, "backend/data/gse40279_meta.csv")
            df = pd.read_csv(dataset_path)
            df.index = ['age', 'tissue', 'geo_accession']
            age_values = df.loc['age'].astype(float).tolist()
            result = {
                "description": hannum_description,
                "trained_clocks": hannum_clocks,
                "study_description_1": hannum_reprogramming_description,
                "study_description_2": hannum_cancer_description,
                "study_description_3": hannum_boxplot_description,
                "metadata": df.iloc[:3, :20].to_dict(),
                "ages": age_values,
                "study_scatterplot_1": hannum_rejuvenation,
                "study_scatterplot_2": hannum_cancer_plot_scatterplot,
                "study_boxplot_1": hannum_cancer_boxplot
            }
            del df  # Free memory
            gc.collect()  # Force garbage collection
            return result
        elif dataset_name == "Computage":
            dataset_path = os.path.join(PROJECT_ROOT, "backend/data/computage_train_meta.csv")
            df = pd.read_csv(dataset_path, sep=',', index_col=0)
            age_values = df.loc['Age'].astype(float).tolist()
            result = {
                "trained_clocks": computage_clocks,
                "description": computage_description,
                "study_description_1": computage_disease_description,
                "study_description_2": computage_boxplot_description,
                "metadata": df.iloc[:8, :20].to_dict(),
                "ages": age_values,
                "study_scatterplot_1": computage_disease_scatterplot,
                "study_boxplot_1": computage_disease_boxplot
            }
            del df  # Free memory
            gc.collect()  # Force garbage collection
            return result
        elif dataset_name == "AltumAge":
            dataset_path = os.path.join(PROJECT_ROOT, "backend/data/altumAge450k_meta.csv")
            df = pd.read_csv(dataset_path, sep=',', index_col=0)
            age_values = df.loc['age'].astype(float).tolist()
            result = {
                "trained_clocks": altumAge_clocks,
                "description": atlumage_description,
                "metadata": df.iloc[:5, :20].to_dict(),
                "ages": age_values
            }
            del df
            gc.collect()
            return result
        else:
            raise ValueError("Dataset not found.")
    except Exception as e:
        raise ValueError(f"❌ Error processing dataset {dataset_name}: {e}")

hannum_description = (
    "The GSE40279 accession data is a widely used methylation data for model training.\n"
    "It contains 656 blood samples, measured with illumina450k (so each sample has about 480k features.)."
    "It is accessible from the GEO database, with this link: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE40279\n"
)

atlumage_description = """
    The altumAge dataset is a public dataset from GitHub, which I have modified since the original dataset had 27k features, and I needed way more.
    So I merged a dataset from the datasets that were measured on the illumina450k.
    My merged and filtered altumAge450k multi-tissue dataset has 433 samples.
    The dataset includes information about whether the person had cancer or not.\n
    Dataset detailed description and tutorial: https://github.com/rsinghlab/AltumAge?tab=readme-ov-file\n
    Tissue distribution in this dataset:
  - Breast: 70
  - Pancreas: 196
  - Nasopharyngeal: 48
  - Kidney: 71
  - Colon: 45
  - Liver: 3
"""

computage_description = (
    "This is a public dataset from Hugging Face.\n"
    "Dataset detailed description and tutorial for usage: https://huggingface.co/datasets/computage/computage_bench \n"
    "The interesting part is that it contains disease information, so we could measure if certain diseases affect the biological age prediction.\n"
    "The data used for training (healthy samples) contains about 7,000 blood samples\n"
    "The data used for testing contains about 10,000 samples."
)

hannum_clocks = ("Blood_inflammatory_clock_1\n")

computage_clocks = ("Blood_inflammatory_clock_2\n"
"\nBlood_inflammatory_clock_XGBoost\n")
altumAge_clocks = ("Multi_tissue_inflammatory_clock\n")

hannum_reprogramming_description = (
    "The 'Blood inflammatory clok 1' was trained on the GSE40279 datasets, specifically on the CpG sites located on the ISig genes group,"
    " achieving an MAE of 6.84 and a Pearson r of 0.85 accuracy. This clock was applied to data where genes were rejuvenated. "
    "The dataset used in this study can be found here: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE54848"
    )

hannum_cancer_description = (
    "CONTROL: Samples taken from healthy individuals with no known disease.\n"
    "DISEASE TISSUE: The actual cancerous tissue from the tumor.\n"
    "ADJACENT NORMAL: Tissue collected from the same patient as the tumor, but from an area near the tumor that appears histologically normal.\n\n"
    "This is the age predictions of the Hannum clock (red points are the disease tissue prediction, yellow is the adjacent normal, and green are the healthy control samples)."
)

hannum_rejuvenation = "backend/data/hannum_rejuvenation.png"

hannum_cancer_plot_scatterplot = "backend/data/hannum_cancer_scatterplot.png"
hannum_cancer_boxplot = "backend/data/hannum_cancer_boxplot.png"

computage_disease_description = (
    "I trained the Blood inflammatory clock 2 on 7000 healthy samples. The models evaluation on test set is, MAE=5.9 r=0.94. Then I used it for age prediction on diseased samples.\n\n"
    "These disease groups names that appear in the dataset:\n\n"
    "Immune system diseases (ISD):\n\n"
    "Kidney diseases (KD):\n\n"
    "Liver diseases (LD):\n\n"
    "Metabolic diseases (MBD):\n\n"
    "Muscolosceletal diseases (MSD):\n\n"
    "Neurodegenerative diseases (NDD):\n\n"
    "Respiratory diseases (RSD):\n\n"
    "Progeroid syndromes (PGS):\n\n"
    "Healthy control (HC):\n\n"
)
computage_disease_scatterplot = "backend/data/computage_disease_scatterplot.png"
computage_disease_boxplot = "backend/data/computage_disease_boxplot.png"
hannum_boxplot_description = "The age acceleration of the 3 groups (healthy control, adjacent normal, and disease tissue). The healthy samples age accleration is significantly lower than the disease tissue samples, and the adjacent normal samples."
computage_boxplot_description = "The age acceleration of the disease groups."