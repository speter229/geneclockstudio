import pandas as pd
try:
    import torch
    from torch.utils.data import Dataset
except Exception:
    # Allow the module to be imported in environments without torch (tests, minimal CI)
    torch = None

    class Dataset:
        """Minimal fallback Dataset base class for environments without torch.

        This provides the minimal interface used by MethylationDataset so the
        module can be imported and functions that don't require torch will work.
        """
        def __len__(self):
            raise NotImplementedError()

        def __getitem__(self, idx):
            raise NotImplementedError()
from sklearn.model_selection import train_test_split
import numpy as np
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import cross_val_score
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
try:
    from xgboost import XGBRegressor
except Exception:
    XGBRegressor = None
import os
from backend.config import PROJECT_ROOT

def cg_selection(UPLOADED_GENE: pd.DataFrame, promoter_only: bool) -> list:
    """
    Filters CpG sites based on the provided gene list and optionally restricts to promoter regions.
    Returns a list of (gene, cpg) pairs.

    Args:
        UPLOADED_GENE (pd.DataFrame): A DataFrame with one column named 'Gene_ID'.
        promoter_only (bool): If True, restricts the selection to promoter regions.

    Returns:
        list: A list of tuples, each containing a gene and its corresponding CpG site.
    """
    # Load the probe table
    probe_table_path = os.path.join(PROJECT_ROOT, "backend/data/Illumina_cg_data.csv")
    probe_table = pd.read_csv(probe_table_path, index_col=0)

    # Create a set of selected genes from the 'Gene_ID' column
    selected_genes_set = set(UPLOADED_GENE['Gene_ID'])

    # If promoter_only is True, filter for promoter regions
    if promoter_only:
        probe_table = probe_table[
            probe_table['UCSC_RefGene_Group']
            .astype(str)  # Convert to string
            .str.contains('TSS1500|TSS200|5\'UTR|1stExon', case=False, na=False)
        ]

    # Filter CpG sites based on the selected genes
    filtered_cgs = probe_table[
        probe_table['UCSC_RefGene_Name'].apply(
            lambda x: any(gene in selected_genes_set for gene in str(x).split(';'))
        )
    ]

    # Create a list of (gene, cpg) pairs
    gene_cpg_pairs = []
    for cpg, row in filtered_cgs.iterrows():
        genes = str(row['UCSC_RefGene_Name']).split(';')  # Split multiple genes
        for gene in genes:
            if gene in selected_genes_set:
                gene_cpg_pairs.append((gene, cpg))

    return gene_cpg_pairs

def prepocess_before_training(df_betas: pd.DataFrame,df_meta: pd.DataFrame):
    """
    Preprocesses the beta and metadata tables before training.

    Args:
        df_betas (pd.DataFrame): Beta values DataFrame.
        df_meta (pd.DataFrame): Metadata DataFrame.

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Preprocessed beta and metadata DataFrames.
    """
    # Calculate thresholds for dropping rows and columns
    col_threshold = df_betas.shape[0] * 0.5  # 50% of the number of rows
    row_threshold = df_betas.shape[1] * 0.5  # 50% of the number of columns
    # Drop cols with more than 50% missing values
    df_betas = df_betas.loc[:, df_betas.isnull().sum() <= col_threshold]
    # Drop rows with more than 50% missing values
    df_betas = df_betas.loc[df_betas.isnull().sum(axis=1) <= row_threshold]
    #fill nan values with means
    df_betas=df_betas.fillna(df_betas.mean())
    #the raw and meta dfs have to be in the same column order
    df_meta = df_meta[list(df_betas.columns)]
    return df_betas, df_meta

