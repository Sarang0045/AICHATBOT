from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion
from sklearn.pipeline import Pipeline

from app.intent_detector import clean_text

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_CANDIDATE_PATHS = (
    BACKEND_DIR / "data" / "intents.csv",
    PROJECT_ROOT / "intents.csv",
)
MODEL_DIR = BACKEND_DIR / "models"
MODEL_PATH = MODEL_DIR / "intent_model.joblib"

_cached_model: Pipeline | None = None


def _resolve_data_path() -> Path:
    for path in DATA_CANDIDATE_PATHS:
        if path.exists():
            return path

    checked_paths = ", ".join(str(path) for path in DATA_CANDIDATE_PATHS)
    raise FileNotFoundError(
        f"Could not find intents training data. Checked: {checked_paths}"
    )


def load_training_data() -> tuple[list[str], list[str]]:
    import csv

    texts: list[str] = []
    labels: list[str] = []
    data_path = _resolve_data_path()

    with data_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            texts.append(row["text"])
            labels.append(row["intent"])

    return texts, labels


def build_model() -> Pipeline:
    return Pipeline(
        steps=[
            (
                "features",
                FeatureUnion(
                    [
                        (
                            "word_tfidf",
                            TfidfVectorizer(
                                preprocessor=clean_text,
                                ngram_range=(1, 3),
                                min_df=1,
                                sublinear_tf=True,
                            ),
                        ),
                        (
                            "char_tfidf",
                            TfidfVectorizer(
                                preprocessor=clean_text,
                                analyzer="char_wb",
                                ngram_range=(3, 5),
                                min_df=1,
                                sublinear_tf=True,
                            ),
                        ),
                    ],
                ),
            ),
            (
                "feature_selection",
                SelectKBest(score_func=chi2, k="all"),
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1500,
                    solver="liblinear",
                    random_state=42,
                ),
            ),
        ]
    )

def train_intent_model() -> dict:
    global _cached_model

    texts, labels = load_training_data()

    X_train, X_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.25,
        random_state=42,
        stratify=labels
    )

    model = build_model()
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)

    report = classification_report(
        y_test,
        predictions,
        output_dict=True,
        zero_division=0,
    )
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    _cached_model = model

    return {
        "message": "Intent model trained successfully.",
        "total_examples": len(texts),
        "accuracy": round(float(accuracy), 4),
        "model_path": str(MODEL_PATH),
        "classification_report": report,
    }

def load_model() -> Pipeline | None:
    global _cached_model

    if _cached_model is not None:
        return _cached_model

    if not MODEL_PATH.exists():
        return None

    _cached_model = joblib.load(MODEL_PATH)
    return _cached_model


def predict_intent_with_model(message: str) -> tuple[str | None, float | None]:
    model = load_model()

    if model is None:
        return None, None

    intent = str(model.predict([message])[0])
    confidence = None

    if hasattr(model, "predict_proba"):
        confidence = float(max(model.predict_proba([message])[0]))

    return intent, confidence
