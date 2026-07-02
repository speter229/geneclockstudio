import numpy as np
from backend.services.train_preprocess import train_elasticnet_model


def test_elasticnet_imputes_nans():
    # Create X with NaNs and y
    X = np.array([[1.0, np.nan, 3.0], [4.0, 5.0, np.nan], [np.nan, 8.0, 9.0], [2.0, 3.0, 4.0]])
    y = np.array([10.0, 20.0, 30.0, 15.0])

    model = train_elasticnet_model(X, y, cv=2, alpha=0.1, l1_ratio=0.5, max_iter=1000)
    # model should be a pipeline with a named step 'elasticnet'
    assert hasattr(model, 'named_steps')
    assert 'elasticnet' in model.named_steps
    preds = model.predict(X)
    assert preds.shape[0] == X.shape[0]
    # Predictions should be finite
    assert np.isfinite(preds).all()
