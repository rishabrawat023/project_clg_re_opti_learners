"""
==============================================================================
Campus Resource Optimizer - Machine Learning Demand Prediction Prototype
Folder: ml/
File: prediction.py
BCA (AI & Data Science) College Project

OBJECTIVE:
Demonstrates how historical college resource booking data can be used by
Machine Learning models to forecast campus room demand and peak hours.

NOTE:
This script is a demonstration / proof-of-concept module.
The main web application functions independently without ML.
==============================================================================
"""

import sys

def run_ml_demand_prediction():
    print("=" * 72)
    print(" CAMPUS RESOURCE OPTIMIZER - AI/ML DEMAND PREDICTION MODULE")
    print(" BCA (AI & Data Science) Specialization")
    print("=" * 72)

    # --------------------------------------------------------------------------
    # Step 1: Simulated Historical College Booking Dataset
    # --------------------------------------------------------------------------
    # Features:
    #   - day_of_week: 1 (Mon) to 5 (Fri)
    #   - hour_of_day: 8 to 17 (8:00 AM to 5:00 PM)
    #   - resource_type_code: 0=Classroom, 1=Computer Lab, 2=Seminar Hall, 3=Auditorium
    #   - group_size: Number of students
    # Target:
    #   - demand_score: 0 to 100 (Percentage probability of resource being occupied)
    # --------------------------------------------------------------------------

    print("\n[Step 1] Loading historical campus booking logs...")

    sample_historical_data = {
        'day_of_week': [1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 1, 2, 3, 4],
        'hour_of_day': [9, 10, 14, 10, 11, 9, 14, 11, 15, 10, 14, 11, 14, 11, 10],
        'resource_type_code': [0, 0, 1, 0, 1, 2, 1, 0, 2, 0, 3, 0, 1, 0, 0],
        'group_size': [60, 55, 38, 50, 40, 120, 35, 60, 140, 50, 280, 58, 42, 52, 60],
        'demand_score': [75, 90, 85, 80, 88, 70, 80, 85, 65, 70, 95, 88, 82, 85, 90]
    }

    try:
        import pandas as pd
        import numpy as np
        df = pd.DataFrame(sample_historical_data)
        print("Historical Dataset Summary (First 5 records):")
        print(df.head(5).to_string(index=False))
    except ImportError:
        print("[Note] Pandas is optional; displaying raw records:")
        for k in range(5):
            print(f"  Day: {sample_historical_data['day_of_week'][k]}, "
                  f"Hour: {sample_historical_data['hour_of_day'][k]}, "
                  f"Students: {sample_historical_data['group_size'][k]} -> "
                  f"Demand: {sample_historical_data['demand_score'][k]}%")

    # --------------------------------------------------------------------------
    # Step 2: Feature Matrix (X) and Target Vector (y)
    # --------------------------------------------------------------------------
    feature_cols = ['day_of_week', 'hour_of_day', 'resource_type_code', 'group_size']
    
    # Check if scikit-learn is available and can load without OS policy restrictions
    use_sklearn = False
    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_squared_error
        # Quick probe to test if DLL is allowed by Windows policy
        test_model = LinearRegression()
        test_model.fit([[1, 2], [3, 4]], [5, 6])
        use_sklearn = True
    except Exception:
        use_sklearn = False

    print("\n[Step 2] Training Supervised Learning Model...")

    if use_sklearn:
        # Standard Scikit-Learn Pipeline
        import pandas as pd
        df = pd.DataFrame(sample_historical_data)
        X = df[feature_cols]
        y = df['demand_score']
        
        model = LinearRegression()
        model.fit(X, y)
        predictions = model.predict(X)
        mse = mean_squared_error(y, predictions)
        print(f"Scikit-Learn LinearRegression trained. Mean Squared Error (MSE): {mse:.2f}")

        def predict_fn(feats):
            feat_df = pd.DataFrame([feats], columns=feature_cols)
            return float(model.predict(feat_df)[0])

    else:
        # Robust Least-Squares Fallback (using Numpy / Pure Python Math)
        import numpy as np
        X_mat = np.column_stack([
            np.ones(len(sample_historical_data['day_of_week'])), # intercept
            sample_historical_data['day_of_week'],
            sample_historical_data['hour_of_day'],
            sample_historical_data['resource_type_code'],
            sample_historical_data['group_size']
        ])
        y_vec = np.array(sample_historical_data['demand_score'], dtype=float)

        # Solve normal equations via Least Squares: (X^T * X) * beta = X^T * y
        betas, residuals, rank, s = np.linalg.lstsq(X_mat, y_vec, rcond=None)
        preds = X_mat.dot(betas)
        mse = float(np.mean((y_vec - preds) ** 2))
        print(f"Linear Regression (Least Squares) trained. Mean Squared Error (MSE): {mse:.2f}")

        def predict_fn(feats):
            x_input = np.array([1.0] + feats)
            return float(x_input.dot(betas))

    # --------------------------------------------------------------------------
    # Step 3: Making Future Demand Predictions for Campus Slots
    # --------------------------------------------------------------------------
    print("\n[Step 3] Predicting Demand for Upcoming Campus Slots:")
    
    test_cases = [
        {"desc": "Monday 10:00 AM - Classroom (55 Students)", "features": [1, 10, 0, 55]},
        {"desc": "Wednesday 02:00 PM - Computer Lab (40 Students)", "features": [3, 14, 1, 40]},
        {"desc": "Friday 11:00 AM - Seminar Hall (120 Students)", "features": [5, 11, 2, 120]}
    ]

    for case in test_cases:
        raw_demand = predict_fn(case['features'])
        # Clamp demand score between 0 and 100%
        predicted_demand = max(0.0, min(100.0, raw_demand))

        demand_level = "[HIGH PEAK]" if predicted_demand >= 80 else ("[MODERATE]" if predicted_demand >= 60 else "[LOW]")
        print(f"  * {case['desc']}")
        print(f"    --> Predicted Utilization Score: {predicted_demand:.1f}% {demand_level}")

    print("\n" + "=" * 72)
    print(" [CONCLUSION] As real college booking records accumulate in MySQL,")
    print(" this ML model can be retrained periodically to forecast demand")
    print(" spikes, avoid scheduling crunches, and recommend energy-saving schedules.")
    print("=" * 72 + "\n")


if __name__ == '__main__':
    run_ml_demand_prediction()
