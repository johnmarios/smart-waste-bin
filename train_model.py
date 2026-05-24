import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os


def generate_training_data(days=30, seed=42):
    """
    Generate synthetic wastebin usage data
    for training a busy/quiet classifier.
    """

    rng = np.random.default_rng(seed)

    rows = []

    for day in range(days):

        # 0 = Monday, 6 = Sunday
        day_of_week = day % 7

        for hour in range(24):

            # Weekend activity
            if day_of_week in [5, 6]:
                base_rate = 2

            # Morning rush
            elif 8 <= hour <= 10:
                base_rate = 15

            # Lunch hours
            elif 11 <= hour <= 14:
                base_rate = 25

            # Afternoon
            elif 15 <= hour <= 17:
                base_rate = 12

            # Evening
            elif 18 <= hour <= 20:
                base_rate = 8

            # Night / early morning
            else:
                base_rate = 1

            # Generate synthetic event count
            event_count = int(
                rng.normal(
                    loc=base_rate,
                    scale=base_rate * 0.3
                )
            )

            # Prevent negative values
            if event_count < 0:
                event_count = 0

            # Generate label
            if event_count > 10:
                label = "busy"
            else:
                label = "quiet"

            rows.append({
                "day_of_week": day_of_week,
                "hour": hour,
                "is_weekend": 1 if day_of_week in [5, 6] else 0,
                "event_count": event_count,
                "label": label
            })

    df = pd.DataFrame(rows)

    return df


def train_and_save(output_dir="models"):

    # Create models directory if needed
    os.makedirs(output_dir, exist_ok=True)

    # Generate synthetic dataset
    df = generate_training_data()

    # Features
    X = df[
        [
            "day_of_week",
            "hour",
            "is_weekend"
        ]
    ]

    # Labels
    y = df["label"]

    # Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    # Random Forest classifier
    model = RandomForestClassifier(
        n_estimators=50,
        random_state=42
    )

    # Train model
    model.fit(X_train, y_train)

    # Predictions
    y_pred = model.predict(X_test)

    # Evaluation
    print("\nModel evaluation:\n")

    print(
        classification_report(
            y_test,
            y_pred
        )
    )

    # Save trained model
    model_path = os.path.join(
        output_dir,
        "busy_predictor.joblib"
    )

    joblib.dump(model, model_path)

    print(f"Model saved to: {model_path}")

    return model


if __name__ == "__main__":
    train_and_save()