def check_dataframes(df_betas: pd.DataFrame, df_meta: pd.DataFrame) -> bool:
    """
    Validates the integrity and compatibility of the beta and metadata DataFrames.

    Args:
        df_betas (pd.DataFrame): Beta values DataFrame containing CpG site values as rows and samples as columns.
        df_meta (pd.DataFrame): Metadata DataFrame containing sample information, including an 'Age' row.

    Returns:
        bool: True if all validation checks pass successfully.

    Raises:
        ValueError: If any of the following conditions are not met:
            - All values in df_betas must be of type float.
            - Both DataFrames must have at least 20 columns (samples).
            - df_betas must have at least 20 rows (CpG sites).
            - The column names of df_betas and df_meta must match exactly.
            - The 'Age' row must exist in df_meta, contain only numeric values, and have no missing values.
    """
    if not all(df_betas.dtypes == float):
        raise ValueError("All values in the DataFrame must be float.")

    # Check if the training data has too few columns
    if df_betas.shape[1] < 20 or df_meta.shape[1] < 20:
        raise ValueError("Too few samples in the training data. At least 20 samples are required.")

    # Check if the training data has too few rows
    if df_betas.shape[0] < 20:
        raise ValueError("Too few cg sites. At least 20 cg sites are required.")
    
    # Ensure df_betas and df_meta have matching colnames
    if not df_betas.columns.equals(df_meta.columns):
        raise ValueError("The columns of betas dataframe must match the columns of metas dataframe.")

    # Check if 'Age' row exists (case-insensitive)
    if 'age' in df_meta.index.str.lower():
        age_row_index = df_meta.index.str.lower().get_loc('age')
        age_row = df_meta.iloc[age_row_index]
        age_row = age_row.astype(float)  # Ensure the row is float type

        # Check if all values in the 'Age' row are floats
        if not np.issubdtype(age_row.dtype, np.number):
            raise ValueError("The 'Age' row in meta_table must contain only float values.")

        # Check for missing values or NaNs in the 'Age' row
        if age_row.isnull().any():
            raise ValueError("The 'Age' row in meta_table contains missing values or NaNs.")
    else:
        raise ValueError("'Age' row not found in meta_table.")
    
    return True

def validate_gene_dataframe(df: pd.DataFrame) -> bool:
    """
    Validates the gene dataframe.

    Args:
        df (pd.DataFrame): The gene dataframe to validate.

    Returns:
        bool: True if validation passes.

    Raises:
        ValueError: If the dataframe does not contain exactly one column
                    or if the column name is not 'Gene_ID'.
    """
    if df.shape[1] != 1:
        raise ValueError(f"Gene dataframe must contain exactly one column, but found {df.shape[1]} columns.")
    if df.columns[0] != "Gene_ID":
        raise ValueError(f"Gene dataframe column name must be 'Gene_ID', but found '{df.columns[0]}'")
    return True

class MethylationDataset(Dataset):
    def __init__(self, meta_table, raw_table, transform=None):
        self.meta_table = meta_table
        self.raw_table = raw_table
        
        # Check if 'Age' row exists (case-insensitive)
        if 'age' in self.meta_table.index.str.lower():
            self.age_row_index = self.meta_table.index.str.lower().get_loc('age')
            age_row = self.meta_table.iloc[self.age_row_index]
            age_row = age_row.astype(float)  # Ensure the row is float type
        else:
            raise ValueError("'Age' row not found in meta_table.")

    def __len__(self):
        return self.raw_table.shape[1]

    def __getitem__(self, idx):
        # Ensure the index is within the bounds of the meta_table
        if idx >= self.__len__():
            return -1

        # Extract the RNA data and age
        try:
            methylation_data = self.raw_table.iloc[:, idx].tolist()
            age=float(self.meta_table.iloc[self.age_row_index,idx])
        except IndexError as e:
            raise IndexError(f"IndexError: {e}, idx: {idx}")
        return np.array(methylation_data), age
    
    def get_features_and_targets(self):
        features = []
        targets = []
        for idx in range(len(self)):
            methylation_data, age = self[idx]
            features.append(methylation_data.numpy())
            targets.append(age.numpy())
        return np.array(features), np.array(targets)

