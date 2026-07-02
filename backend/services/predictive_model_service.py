import joblib
import pandas as pd
import numpy as np
import os
from backend.config import PROJECT_ROOT  # Import PROJECT_ROOT

def calculate_percent(clock_cpgs, table_cpgs):
    '''
    input: clock_cpgs - list of CpGs in the clock
           table_cpgs - list of CpGs in the uploaded table
    Calculate the percentage of CpGs of a clock that are in the uploaded table.
    '''
    clock_set = set(clock_cpgs)
    table_set = set(table_cpgs)
    if len(clock_set) == 0:
        return 0  # Return 0% if the clock CpGs set is empty
    common_elements = table_set.intersection(clock_set)
    return (len(common_elements) / len(clock_set)) * 100

def calculate_feature_coverage (index_list):
    """
    Process a list of indices and return percents (the covered CpG sites for each aging clock).
    """
    hannum_cg_order_path = os.path.join(PROJECT_ROOT, "backend/data/Hannum_Inflammation_elnet_nonzero_cpg_order.csv")
    hannum_cg_order = pd.read_csv(hannum_cg_order_path, index_col=0)
    list_hannum_cg_order = hannum_cg_order['cpg'].tolist()

    altumAge_cg_order_path = os.path.join(PROJECT_ROOT, "backend/data/altumAge450k_elnet_nonzero_cg_order.csv")
    altumAge_cg_order = pd.read_csv(altumAge_cg_order_path)
    list_altumAge_cg_order = altumAge_cg_order['cpg'].tolist()

    computage_elasticnet_cg_order_path = os.path.join(PROJECT_ROOT, "backend/data/computage_elnet_nonzero_cpg_order.csv")
    computage_elasticnet_cg_order = pd.read_csv(computage_elasticnet_cg_order_path)
    list_computage_elasticnet_cg_order = computage_elasticnet_cg_order['cpg'].tolist()

    computage_xgboost_cg_order_path = os.path.join(PROJECT_ROOT, "backend/data/inflamm_hugging_models_cg_order.csv")
    computage_xgboost_cg_order = pd.read_csv(computage_xgboost_cg_order_path)
    list_computage_xgboost_cg_order = computage_xgboost_cg_order['ID'].tolist()

    # Calculate the percentage of CpGs in the clock that are present in the given table
    result = [None] * 4

    result[0] = round(calculate_percent(list_hannum_cg_order, index_list), 2)
    result[1] = round(calculate_percent(list_altumAge_cg_order, index_list), 2)
    result[2] = round(calculate_percent(list_computage_elasticnet_cg_order, index_list), 2)
    result[3] = round(calculate_percent(list_computage_xgboost_cg_order, index_list), 2)

    return result

def reorder_df_for_model(cg_order_df, df_betas):
    '''
    Reorder the beta values to match the order of the model
    handles missing rows, values are filled with the mean of the row
    '''
    inflamm_cg_mean_path = os.path.join(PROJECT_ROOT, "backend/data/inflammation_cg_means.csv")
    inflamm_cg_mean = pd.read_csv(inflamm_cg_mean_path, index_col=0)
    #the featuers order has to be that of the model
    filtered_betas = df_betas[df_betas.index.isin(cg_order_df.index)]
    # fill missing values with mean
    filtered_betas = filtered_betas.fillna(inflamm_cg_mean['mean'])
    # add absent features (absent cpgs)
    absent_cpgs = list(set(cg_order_df.index) - set(filtered_betas.index))
    absent_cpgs = [cpg for cpg in absent_cpgs if cpg in inflamm_cg_mean.index]
    absent_cpgs_mean = inflamm_cg_mean.loc[absent_cpgs]
    N = df_betas.shape[1]
    repeated_means = pd.DataFrame(absent_cpgs_mean['mean'].values.repeat(N).reshape(-1, N), index=absent_cpgs_mean.index)
    repeated_means.columns = filtered_betas.columns
    betas_extended = pd.concat([filtered_betas, repeated_means])
    return betas_extended.reindex(cg_order_df.index)

def predict_biological_age(model_name: str, csv_df: pd.DataFrame) -> dict:
    """
    Predicts biological age using a specified aging clock model and input beta values.
    """
    betas = csv_df

    # Check if betas dataframe values are float
    if not all(betas.dtypes == float):
        raise ValueError("All values in the DataFrame must be float.")
    cg_order = pd.DataFrame()

    if model_name == "Blood inflammatory Clock 1":
        model_path = os.path.join(PROJECT_ROOT, "backend/models/aging_clocks/hannum_inflamm_elastic_model_1.pkl")
        model = joblib.load(model_path)
        cg_order_path = os.path.join(PROJECT_ROOT, "backend/data/hannum_elnet_cg_order.csv")
        cg_order = pd.read_csv(cg_order_path, index_col=0)
    elif model_name == "Multi-tissue inflammatory clock":
        model_path = os.path.join(PROJECT_ROOT, "backend/models/aging_clocks/altumage450k_inflamm_elastic_model.pkl")
        model = joblib.load(model_path)
        cg_order_path = os.path.join(PROJECT_ROOT, "backend/data/altumAge450k_elnet_cg_order.csv")
        cg_order = pd.read_csv(cg_order_path, index_col=0)
    elif model_name == "Blood inflammatory Clock 2":
        model_path = os.path.join(PROJECT_ROOT, "backend/models/aging_clocks/hugging_inflamm_elastic_5.9MAE.pkl")
        model = joblib.load(model_path)
        cg_order_path = os.path.join(PROJECT_ROOT, "backend/data/inflamm_hugging_models_cg_order.csv")
        cg_order = pd.read_csv(cg_order_path, index_col=0)
    elif model_name == "Blood inflammatory Clock XGBoost":
        model_path = os.path.join(PROJECT_ROOT, "backend/models/aging_clocks/hugging_inflamm_xgboost_model_5.4MAE.pkl")
        model = joblib.load(model_path)
        cg_order_path = os.path.join(PROJECT_ROOT, "backend/data/inflamm_hugging_models_cg_order.csv")
        cg_order = pd.read_csv(cg_order_path, index_col=0)
    else:
        raise ValueError("Unknown model")

    betas = reorder_df_for_model(cg_order, betas)
    predictions = model.predict(betas.T.values)

    predictions_df = pd.DataFrame(list(predictions), index=betas.columns, columns=["PredictedAge"]).T

    return {
        "predictions": predictions_df.to_dict()
    }