def train_elasticnet_model(X_train, y_train, cv=2, alpha=0.1, l1_ratio=0.5, max_iter=50000):
    """
    Train an ElasticNet model with mean imputation if necessary.

    This function ensures X_train/y_train are numpy arrays, checks for NaNs,
    and wraps an imputer + ElasticNet in a pipeline so cross-validation and
    fitting never receive NaN values.
    """
    # Convert to numpy arrays (ensure numeric dtype)
    X_train = np.array(X_train, dtype=float)
    y_train = np.array(y_train, dtype=float)

    # If there are NaNs in X_train, we'll impute them with column means using SimpleImputer.
    imputer = SimpleImputer(strategy="mean")

    # Create a pipeline: imputer -> ElasticNet
    elastic = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=max_iter)
    pipeline = Pipeline([("imputer", imputer), ("elasticnet", elastic)])

    # Check for NaNs and warn (pipeline will handle them during fit/cv)
    if np.isnan(X_train).any():
        # Keep the behaviour deterministic: imputer will replace NaNs by column means
        # but surface a clear log message for debugging
        print("Warning: NaNs detected in X_train. Applying mean imputation before training.")

    # Perform cross-validation on the pipeline
    cv_scores = cross_val_score(
        pipeline, X_train, y_train, cv=cv, scoring='neg_mean_absolute_error'
    )

    # Fit the pipeline on the full training data (imputer will transform X before fitting ElasticNet)
    pipeline.fit(X_train, y_train)

    # Return the trained pipeline (it contains the imputer and the trained ElasticNet)
    return pipeline

def train_xgboost_model(
    X_train, y_train, 
    learning_rate=0.1, max_depth=3, 
    n_estimators=100, subsample=1.0
):
    """
    Trains an XGBoost model with fixed hyperparameters.

    Args:
        X_train (np.ndarray or pd.DataFrame): Training features.
        y_train (np.ndarray or pd.Series): Training target values.
        learning_rate (float): Learning rate for XGBoost. Default is 0.1.
        max_depth (int): Maximum depth of a tree. Default is 3.
        n_estimators (int): Number of boosting rounds. Default is 100.
        subsample (float): Subsample ratio of the training instances. Default is 1.0.

    Returns:
        XGBRegressor: The trained XGBoost model.
    """
    # Ensure X_train/y_train are numpy arrays of float
    X_train = np.array(X_train, dtype=float)
    y_train = np.array(y_train, dtype=float)

    if XGBRegressor is None:
        raise ImportError("XGBoost is not installed in the environment. Install xgboost or choose another model.")

    # Build pipeline: impute missing values then train XGBoost
    imputer = SimpleImputer(strategy="mean")
    xgb = XGBRegressor(
        learning_rate=learning_rate,
        max_depth=max_depth,
        n_estimators=n_estimators,
        subsample=subsample,
        objective='reg:squarederror',  # Use squared error for regression
        random_state=42,
    )
    pipeline = Pipeline([("imputer", imputer), ("xgb", xgb)])

    pipeline.fit(X_train, y_train)
    return pipeline

def train_random_forest_model(
    X_train, y_train,
    n_estimators=100, max_depth=10,
    min_samples_split=2, min_samples_leaf=2,
    max_features="sqrt", bootstrap=True, random_state=42
):
    """
    Trains a Random Forest model with fixed hyperparameters.

    Args:
        X_train (np.ndarray or pd.DataFrame): Training features.
        y_train (np.ndarray or pd.Series): Training target values.
        n_estimators (int): Number of trees in the forest. Default is 100.
        max_depth (int): Maximum depth of each tree. Default is 10.
        min_samples_split (int): Minimum number of samples required to split an internal node. Default is 2.
        min_samples_leaf (int): Minimum number of samples required at a leaf node. Default is 2.
        max_features (str or int): Number of features to consider when looking for the best split. Default is 'sqrt'.
        bootstrap (bool): Whether bootstrap samples are used when building trees. Default is True.
        random_state (int): Random seed for reproducibility. Default is 42.

    Returns:
        RandomForestRegressor: The trained Random Forest model.
    """

    # Ensure X_train/y_train are numpy arrays of float
    X_train = np.array(X_train, dtype=float)
    y_train = np.array(y_train, dtype=float)

    # Create imputer + RandomForest pipeline to handle NaNs
    imputer = SimpleImputer(strategy="mean")
    rf = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
        min_samples_leaf=min_samples_leaf,
        max_features=max_features,
        bootstrap=bootstrap,
        random_state=random_state
    )
    pipeline = Pipeline([("imputer", imputer), ("randomforest", rf)])

    pipeline.fit(X_train, y_train)
    return pipeline