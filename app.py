import csv
import io
import json
import os
import random
import shutil
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st


APP_NAME = "Crohn's Disease and IBD Tracker Dashboard"
APP_VERSION = "1.0.0"
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
BACKUP_DIR = DATA_DIR / "data_backups"
UPLOADS_DIR = ROOT_DIR / "uploads"
PDFS_DIR = UPLOADS_DIR / "pdfs"
IMAGES_DIR = UPLOADS_DIR / "images"
SCANS_DIR = UPLOADS_DIR / "scans"
ARCHIVE_DIR = UPLOADS_DIR / "archive"
EXPORTS_DIR = DATA_DIR / "exports"
HEALTH_DATA_FILE = DATA_DIR / "health_data.json"
ABOUT_CROHNS_URL = "https://www.crohnscolitisfoundation.org/patientsandcaregivers/what-is-crohns-disease"

TRIGGER_TAGS = ["Dairy", "Gluten", "Spicy", "High Fat", "High Fiber", "Raw Vegetables"]
POSITIVE_MESSAGES = [
    "Every log you add gives your care story more clarity and momentum.",
    "Small, steady tracking can reveal patterns that are easy to miss day to day.",
    "You are building a useful record for better conversations with your care team.",
    "Progress does not have to be perfect to be meaningful.",
    "Today is a good day to notice one thing that went well and one thing to track.",
    "Your data can help turn uncertainty into insight.",
    "Consistency matters more than intensity when it comes to long-term tracking.",
]
LAB_MARKERS = ["Ferritin", "Hemoglobin", "ESR", "CRP", "Calprotectin Level", "Infliximab Level"]
LAB_REFERENCE_RANGES = {
    "Ferritin": (15.0, 150.0, "mcg/L"),
    "Hemoglobin": (12.0, 16.0, "g/dL"),
    "ESR": (0.0, 20.0, "mm/hr"),
    "CRP": (0.0, 5.0, "mg/L"),
    "Calprotectin Level": (0.0, 50.0, "mcg/g"),
    "Infliximab Level": (5.0, 15.0, "mcg/mL"),
}
LAB_INPUT_PRECISION = {
    "Ferritin": 1,
    "Hemoglobin": 2,
    "ESR": 1,
    "CRP": 3,
    "Calprotectin Level": 1,
    "Infliximab Level": 2,
}
FOOD_CATALOG_DEFAULT = {
    "Indian Vegetarian - Breakfast": [
        "Idli",
        "Dosa",
        "Upma",
        "Poha",
        "Pongal",
        "Appam with vegetable stew",
    ],
    "Indian Vegetarian - Lunch": [
        "Khichdi",
        "Plain dal and rice",
        "Curd rice",
        "Sambar rice",
        "Lemon rice",
        "Vegetable khichdi",
    ],
    "Indian Vegetarian - Dinner": [
        "Chapati with paneer curry",
        "Roti with dal",
        "Rice with vegetable curry",
        "Moong dal khichdi",
    ],
    "Indian Vegetarian - Snacks": [
        "Banana",
        "Fruit bowl",
        "Plain yogurt",
        "Roasted makhana",
        "Sattu drink",
    ],
    "Pasta": [
        "Plain pasta",
        "Pasta with tomato sauce",
        "Pasta primavera",
        "Pasta with olive oil and herbs",
        "Mac and cheese",
    ],
    "Pizza": [
        "Margherita pizza",
        "Cheese pizza",
        "Veggie pizza",
        "Thin crust pizza",
        "Gluten-free pizza",
    ],
    "Desserts": [
        "Plain yogurt",
        "Rice pudding",
        "Fruit bowl",
        "Gelato",
        "Ice cream",
        "Custard",
    ],
    "Other": [
        "Banana",
        "Apple sauce",
        "Oatmeal",
    ],
}
FOOD_TRIGGER_RULES = {
    "Dairy": [
        "paneer",
        "cheese",
        "curd",
        "yogurt",
        "butter",
        "cream",
        "milk",
        "lassi",
        "ice cream",
        "gelato",
        "custard",
        "khoya",
        "ghee",
    ],
    "Gluten": [
        "wheat",
        "naan",
        "roti",
        "chapati",
        "pasta",
        "pizza",
        "bread",
        "pav",
    ],
    "Spicy": [
        "spicy",
        "chili",
        "chilli",
        "masala",
        "pepper",
        "hot",
    ],
    "High Fat": [
        "fried",
        "pizza",
        "cheese",
        "butter",
        "cream",
        "ghee",
        "ice cream",
        "mac and cheese",
    ],
    "High Fiber": [
        "beans",
        "salad",
        "oats",
        "oatmeal",
        "sprouts",
        "vegetable",
    ],
    "Raw Vegetables": [
        "raw",
        "salad",
        "cucumber",
        "carrot",
        "lettuce",
        "sprouts",
    ],
}
LAB_UPLOAD_COLUMNS = [
    "date",
    "metric",
    "value",
    "unit",
    "normal_min",
    "normal_max",
    "comments",
]
INFUSION_MEDICATION = "Infliximab"
SAFE_MEALS = [
    "Rice based item",
    "Vegetables cooked or steamed",
    "Oatmeal with banana",
    "Omelet with vegetables",
    "Indian dal or rasam with rice",
    "Scrambled eggs and toast",
]
TRIGGER_MEALS = [
    "Cheesy pasta",
    "Cheese Pizza",
    "Ice cream and cookies",
    "Fried food",
    "Doughnuts",
    "Thai food with Tofu",
]


def ensure_directories() -> None:
    for path in [DATA_DIR, BACKUP_DIR, UPLOADS_DIR, PDFS_DIR, IMAGES_DIR, SCANS_DIR, ARCHIVE_DIR, EXPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def today() -> date:
    return datetime.now().date()


def date_to_str(value: date) -> str:
    return value.strftime("%Y-%m-%d")


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def rerun_app() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def make_id(prefix: str, dt: Optional[date] = None, suffix: Optional[str] = None) -> str:
    stamp = (dt or today()).strftime("%Y%m%d")
    if suffix:
        return f"{prefix}_{stamp}_{suffix}"
    return f"{prefix}_{stamp}_{random.randint(1000, 9999)}"


def default_data() -> Dict[str, Any]:
    return {
        "app_metadata": {
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "patient_id": "patient_001",
            "created_at": utc_now_iso(),
            "timezone": "America/Los_Angeles",
        },
        "patient_profile": {
            "full_name": "Sample Patient",
            "dob": "1994-05-12",
            "sex": "Female",
            "diagnosis": "Crohn's Disease",
            "notes": "Starter profile used for initial mock trend generation",
        },
        "lab_biomarkers": [],
        "infusion_events": [],
        "daily_symptoms": [],
        "food_logs": [],
        "food_catalog": build_default_food_catalog(),
        "file_library": [],
        "derived_insights": {
            "last_updated": None,
            "top_suspected_triggers": [],
            "baseline_high_pain_rate": 0.0,
        },
    }


def load_data() -> Dict[str, Any]:
    try:
        if not HEALTH_DATA_FILE.exists():
            raise FileNotFoundError(str(HEALTH_DATA_FILE))
        with HEALTH_DATA_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        data = restore_from_latest_backup()
        if data is None:
            data = seed_and_save_data()
            st.session_state["recovery_message"] = (
                "No valid backup was available. A fresh data file was created."
            )
            return data
        st.session_state["recovery_message"] = (
            "Corrupted file detected. System successfully restored from your latest backup."
        )
        return data
    except OSError:
        data = restore_from_latest_backup()
        if data is None:
            data = seed_and_save_data()
            st.session_state["recovery_message"] = (
                "A file access error occurred. A fresh data file was created."
            )
            return data
        st.session_state["recovery_message"] = (
            "File access error detected. System successfully restored from your latest backup."
        )
        return data

    data = normalize_schema(data)
    data = ensure_mock_history(data, target_days=30)
    recompute_derived_insights(data)
    save_data(data)
    return data


def _serialize_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=True)


def _prune_backups(limit: int = 10) -> None:
    if not BACKUP_DIR.exists():
        return
    backups = sorted([path for path in BACKUP_DIR.glob("backup_*.json") if path.is_file()])
    while len(backups) > limit:
        stale_backup = backups.pop(0)
        try:
            stale_backup.unlink()
        except OSError:
            pass


def _write_json_atomically(path: Path, serialized: str) -> None:
    tmp_path = path.with_name(f"{path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _write_json_backup(data: Dict[str, Any], serialized: str) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = BACKUP_DIR / backup_name
    with backup_path.open("w", encoding="utf-8") as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    _prune_backups(limit=10)


def restore_from_latest_backup() -> Optional[Dict[str, Any]]:
    if not BACKUP_DIR.exists():
        return None
    backups = sorted([path for path in BACKUP_DIR.glob("backup_*.json") if path.is_file()], reverse=True)
    for backup_path in backups:
        try:
            with backup_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        data = normalize_schema(data)
        data = ensure_mock_history(data, target_days=30)
        recompute_derived_insights(data)
        save_data(data)
        return data
    return None


def get_backup_status() -> Dict[str, Any]:
    if not BACKUP_DIR.exists():
        return {"count": 0, "latest_name": None, "latest_modified": None}

    backups = sorted([path for path in BACKUP_DIR.glob("backup_*.json") if path.is_file()], key=lambda item: item.stat().st_mtime, reverse=True)
    if not backups:
        return {"count": 0, "latest_name": None, "latest_modified": None}

    latest_backup = backups[0]
    latest_modified = datetime.fromtimestamp(latest_backup.stat().st_mtime).strftime("%b %d, %Y %I:%M %p")
    return {
        "count": len(backups),
        "latest_name": latest_backup.name,
        "latest_modified": latest_modified,
    }


def save_data(data: Dict[str, Any]) -> None:
    data = normalize_schema(data)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    serialized = _serialize_json(data)
    try:
        _write_json_backup(data, serialized)
    except OSError:
        pass
    try:
        _write_json_atomically(HEALTH_DATA_FILE, serialized)
    except OSError:
        with HEALTH_DATA_FILE.open("w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())


def normalize_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    base = default_data()
    for key in base:
        if key not in data:
            data[key] = base[key]
    for key in ["lab_biomarkers", "infusion_events", "daily_symptoms", "food_logs", "file_library"]:
        if not isinstance(data.get(key), list):
            data[key] = []
    if not isinstance(data.get("food_catalog"), dict):
        data["food_catalog"] = build_default_food_catalog()
    else:
        normalized_catalog = build_default_food_catalog()
        for category, choices in data.get("food_catalog", {}).items():
            if category not in normalized_catalog:
                normalized_catalog[category] = []
            if isinstance(choices, list):
                for choice in choices:
                    choice_text = str(choice).strip()
                    if choice_text and choice_text not in normalized_catalog[category]:
                        normalized_catalog[category].append(choice_text)
        data["food_catalog"] = normalized_catalog
    normalize_lab_units(data)
    if not isinstance(data.get("derived_insights"), dict):
        data["derived_insights"] = base["derived_insights"]
    return data


def build_default_food_catalog() -> Dict[str, List[str]]:
    return {category: list(choices) for category, choices in FOOD_CATALOG_DEFAULT.items()}


def normalize_lab_units(data: Dict[str, Any]) -> None:
    for item in data.get("lab_biomarkers", []):
        metric = str(item.get("metric", "")).strip()
        metric_lower = metric.lower()
        unit = str(item.get("unit", "")).strip()
        if metric == "Ferritin" and unit.lower() in {"ng/ml", "mcg/l", "ug/l"}:
            item["unit"] = "mcg/L"
        elif metric == "Infliximab Level" and unit.lower() in {"ug/ml", "mcg/ml"}:
            item["unit"] = "mcg/mL"
        elif metric_lower in {"calprotectin", "fecal calprotectin", "calprotectin level"}:
            item["metric"] = "Calprotectin Level"
            if unit.lower() in {"ug/g", "mcg/g"}:
                item["unit"] = "mcg/g"

    for item in data.get("infusion_events", []):
        level_unit = str(item.get("level_unit", "")).strip()
        if level_unit.lower() in {"ug/ml", "mcg/ml"}:
            item["level_unit"] = "mcg/mL"


def seed_and_save_data() -> Dict[str, Any]:
    data = default_data()
    seeded = generate_mock_history(30)
    data["lab_biomarkers"] = seeded["lab_biomarkers"]
    data["infusion_events"] = seeded["infusion_events"]
    data["daily_symptoms"] = seeded["daily_symptoms"]
    data["food_logs"] = seeded["food_logs"]
    data["file_library"] = []
    recompute_derived_insights(data)
    save_data(data)
    return data


def generate_mock_history(days: int = 30, end_date: Optional[date] = None) -> Dict[str, List[Dict[str, Any]]]:
    rng = random.Random(20260816)
    end = end_date or today()
    start = end - timedelta(days=days - 1)
    daily_symptoms: List[Dict[str, Any]] = []
    food_logs: List[Dict[str, Any]] = []
    lab_biomarkers: List[Dict[str, Any]] = []
    infusion_events: List[Dict[str, Any]] = []
    flare_cycle = {3, 8, 13, 18, 24, 27}

    for offset in range(days):
        current_date = start + timedelta(days=offset)
        day_str = date_to_str(current_date)
        flare_day = offset in flare_cycle or rng.random() < 0.22

        if flare_day:
            pain = min(10, rng.randint(7, 9) + (1 if offset % 6 == 0 else 0))
            stool_frequency = rng.randint(5, 9)
            fatigue = rng.randint(6, 9)
            medications = ["Mesalamine", "Vitamin D"]
            if rng.random() < 0.35:
                medications.append("Prednisone")
        else:
            pain = rng.randint(1, 5)
            stool_frequency = rng.randint(1, 4)
            fatigue = rng.randint(2, 6)
            medications = ["Mesalamine"]
            if rng.random() < 0.3:
                medications.append("Vitamin D")

        flare_flag = pain >= 7 or stool_frequency >= 7
        daily_symptoms.append(
            {
                "entry_id": make_id("sym", current_date, "seed"),
                "date": day_str,
                "stool_frequency": stool_frequency,
                "pain_scale": pain,
                "fatigue_scale": fatigue,
                "medications": medications,
                "symptom_notes": "Mock trend record generated for dashboard initialization",
                "flare_flag": flare_flag,
                "source": "mock_seed",
            }
        )

        meal_types = ["Breakfast", "Lunch", "Dinner"]
        daily_trigger_tags: List[str] = []
        if flare_flag:
            daily_trigger_tags = rng.sample(TRIGGER_TAGS[:3], k=2 if rng.random() < 0.6 else 1)
        elif rng.random() < 0.4:
            daily_trigger_tags = [rng.choice(TRIGGER_TAGS)]

        day_meals: List[Tuple[str, str, List[str]]] = []
        safe_meals = rng.sample(SAFE_MEALS, k=min(2, len(SAFE_MEALS)))
        if flare_day:
            trigger_meal = rng.choice(TRIGGER_MEALS)
            day_meals.append((meal_types[0], safe_meals[0], []))
            day_meals.append((meal_types[1], trigger_meal, daily_trigger_tags[:1] or ["Spicy"]))
            day_meals.append((meal_types[2], safe_meals[-1], []))
        else:
            day_meals.append((meal_types[0], safe_meals[0], []))
            if rng.random() < 0.7:
                day_meals.append((meal_types[1], safe_meals[-1], []))
            if rng.random() < 0.5:
                day_meals.append((meal_types[2], rng.choice(SAFE_MEALS), []))

        for meal_index, (meal_type, text_entry, forced_tags) in enumerate(day_meals):
            trigger_tags = list(forced_tags)
            if not trigger_tags and rng.random() < 0.2:
                trigger_tags = [rng.choice(TRIGGER_TAGS)]
            food_logs.append(
                {
                    "food_id": make_id("food", current_date, str(meal_index + 1)),
                    "date": day_str,
                    "meal_type": meal_type,
                    "text_entry": text_entry,
                    "trigger_tags": trigger_tags,
                    "other_tags": [tag for tag in ["Low Residue", "High Protein", "Balanced"] if rng.random() < 0.25][:1],
                    "portion_size": "1 serving",
                    "symptom_link_note": "Generated as part of the 30-day seed history",
                    "source": "mock_seed",
                }
            )

    lab_dates = [start + timedelta(days=offset) for offset in range(0, days, 5)]
    if lab_dates[-1] != end:
        lab_dates.append(end)
    for idx, current_date in enumerate(lab_dates):
        severity = 0.4 + (idx * 0.12)
        ferritin = round(80.0 - severity * 18.0 + rng.random() * 4.0, 1)
        hemoglobin = round(13.8 - severity * 1.1 + rng.random() * 0.2, 1)
        esr = round(10.0 + severity * 12.0 + rng.random() * 2.0, 1)
        crp = round(2.0 + severity * 6.0 + rng.random() * 1.5, 1)
        calprotectin = round(35.0 + severity * 120.0 + rng.random() * 10.0, 1)
        infliximab = round(7.5 - severity * 1.1 + rng.random() * 0.4, 1)
        lab_biomarkers.extend(
            [
                make_lab_entry(current_date, "Ferritin", ferritin),
                make_lab_entry(current_date, "Hemoglobin", hemoglobin),
                make_lab_entry(current_date, "ESR", esr),
                make_lab_entry(current_date, "CRP", crp),
                make_lab_entry(current_date, "Calprotectin Level", calprotectin),
                make_lab_entry(current_date, "Infliximab Level", infliximab),
            ]
        )

    infusion_dates = [start + timedelta(days=offset) for offset in range(0, days, 14)]
    for idx, current_date in enumerate(infusion_dates):
        infusion_events.append(
            make_infusion_entry(
                current_date,
                dose_mg=round(300 + idx * 25 + rng.random() * 20, 0),
                frequency_days=56,
                notes="Mock infliximab infusion record",
            )
        )

    return {
        "lab_biomarkers": lab_biomarkers,
        "infusion_events": infusion_events,
        "daily_symptoms": daily_symptoms,
        "food_logs": food_logs,
    }


def make_lab_entry(entry_date: date, metric: str, value: float, unit: Optional[str] = None) -> Dict[str, Any]:
    low, high, default_unit = LAB_REFERENCE_RANGES.get(metric, (0.0, 0.0, ""))
    unit = unit or default_unit
    flag = "normal"
    if low and value < low:
        flag = "low"
    elif high and value > high:
        flag = "high"
    return {
        "record_id": make_id("lab", entry_date, metric.lower().replace(" ", "_")),
        "date": date_to_str(entry_date),
        "metric": metric,
        "value": value,
        "unit": unit,
        "reference_range": {"normal_min": low, "normal_max": high},
        "flag": flag,
        "source": "mock_seed",
        "comments": "Seeded biomarker entry",
    }


def make_infusion_entry(
    entry_date: date,
    dose_mg: float,
    frequency_days: int,
    weight_kg: Optional[float] = None,
    height_cm: Optional[float] = None,
    infliximab_level: Optional[float] = None,
    level_unit: str = "mcg/mL",
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "infusion_id": make_id("inf", entry_date, "seed"),
        "date": date_to_str(entry_date),
        "medication": INFUSION_MEDICATION,
        "dose_mg": dose_mg,
        "frequency_days": frequency_days,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
        "bmi": compute_bmi(weight_kg, height_cm),
        "infliximab_level": infliximab_level,
        "level_unit": level_unit,
        "site": "Outpatient infusion center",
        "notes": notes,
        "source": "mock_seed",
    }


def ensure_mock_history(data: Dict[str, Any], target_days: int = 30) -> Dict[str, Any]:
    symptom_dates = sorted({entry["date"] for entry in data.get("daily_symptoms", []) if entry.get("date")})
    if len(symptom_dates) >= target_days:
        return data

    if symptom_dates:
        earliest = parse_date(symptom_dates[0])
        missing_days = target_days - len(symptom_dates)
        start = earliest - timedelta(days=missing_days)
        generated = generate_mock_history(missing_days, start + timedelta(days=missing_days - 1))
    else:
        generated = generate_mock_history(target_days)
        start = None

    existing_symptom_dates = {entry["date"] for entry in data.get("daily_symptoms", [])}
    existing_food_keys = {(entry.get("date"), entry.get("meal_type"), entry.get("text_entry")) for entry in data.get("food_logs", [])}
    existing_lab_keys = {(entry.get("date"), entry.get("metric")) for entry in data.get("lab_biomarkers", [])}
    existing_infusion_dates = {entry.get("date") for entry in data.get("infusion_events", [])}

    for entry in generated["daily_symptoms"]:
        if entry["date"] not in existing_symptom_dates:
            data["daily_symptoms"].append(entry)

    for entry in generated["food_logs"]:
        key = (entry.get("date"), entry.get("meal_type"), entry.get("text_entry"))
        if key not in existing_food_keys:
            data["food_logs"].append(entry)

    for entry in generated["lab_biomarkers"]:
        key = (entry.get("date"), entry.get("metric"))
        if key not in existing_lab_keys:
            data["lab_biomarkers"].append(entry)

    for entry in generated.get("infusion_events", []):
        if entry.get("date") not in existing_infusion_dates:
            data["infusion_events"].append(entry)

    data["daily_symptoms"] = sorted(data["daily_symptoms"], key=lambda item: item.get("date", ""))
    data["food_logs"] = sorted(data["food_logs"], key=lambda item: (item.get("date", ""), item.get("meal_type", "")))
    data["lab_biomarkers"] = sorted(data["lab_biomarkers"], key=lambda item: (item.get("date", ""), item.get("metric", "")))
    data["infusion_events"] = sorted(data["infusion_events"], key=lambda item: item.get("date", ""))
    return data


def recompute_derived_insights(data: Dict[str, Any]) -> None:
    patterns = compute_tag_correlations(data)
    high_pain_days = sum(1 for item in data.get("daily_symptoms", []) if int(item.get("pain_scale", 0)) >= 7)
    total_days = len({item.get("date") for item in data.get("daily_symptoms", []) if item.get("date")})
    baseline = round((high_pain_days / total_days) * 100.0, 1) if total_days else 0.0
    data["derived_insights"] = {
        "last_updated": utc_now_iso(),
        "top_suspected_triggers": patterns[:5],
        "baseline_high_pain_rate": baseline,
    }


def get_dataframe(records: List[Dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def summarize_symptoms(data: Dict[str, Any]) -> pd.DataFrame:
    symptom_df = get_dataframe(data.get("daily_symptoms", []))
    if symptom_df.empty:
        return symptom_df
    symptom_df["date"] = pd.to_datetime(symptom_df["date"])
    symptom_df = symptom_df.sort_values("date")
    return symptom_df


def build_daily_view(data: Dict[str, Any]) -> pd.DataFrame:
    symptoms = summarize_symptoms(data)
    if symptoms.empty:
        return pd.DataFrame(columns=["date", "pain_scale", "stool_frequency", "fatigue_scale", "flare_flag", "medications", "foods", "trigger_tags"])

    foods = get_dataframe(data.get("food_logs", []))
    if not foods.empty:
        foods["date"] = pd.to_datetime(foods["date"])
        foods["food_label"] = foods.apply(
            lambda row: row.get("food_choice") or row.get("text_entry") or "",
            axis=1,
        )
        food_summary = (
            foods.groupby("date")
            .agg(
                foods=("food_label", lambda values: " | ".join([str(value) for value in values if str(value).strip()])),
                trigger_tags=("trigger_tags", lambda values: sorted({tag for sub in values for tag in (sub or [])})),
            )
            .reset_index()
        )
    else:
        food_summary = pd.DataFrame(columns=["date", "foods", "trigger_tags"])

    merged = symptoms.merge(food_summary, on="date", how="left")
    merged["foods"] = merged["foods"].fillna("")
    merged["trigger_tags"] = merged["trigger_tags"].apply(lambda value: ", ".join(value) if isinstance(value, list) else "")
    merged["medications"] = merged["medications"].apply(lambda value: ", ".join(value) if isinstance(value, list) else "")
    merged["date"] = merged["date"].dt.date
    return merged


def add_symptom_entry(data: Dict[str, Any], payload: Dict[str, Any]) -> None:
    payload = dict(payload)
    payload["entry_id"] = make_id("sym", parse_date(payload["date"]), "manual")
    payload["source"] = "manual_entry"
    data["daily_symptoms"].append(payload)
    data["daily_symptoms"] = sorted(data["daily_symptoms"], key=lambda item: item.get("date", ""))
    recompute_derived_insights(data)
    save_data(data)


def add_food_entry(data: Dict[str, Any], payload: Dict[str, Any]) -> None:
    payload = dict(payload)
    payload["food_id"] = make_id("food", parse_date(payload["date"]), "manual")
    payload["source"] = "manual_entry"
    food_choice = payload.get("food_choice") or payload.get("text_entry", "")
    payload["food_choice"] = str(food_choice).strip()
    payload["text_entry"] = payload["food_choice"]
    payload["inferred_trigger_tags"] = infer_food_trigger_tags(payload)
    data["food_logs"].append(payload)
    data["food_logs"] = sorted(data["food_logs"], key=lambda item: (item.get("date", ""), item.get("meal_type", "")))
    recompute_derived_insights(data)
    save_data(data)


def food_catalog_categories(data: Dict[str, Any]) -> List[str]:
    catalog = data.get("food_catalog", build_default_food_catalog())
    return list(catalog.keys())


def food_catalog_choices(data: Dict[str, Any], category: str) -> List[str]:
    catalog = data.get("food_catalog", build_default_food_catalog())
    choices = catalog.get(category, [])
    return [str(choice).strip() for choice in choices if str(choice).strip()]


def food_choice_default_index(options: List[str], search_text: str) -> int:
    if not options:
        return 0
    query = search_text.strip().lower()
    if query:
        for idx, choice in enumerate(options):
            if choice.lower() == query:
                return idx
        for idx, choice in enumerate(options):
            normalized_choice = choice.lower()
            if query in normalized_choice or normalized_choice in query:
                return idx
    return 0


def ensure_food_choice_in_catalog(data: Dict[str, Any], category: str, choice: str) -> str:
    choice = choice.strip()
    if not choice:
        return choice
    if "food_catalog" not in data or not isinstance(data["food_catalog"], dict):
        data["food_catalog"] = build_default_food_catalog()
    if category not in data["food_catalog"]:
        data["food_catalog"][category] = []
    for existing in data["food_catalog"][category]:
        if str(existing).strip().lower() == choice.lower():
            return str(existing).strip()
    data["food_catalog"][category].append(choice)
    data["food_catalog"][category] = sorted({str(item).strip() for item in data["food_catalog"][category] if str(item).strip()}, key=str.lower)
    return choice


def food_catalog_rows(data: Dict[str, Any]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for category in food_catalog_categories(data):
        for choice in food_catalog_choices(data, category):
            rows.append({"category": category, "food_choice": choice})
    if not rows:
        return pd.DataFrame(columns=["category", "food_choice"])
    return pd.DataFrame(rows).sort_values(["category", "food_choice"]).reset_index(drop=True)


def update_food_catalog_from_rows(data: Dict[str, Any], rows_df: pd.DataFrame) -> None:
    if rows_df.empty:
        data["food_catalog"] = {}
        save_data(data)
        return

    rebuilt: Dict[str, List[str]] = {}
    for _, row in rows_df.iterrows():
        category = str(row.get("category", "")).strip()
        choice = str(row.get("food_choice", "")).strip()
        if not category or not choice:
            continue
        rebuilt.setdefault(category, [])
        if choice not in rebuilt[category]:
            rebuilt[category].append(choice)

    for category in list(rebuilt.keys()):
        rebuilt[category] = sorted(rebuilt[category], key=str.lower)

    data["food_catalog"] = rebuilt
    save_data(data)


def infer_food_trigger_tags(food_entry: Dict[str, Any]) -> List[str]:
    tags: set[str] = set()
    manual_tags = food_entry.get("trigger_tags") or []
    if isinstance(manual_tags, list):
        for tag in manual_tags:
            tag_text = str(tag).strip()
            if tag_text:
                tags.add(tag_text)

    food_category = str(food_entry.get("food_category", "")).lower()
    food_choice = str(food_entry.get("food_choice") or food_entry.get("text_entry") or "").lower()
    searchable = f"{food_category} {food_choice}".strip()

    for tag, keywords in FOOD_TRIGGER_RULES.items():
        if any(keyword in searchable for keyword in keywords):
            tags.add(tag)

    if "indian vegetarian" in food_category:
        if any(keyword in food_choice for keyword in ["paneer", "curd", "yogurt", "lassi", "milk", "cheese", "butter", "cream", "ghee", "khoya"]):
            tags.add("Dairy")

    return sorted(tags)


def add_infusion_entry(data: Dict[str, Any], payload: Dict[str, Any]) -> None:
    payload = dict(payload)
    payload["infusion_id"] = make_id("inf", parse_date(payload["date"]))
    payload["source"] = "manual_entry"
    payload["weight_kg"] = _nullable_float(payload.get("weight_kg"))
    payload["height_cm"] = _nullable_float(payload.get("height_cm"))
    payload["bmi"] = compute_bmi(payload.get("weight_kg"), payload.get("height_cm"))
    if "infliximab_level" in payload and payload["infliximab_level"] == "":
        payload["infliximab_level"] = None
    if "level_unit" not in payload:
        payload["level_unit"] = "mcg/mL"
    data["infusion_events"].append(payload)
    data["infusion_events"] = sorted(data["infusion_events"], key=lambda item: item.get("date", ""))
    save_data(data)


def add_lab_entry(data: Dict[str, Any], payload: Dict[str, Any]) -> None:
    add_lab_entry_with_source(data, payload, source="manual_entry")


def add_lab_entry_with_source(data: Dict[str, Any], payload: Dict[str, Any], source: str) -> None:
    payload = dict(payload)
    payload["record_id"] = make_id("lab", parse_date(payload["date"]))
    payload["source"] = source
    metric = payload.get("metric", "")
    value = float(payload.get("value", 0.0))
    low = float(payload.get("reference_range", {}).get("normal_min", 0.0))
    high = float(payload.get("reference_range", {}).get("normal_max", 0.0))
    if low and value < low:
        payload["flag"] = "low"
    elif high and value > high:
        payload["flag"] = "high"
    else:
        payload["flag"] = "normal"
    data["lab_biomarkers"].append(payload)
    data["lab_biomarkers"] = sorted(data["lab_biomarkers"], key=lambda item: (item.get("date", ""), item.get("metric", "")))
    recompute_derived_insights(data)
    save_data(data)


def _nullable_float(value: Any) -> Optional[float]:
    if _is_blank_upload_value(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compute_bmi(weight_kg: Any, height_cm: Any) -> Optional[float]:
    weight = _nullable_float(weight_kg)
    height = _nullable_float(height_cm)
    if weight is None or height is None or height <= 0:
        return None
    return round(weight / ((height / 100.0) ** 2), 1)


def latest_bmi_record(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    infusion_events = [item for item in data.get("infusion_events", []) if item.get("date")]
    if not infusion_events:
        return None

    enriched: List[Dict[str, Any]] = []
    for item in infusion_events:
        bmi_value = item.get("bmi")
        if bmi_value in (None, "", 0, 0.0):
            bmi_value = compute_bmi(item.get("weight_kg"), item.get("height_cm"))
        if bmi_value is None:
            continue
        record = dict(item)
        record["bmi"] = float(bmi_value)
        enriched.append(record)

    if not enriched:
        return None
    return sorted(enriched, key=lambda item: item.get("date", ""))[-1]


def latest_infusion_record(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    infusion_events = [item for item in data.get("infusion_events", []) if item.get("date")]
    if not infusion_events:
        return None
    return sorted(infusion_events, key=lambda item: item.get("date", ""))[-1]


def days_since_last_infusion(data: Dict[str, Any]) -> Optional[int]:
    latest = latest_infusion_record(data)
    if not latest:
        return None
    try:
        infusion_date = parse_date(str(latest.get("date", "")))
    except ValueError:
        return None
    return max((today() - infusion_date).days, 0)


def build_bmi_time_series(data: Dict[str, Any]) -> pd.DataFrame:
    infusion_df = get_dataframe(data.get("infusion_events", []))
    if infusion_df.empty:
        return pd.DataFrame(columns=["date", "bmi"])

    series_rows: List[Dict[str, Any]] = []
    for _, row in infusion_df.iterrows():
        bmi_value = row.get("bmi")
        if bmi_value in (None, "", 0, 0.0):
            bmi_value = compute_bmi(row.get("weight_kg"), row.get("height_cm"))
        if bmi_value is None:
            continue
        series_rows.append({"date": row.get("date"), "bmi": float(bmi_value)})

    if not series_rows:
        return pd.DataFrame(columns=["date", "bmi"])

    bmi_df = pd.DataFrame(series_rows)
    bmi_df["date"] = pd.to_datetime(bmi_df["date"])
    bmi_df = bmi_df.sort_values("date").set_index("date")
    return bmi_df


def lab_input_precision(metric: str) -> int:
    return LAB_INPUT_PRECISION.get(metric, 2)


def lab_input_step(metric: str) -> float:
    return 10 ** (-lab_input_precision(metric))


def lab_input_format(metric: str) -> str:
    return f"%.{lab_input_precision(metric)}f"


def lab_default_unit(metric: str) -> str:
    return LAB_REFERENCE_RANGES.get(metric, (0.0, 0.0, ""))[2]


def lab_default_bounds(metric: str) -> Tuple[float, float]:
    low, high, _ = LAB_REFERENCE_RANGES.get(metric, (0.0, 0.0, ""))
    return low, high


def format_utc_timestamp(value: Optional[str]) -> str:
    if not value:
        return "Unknown"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%b %d, %Y %I:%M %p UTC")
    except ValueError:
        return str(value)


def latest_numeric_change(records: List[Dict[str, Any]], value_key: str = "value") -> Optional[Tuple[float, float]]:
    numeric_values: List[float] = []
    for item in records:
        try:
            numeric_values.append(float(item.get(value_key)))
        except (TypeError, ValueError):
            continue
    if len(numeric_values) < 2:
        return None
    return numeric_values[-1], numeric_values[-2]


def change_note(current: Optional[float], previous: Optional[float], unit: str = "", precision: int = 1) -> str:
    if current is None:
        return "No prior comparison"
    if previous is None:
        return "First recorded value"
    delta = round(current - previous, precision)
    sign = "+" if delta > 0 else ""
    suffix = f" {unit}".strip()
    return f"{sign}{delta}{suffix} vs prev"


def lab_status(value: Any, normal_min: Any, normal_max: Any) -> str:
    try:
        numeric_value = float(value)
        low = float(normal_min)
        high = float(normal_max)
    except (TypeError, ValueError):
        return "Unknown"
    if numeric_value < low:
        return "Low"
    if numeric_value > high:
        return "High"
    return "Normal"


def build_lab_review_table(data: Dict[str, Any], limit: int = 12) -> pd.DataFrame:
    labs = _prepare_recent_lab_editor(data, limit=limit)
    if labs.empty:
        return labs
    review = labs.copy()
    review["status"] = review.apply(lambda row: lab_status(row.get("value"), row.get("normal_min"), row.get("normal_max")), axis=1)
    review["range"] = review.apply(lambda row: f"{row.get('normal_min', '')} - {row.get('normal_max', '')}", axis=1)
    return review[["date", "metric", "value", "unit", "range", "status", "comments"]]


def style_lab_review_table(df: pd.DataFrame) -> Any:
    def highlight_row(row: pd.Series) -> List[str]:
        status = str(row.get("status", "")).lower()
        if status == "high":
            return ["background-color: #fff1f1; color: #8a1f11;"] * len(row)
        if status == "low":
            return ["background-color: #fff8e6; color: #8a5a00;"] * len(row)
        if status == "normal":
            return ["background-color: #f1fbf5; color: #17633f;"] * len(row)
        return [""] * len(row)

    styler = df.style.apply(highlight_row, axis=1)
    return styler


def latest_metric_values(data: Dict[str, Any], metric: str) -> List[Dict[str, Any]]:
    records = [dict(item) for item in data.get("lab_biomarkers", []) if item.get("metric") == metric and item.get("date")]
    return sorted(records, key=lambda row: row.get("date", ""))


def build_lab_upload_sample_rows() -> List[Dict[str, Any]]:
    return [
        {
            "date": date_to_str(today() - timedelta(days=7)),
            "metric": "Ferritin",
            "value": 68.2,
            "unit": "mcg/L",
            "normal_min": 15.0,
            "normal_max": 150.0,
            "comments": "Iron store marker",
        },
        {
            "date": date_to_str(today() - timedelta(days=7)),
            "metric": "Hemoglobin",
            "value": 12.8,
            "unit": "g/dL",
            "normal_min": 12.0,
            "normal_max": 16.0,
            "comments": "CBC result",
        },
        {
            "date": date_to_str(today() - timedelta(days=7)),
            "metric": "ESR",
            "value": 14.0,
            "unit": "mm/hr",
            "normal_min": 0.0,
            "normal_max": 20.0,
            "comments": "Inflammation marker",
        },
        {
            "date": date_to_str(today() - timedelta(days=7)),
            "metric": "Infliximab Level",
            "value": 8.4,
            "unit": "mcg/mL",
            "normal_min": 5.0,
            "normal_max": 15.0,
            "comments": "Trough level before infusion",
        },
        {
            "date": date_to_str(today() - timedelta(days=7)),
            "metric": "CRP",
            "value": 0.03,
            "unit": "mg/L",
            "normal_min": 0.0,
            "normal_max": 5.0,
            "comments": "High-sensitivity CRP example",
        },
        {
            "date": date_to_str(today() - timedelta(days=7)),
            "metric": "Calprotectin Level",
            "value": 86.0,
            "unit": "mcg/g",
            "normal_min": 0.0,
            "normal_max": 50.0,
            "comments": "Fecal inflammation marker",
        },
    ]


def build_lab_upload_csv_sample() -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=LAB_UPLOAD_COLUMNS)
    writer.writeheader()
    writer.writerows(build_lab_upload_sample_rows())
    return buffer.getvalue()


def build_lab_upload_json_sample() -> str:
    return json.dumps({"lab_biomarkers": build_lab_upload_sample_rows()}, indent=2, ensure_ascii=True)


def _normalize_upload_key(value: str) -> str:
    return "".join(ch.lower() for ch in value.strip() if ch.isalnum())


def _is_blank_upload_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return bool(pd.isna(value))


def _upload_value_to_text(value: Any) -> str:
    return "" if _is_blank_upload_value(value) else str(value).strip()


def _upload_value_to_float(value: Any) -> float:
    if _is_blank_upload_value(value):
        return 0.0
    return float(value)


def _coerce_upload_date(value: Any) -> Optional[date]:
    if _is_blank_upload_value(value):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _comma_separated_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if str(item).strip())
    if value is None:
        return ""
    return str(value)


def _split_comma_separated_text(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if _is_blank_upload_value(value):
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _prepare_recent_lab_editor(data: Dict[str, Any], limit: int = 12) -> pd.DataFrame:
    labs = get_dataframe(data.get("lab_biomarkers", []))
    if labs.empty:
        return pd.DataFrame(columns=["record_id", "date", "metric", "value", "unit", "normal_min", "normal_max", "comments"])
    view = labs.sort_values("date", ascending=False).head(limit).copy()
    view["normal_min"] = view["reference_range"].apply(lambda ref: ref.get("normal_min", "") if isinstance(ref, dict) else "")
    view["normal_max"] = view["reference_range"].apply(lambda ref: ref.get("normal_max", "") if isinstance(ref, dict) else "")
    return view[["record_id", "date", "metric", "value", "unit", "normal_min", "normal_max", "comments"]].fillna("")


def _save_recent_lab_editor(data: Dict[str, Any], edited_df: pd.DataFrame) -> None:
    if edited_df.empty:
        return
    records = {entry.get("record_id"): dict(entry) for entry in data.get("lab_biomarkers", []) if entry.get("record_id")}
    for _, row in edited_df.iterrows():
        record_id = str(row.get("record_id", "")).strip()
        if not record_id or record_id not in records:
            continue
        metric = _upload_value_to_text(row.get("metric", ""))
        value = row.get("value", "")
        normal_min = row.get("normal_min", "")
        normal_max = row.get("normal_max", "")
        try:
            records[record_id].update(
                {
                    "date": date_to_str(_coerce_upload_date(row.get("date")) or parse_date(records[record_id].get("date", date_to_str(today())))),
                    "metric": metric,
                    "value": float(value),
                    "unit": _upload_value_to_text(row.get("unit", "")),
                    "reference_range": {
                        "normal_min": _upload_value_to_float(normal_min),
                        "normal_max": _upload_value_to_float(normal_max),
                    },
                    "comments": _upload_value_to_text(row.get("comments", "")),
                    "source": "manual_edit",
                }
            )
        except (TypeError, ValueError):
            continue

    updated: List[Dict[str, Any]] = []
    edited_ids = set(records.keys())
    for entry in data.get("lab_biomarkers", []):
        record_id = entry.get("record_id")
        if record_id in edited_ids:
            updated.append(records[record_id])
        else:
            updated.append(entry)
    data["lab_biomarkers"] = sorted(updated, key=lambda item: (item.get("date", ""), item.get("metric", "")))
    recompute_derived_insights(data)
    save_data(data)


def _prepare_recent_infusion_editor(data: Dict[str, Any], limit: int = 12) -> pd.DataFrame:
    infusions = get_dataframe(data.get("infusion_events", []))
    if infusions.empty:
        return pd.DataFrame(columns=["infusion_id", "date", "medication", "dose_mg", "frequency_days", "weight_kg", "height_cm", "bmi", "infliximab_level", "level_unit", "site", "notes"])
    view = infusions.sort_values("date", ascending=False).head(limit).copy()
    required_columns = ["infusion_id", "date", "medication", "dose_mg", "frequency_days", "weight_kg", "height_cm", "bmi", "infliximab_level", "level_unit", "site", "notes"]
    for column in required_columns:
        if column not in view.columns:
            view[column] = ""
    return view[required_columns].fillna("")


def _extract_lab_rows_from_json(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ["lab_biomarkers", "labs", "records", "rows"]:
            rows = payload.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def parse_lab_upload_file(uploaded_file: Any) -> Tuple[List[Dict[str, Any]], List[str]]:
    filename = uploaded_file.name.lower()
    warnings: List[str] = []
    raw_bytes = uploaded_file.getvalue()

    if filename.endswith(".csv"):
        text = raw_bytes.decode("utf-8-sig")
        dataframe = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
        rows = dataframe.to_dict(orient="records")
    elif filename.endswith(".json"):
        payload = json.loads(raw_bytes.decode("utf-8-sig"))
        rows = _extract_lab_rows_from_json(payload)
    else:
        return [], [f"Unsupported structured file type for {uploaded_file.name}."]

    parsed_rows: List[Dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        normalized = {_normalize_upload_key(str(key)): value for key, value in row.items()}
        date_value = normalized.get("date", row.get("date", row.get("Date", "")))
        metric = normalized.get("metric", row.get("metric", row.get("Metric", "")))
        value = normalized.get("value", row.get("value", row.get("Value", "")))
        unit = normalized.get("unit", row.get("unit", row.get("Unit", "")))
        comments = normalized.get("comments", row.get("comments", row.get("Comments", "")))

        ref_range = row.get("reference_range") if isinstance(row.get("reference_range"), dict) else {}
        normal_min = normalized.get("normalmin", ref_range.get("normal_min", ""))
        normal_max = normalized.get("normalmax", ref_range.get("normal_max", ""))

        if _is_blank_upload_value(date_value) or _is_blank_upload_value(metric) or _is_blank_upload_value(value):
            warnings.append(f"Row {index} skipped because it is missing date, metric, or value.")
            continue

        try:
            parsed_date = _coerce_upload_date(date_value)
            if parsed_date is None:
                raise ValueError("invalid date")
            parsed_value = _upload_value_to_float(value)
            parsed_min = _upload_value_to_float(normal_min)
            parsed_max = _upload_value_to_float(normal_max)
        except (TypeError, ValueError):
            warnings.append(f"Row {index} skipped because one or more numeric/date fields were invalid.")
            continue

        parsed_rows.append(
            {
                "date": date_to_str(parsed_date),
                "metric": _upload_value_to_text(metric),
                "value": parsed_value,
                "unit": _upload_value_to_text(unit) or LAB_REFERENCE_RANGES.get(_upload_value_to_text(metric), (0.0, 0.0, ""))[2],
                "reference_range": {"normal_min": parsed_min, "normal_max": parsed_max},
                "comments": _upload_value_to_text(comments),
            }
        )

    return parsed_rows, warnings


def preview_structured_lab_upload(uploaded_file: Any) -> Tuple[pd.DataFrame, List[str]]:
    parsed_rows, warnings = parse_lab_upload_file(uploaded_file)
    if not parsed_rows:
        return pd.DataFrame(columns=LAB_UPLOAD_COLUMNS), warnings

    preview_rows: List[Dict[str, Any]] = []
    for row in parsed_rows:
        preview_rows.append(
            {
                "date": row.get("date", ""),
                "metric": row.get("metric", ""),
                "value": row.get("value", ""),
                "unit": row.get("unit", ""),
                "normal_min": row.get("reference_range", {}).get("normal_min", ""),
                "normal_max": row.get("reference_range", {}).get("normal_max", ""),
                "comments": row.get("comments", ""),
            }
        )
    return pd.DataFrame(preview_rows, columns=LAB_UPLOAD_COLUMNS), warnings


def import_structured_lab_upload(data: Dict[str, Any], uploaded_file: Any) -> Tuple[int, List[str]]:
    imported_rows, warnings = parse_lab_upload_file(uploaded_file)
    for row in imported_rows:
        add_lab_entry_with_source(data, row, source="upload_import")
    return len(imported_rows), warnings


def infer_file_bucket(filename: str) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return PDFS_DIR
    if suffix in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"]:
        return IMAGES_DIR
    return SCANS_DIR


def save_uploaded_file(uploaded_file: Any) -> Dict[str, Any]:
    source_name = uploaded_file.name
    target_dir = infer_file_bucket(source_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{source_name}".replace(" ", "_")
    target_path = target_dir / safe_name
    archive_month_dir = ARCHIVE_DIR / datetime.now().strftime("%Y-%m")
    archive_month_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_month_dir / safe_name

    with target_path.open("wb") as destination:
        destination.write(uploaded_file.getbuffer())
    shutil.copy2(target_path, archive_path)

    return {
        "file_id": make_id("file", today(), "upload"),
        "date_added": utc_now_iso(),
        "file_name": source_name,
        "stored_name": safe_name,
        "file_type": Path(source_name).suffix.lower().lstrip(".") or "unknown",
        "file_path": str(target_path.relative_to(ROOT_DIR)),
        "archived_path": str(archive_path.relative_to(ROOT_DIR)),
        "document_category": infer_document_category(source_name),
        "notes": "Uploaded through the File Uploader tab",
        "text_extracted": False,
    }


def infer_document_category(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        if "lab" in lower:
            return "lab_result"
        if "colonoscopy" in lower or "procedure" in lower:
            return "procedure_report"
        return "pdf_document"
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff")):
        return "image_document"
    return "other"


def compute_tag_correlations(
    data: Dict[str, Any],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    pain_threshold: int = 7,
) -> List[Dict[str, Any]]:
    symptom_lookup: Dict[str, Dict[str, Any]] = {}
    for item in data.get("daily_symptoms", []):
        item_date = item.get("date")
        if not item_date:
            continue
        parsed = parse_date(item_date)
        if start_date and parsed < start_date:
            continue
        if end_date and parsed > end_date:
            continue
        symptom_lookup[item_date] = item

    tag_days: Dict[str, set] = defaultdict(set)
    high_pain_days_by_tag: Dict[str, set] = defaultdict(set)

    for item in data.get("food_logs", []):
        item_date = item.get("date")
        if item_date not in symptom_lookup:
            continue
        tags: set[str] = set()
        manual_tags = item.get("trigger_tags") or []
        if isinstance(manual_tags, list):
            for tag in manual_tags:
                tag_text = str(tag).strip()
                if tag_text:
                    tags.add(tag_text)

        inferred_tags = item.get("inferred_trigger_tags")
        if isinstance(inferred_tags, list) and inferred_tags:
            for tag in inferred_tags:
                tag_text = str(tag).strip()
                if tag_text:
                    tags.add(tag_text)
        else:
            for tag in infer_food_trigger_tags(item):
                tags.add(tag)

        if not tags:
            continue
        symptom = symptom_lookup[item_date]
        is_high_pain = int(symptom.get("pain_scale", 0)) >= pain_threshold or bool(symptom.get("flare_flag"))
        for tag in tags:
            tag_days[tag].add(item_date)
            if is_high_pain:
                high_pain_days_by_tag[tag].add(item_date)

    results: List[Dict[str, Any]] = []
    for tag, dates in tag_days.items():
        total_days = len(dates)
        high_days = len(high_pain_days_by_tag.get(tag, set()))
        correlation = round((high_days / total_days) * 100.0, 1) if total_days else 0.0
        results.append(
            {
                "tag": tag,
                "correlation_percent": correlation,
                "supporting_days": high_days,
                "high_pain_days_with_tag": high_days,
                "total_days_with_tag": total_days,
            }
        )

    results.sort(key=lambda item: (item["correlation_percent"], item["total_days_with_tag"]), reverse=True)
    return results


def build_export_package(
    data: Dict[str, Any],
    start_date: Optional[date],
    end_date: Optional[date],
    patterns: List[Dict[str, Any]],
) -> Dict[str, Any]:
    def in_range(item_date: str) -> bool:
        parsed = parse_date(item_date)
        if start_date and parsed < start_date:
            return False
        if end_date and parsed > end_date:
            return False
        return True

    symptoms = [item for item in data.get("daily_symptoms", []) if in_range(item.get("date", "1900-01-01"))]
    foods = [item for item in data.get("food_logs", []) if in_range(item.get("date", "1900-01-01"))]
    labs = [item for item in data.get("lab_biomarkers", []) if in_range(item.get("date", "1900-01-01"))]

    return {
        "export_metadata": {
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "generated_at": utc_now_iso(),
            "date_range": {
                "start_date": start_date.strftime("%Y-%m-%d") if start_date else None,
                "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
            },
        },
        "patient_profile": data.get("patient_profile", {}),
        "daily_symptoms": symptoms,
        "food_logs": foods,
        "lab_biomarkers": labs,
        "top_patterns": patterns[:10],
        "derived_insights": data.get("derived_insights", {}),
    }


def doctor_export_csv(data: Dict[str, Any], start_date: Optional[date], end_date: Optional[date]) -> str:
    daily_view = build_daily_view(data)
    if daily_view.empty:
        return ""

    mask = pd.Series([True] * len(daily_view))
    if start_date:
        mask &= pd.to_datetime(daily_view["date"]) >= pd.Timestamp(start_date)
    if end_date:
        mask &= pd.to_datetime(daily_view["date"]) <= pd.Timestamp(end_date)

    filtered = daily_view.loc[mask].copy()
    if filtered.empty:
        return ""

    columns = [
        "date",
        "pain_scale",
        "stool_frequency",
        "fatigue_scale",
        "flare_flag",
        "medications",
        "foods",
        "trigger_tags",
        "symptom_notes",
    ]
    for column in columns:
        if column not in filtered.columns:
            filtered[column] = ""
    buffer = io.StringIO()
    filtered[columns].to_csv(buffer, index=False)
    return buffer.getvalue()


def get_positive_message() -> str:
    index = today().toordinal() % len(POSITIVE_MESSAGES)
    return POSITIVE_MESSAGES[index]


def render_landing_page() -> None:
    message = get_positive_message()
    st.markdown(
        """
        <style>
        .landing-shell {
            min-height: 78vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .landing-card {
            max-width: 920px;
            padding: 2.2rem 2rem;
            border-radius: 28px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(17, 100, 102, 0.10);
            box-shadow: 0 20px 60px rgba(15, 20, 25, 0.08);
            backdrop-filter: blur(10px);
        }
        .landing-title {
            margin: 0 0 0.6rem 0;
            font-size: 2.6rem;
            line-height: 1.05;
            color: #0b3d3b;
        }
        .landing-subtitle {
            margin: 0 0 1.2rem 0;
            font-size: 1.05rem;
            color: #35565b;
            line-height: 1.6;
        }
        .message-box {
            padding: 1rem 1rem;
            border-left: 5px solid #1c7c6d;
            background: linear-gradient(90deg, rgba(28,124,109,0.10), rgba(28,124,109,0.02));
            border-radius: 16px;
            color: #184b4a;
            font-size: 1.05rem;
            margin-bottom: 1.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="landing-shell">
            <div class="landing-card">
                <p class="landing-title">Welcome to your IBD tracker</p>
                <p class="landing-subtitle">
                    A calm, organized place to track how you feel, what you eat, key lab markers,
                    and infusion timing so your health story is easier to see.
                </p>
                <div class="message-box">
                    <strong>Message of the day:</strong> {message}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    center_left, center_mid, center_right = st.columns([1, 1, 1])
    with center_mid:
        if st.button("Enter Dashboard", use_container_width=True):
            st.session_state["entered_dashboard"] = True
            rerun_app()


def latest_lab_by_metric(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for item in sorted(data.get("lab_biomarkers", []), key=lambda row: row.get("date", "")):
        metric = item.get("metric")
        if metric:
            latest[metric] = item
    return latest


def build_lab_time_series(data: Dict[str, Any], metric: str) -> pd.DataFrame:
    lab_df = get_dataframe(data.get("lab_biomarkers", []))
    if lab_df.empty:
        return pd.DataFrame(columns=["date", "value"])
    metric_df = lab_df.loc[lab_df["metric"] == metric, ["date", "value"]].copy()
    if metric_df.empty:
        return metric_df
    metric_df["date"] = pd.to_datetime(metric_df["date"])
    metric_df = metric_df.sort_values("date").set_index("date")
    return metric_df


def render_marker_overview(data: Dict[str, Any]) -> None:
    latest = latest_lab_by_metric(data)
    cols = st.columns(6)
    for idx, metric in enumerate(LAB_MARKERS):
        item = latest.get(metric)
        if item:
            value = item.get("value", "")
            unit = item.get("unit", "")
            flag = item.get("flag", "normal")
            note = f"{item.get('date', '')} · {flag}"
            display_value = f"{value} {unit}".strip()
        else:
            display_value = "—"
            note = "No data yet"
        cols[idx].markdown(metric_card(metric, str(display_value), note), unsafe_allow_html=True)


def render_lab_trends(data: Dict[str, Any]) -> None:
    st.markdown('<div class="section-title">Lab Trends</div>', unsafe_allow_html=True)
    chart_cols = st.columns(2)
    for idx, metric in enumerate(["Ferritin", "Hemoglobin", "ESR", "CRP", "Calprotectin Level", "Infliximab Level"]):
        series = build_lab_time_series(data, metric)
        with chart_cols[idx % 2]:
            st.caption(metric)
            if series.empty:
                st.info(f"No {metric.lower()} records available.")
            else:
                st.line_chart(series)


def render_infusion_section(data: Dict[str, Any]) -> None:
    st.markdown('<div class="section-title">Infusion History</div>', unsafe_allow_html=True)
    infusion_df = get_dataframe(data.get("infusion_events", []))
    if infusion_df.empty:
        st.info("No infusion records available yet.")
        return

    st.caption("Edit the visible infusion rows, then save your changes.")
    editable_infusions = _prepare_recent_infusion_editor(data, limit=max(len(infusion_df), 12))
    edited_infusions = st.data_editor(
        editable_infusions,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="infusion_editor",
    )
    if st.button("Save infusion edits", key="save_infusion_edits", use_container_width=True):
        _save_recent_infusion_editor(data, edited_infusions)
        st.success("Infusion records updated.")
        rerun_app()

    dates = sorted(pd.to_datetime(infusion_df["date"]).dt.date.tolist())
    if len(dates) > 1:
        intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        st.metric("Average infusion interval", f"{round(sum(intervals) / len(intervals), 1)} days")
    else:
        st.metric("Average infusion interval", "Not enough history")


def render_bmi_section(data: Dict[str, Any]) -> None:
    render_section_anchor("bmi-trend")
    st.markdown('<div class="section-title">BMI Trend</div>', unsafe_allow_html=True)
    bmi_series = build_bmi_time_series(data)
    if bmi_series.empty:
        st.info("No BMI records available yet. Add weight and height in the infusion logger to start tracking.")
        return

    st.line_chart(bmi_series)
    latest = latest_bmi_record(data)
    if latest:
        weight = latest.get("weight_kg")
        height = latest.get("height_cm")
        st.caption(
            f"Latest BMI: {latest.get('bmi', '—')} on {latest.get('date', '')} "
            f"from weight {weight if weight is not None else '—'} kg and height {height if height is not None else '—'} cm."
        )


def render_section_anchor(anchor_id: str) -> None:
    st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)


def render_dashboard_jump_links() -> None:
    st.markdown(
        """
        <div class="jump-links">
            <a href="#overview">Overview</a>
            <a href="#dashboard-symptom-summary">Symptom Log</a>
            <a href="#dashboard-food-summary">Food Log</a>
            <a href="#dashboard-lab-summary">Lab Log</a>
            <a href="#dashboard-infusion-summary">Infusion Log</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_about_crohns() -> None:
    st.markdown('<div class="section-title">About Crohn\'s Disease</div>', unsafe_allow_html=True)
    st.write(
        "Crohn's disease is a chronic inflammatory bowel disease that can affect any part of the digestive tract, "
        "most often the end of the small bowel and the beginning of the colon."
    )

    left, right = st.columns([1.2, 1.0])
    with left:
        st.markdown(
            """
            ### What it can look like
            - Symptoms may include abdominal pain, diarrhea, fatigue, fever, and unintended weight loss.
            - Symptoms can come and go, with periods of flare-ups and calmer periods.
            - Treatment often includes medication, nutrition support, and sometimes surgery.
            - Tracking food, symptoms, labs, and infusion history can help reveal patterns over time.
            """
        )
    with right:
        st.markdown(
            f"""
            ### Official resource
            Learn more from the Crohn's & Colitis Foundation:

            [What is Crohn's Disease?]({ABOUT_CROHNS_URL})

            The Foundation is a nonprofit that provides education, support, and research for people living with IBD.
            """
        )

    st.markdown(
        """
        ### When to reach out
        Contact your clinician promptly if your symptoms suddenly worsen, you cannot keep fluids down,
        you notice blood in stool, or you think you may be having a flare.
        """
    )


def render_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(18, 89, 96, 0.18), transparent 32%),
                radial-gradient(circle at bottom right, rgba(42, 123, 95, 0.14), transparent 28%),
                linear-gradient(180deg, #f6fbfb 0%, #f1f7f5 100%);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .hero {
            padding: 1.2rem 1.25rem;
            border-radius: 22px;
            background: linear-gradient(135deg, #0b3d3b 0%, #116466 55%, #1c7c6d 100%);
            color: white;
            box-shadow: 0 18px 50px rgba(11, 61, 59, 0.18);
            margin-bottom: 1.25rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2.2rem;
        }
        .hero p {
            margin: 0.35rem 0 0 0;
            opacity: 0.95;
            line-height: 1.5;
        }
        .metric-card {
            padding: 1rem 1rem;
            border-radius: 18px;
            background: white;
            border: 1px solid rgba(17, 100, 102, 0.08);
            box-shadow: 0 10px 24px rgba(15, 20, 25, 0.05);
            min-height: 118px;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .mini-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #5a6d6f;
            margin-bottom: 0.25rem;
        }
        .metric-value {
            font-size: 1.65rem;
            font-weight: 700;
            color: #103f3d;
        }
        .section-title {
            margin-top: 1.2rem;
            margin-bottom: 0.6rem;
            font-size: 1.15rem;
            font-weight: 700;
            color: #153c3b;
        }
        .jump-links {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem;
            margin: 0.25rem 0 1rem 0;
        }
        .jump-links a {
            display: inline-block;
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            background: rgba(17, 100, 102, 0.08);
            color: #0b3d3b;
            text-decoration: none;
            font-size: 0.88rem;
            border: 1px solid rgba(17, 100, 102, 0.12);
        }
        .jump-links a:hover {
            background: rgba(17, 100, 102, 0.14);
        }
        .metric-card {
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .metric-card-link {
            display: block;
            color: inherit;
            text-decoration: none;
            height: 100%;
        }
        .metric-card-link:hover .metric-card {
            transform: translateY(-1px);
            box-shadow: 0 14px 28px rgba(15, 20, 25, 0.09);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.35rem;
            padding: 0.25rem;
            background: rgba(17, 100, 102, 0.06);
            border: 1px solid rgba(17, 100, 102, 0.10);
            border-radius: 18px;
            overflow-x: auto;
        }
        .stTabs [data-baseweb="tab"] {
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(17, 100, 102, 0.16);
            border-radius: 14px;
            padding: 0.55rem 0.9rem;
            color: #0b3d3b;
            font-weight: 600;
            transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(17, 100, 102, 0.12);
            border-color: rgba(17, 100, 102, 0.28);
            color: #08302e;
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0b3d3b 0%, #116466 100%);
            border-color: #0b3d3b;
            color: white;
            box-shadow: 0 10px 24px rgba(11, 61, 59, 0.18);
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] p {
            color: white;
        }
        .stTabs [data-baseweb="tab"] p {
            margin: 0;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }
            .hero {
                padding: 1rem 1rem;
            }
            .hero h1 {
                font-size: 1.7rem;
            }
            .hero p {
                font-size: 0.95rem;
            }
            .metric-card {
                min-height: 0;
                padding: 0.85rem 0.85rem;
            }
            .metric-value {
                font-size: 1.35rem;
            }
            .mini-label {
                font-size: 0.74rem;
            }
            .section-title {
                font-size: 1.05rem;
            }
            .jump-links {
                gap: 0.4rem;
            }
            .jump-links a {
                font-size: 0.8rem;
                padding: 0.38rem 0.65rem;
            }
            .stTabs [data-baseweb="tab-list"] {
                gap: 0.25rem;
                padding: 0.2rem;
            }
            .stTabs [data-baseweb="tab"] {
                padding: 0.45rem 0.7rem;
                font-size: 0.82rem;
            }
            div[data-testid="stHorizontalBlock"] {
                gap: 0.75rem;
            }
            div[data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
            }
            div[data-testid="stDataFrame"] {
                overflow-x: auto;
            }
            .stButton > button,
            .stDownloadButton > button {
                width: 100%;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "", href: Optional[str] = None) -> str:
    card = f"""
    <div class="metric-card">
        <div class="mini-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div style="color:#516568;font-size:0.88rem;margin-top:0.2rem;">{note}</div>
    </div>
    """
    if href:
        return f'<a class="metric-card-link" href="{href}">{card}</a>'
    return card


def render_dashboard(data: Dict[str, Any]) -> None:
    render_section_anchor("overview")
    latest_labs = latest_lab_by_metric(data)
    latest_bmi = latest_bmi_record(data)
    bmi_series = build_bmi_time_series(data)
    latest_infusion_gap = days_since_last_infusion(data)
    bmi_value = latest_bmi.get("bmi") if latest_bmi else None
    latest_crp = latest_labs.get("CRP")
    latest_hemoglobin = latest_labs.get("Hemoglobin")
    latest_calprotectin = latest_labs.get("Calprotectin Level")
    updated_at = format_utc_timestamp(data.get("derived_insights", {}).get("last_updated"))

    st.markdown('<div class="section-title">Overview</div>', unsafe_allow_html=True)
    st.caption(f"Last updated: {updated_at}")
    c1, c2, c3, c4, c5 = st.columns(5)

    if latest_hemoglobin:
        hgb_value = latest_hemoglobin.get("value", "")
        hgb_unit = latest_hemoglobin.get("unit", "")
        hgb_display = f"{hgb_value} {hgb_unit}".strip()
        hgb_history = latest_metric_values(data, "Hemoglobin")
        hgb_change = latest_numeric_change(hgb_history)
        hgb_note = latest_hemoglobin.get('date', '')
        if hgb_change:
            hgb_note = f"{hgb_note} · {change_note(hgb_change[0], hgb_change[1], 'g/dL', precision=1)}"
    else:
        hgb_display = "—"
        hgb_note = "No hemoglobin data yet"

    if latest_crp:
        crp_value = latest_crp.get("value", "")
        crp_unit = latest_crp.get("unit", "")
        crp_display = f"{crp_value} {crp_unit}".strip()
        crp_history = latest_metric_values(data, "CRP")
        crp_change = latest_numeric_change(crp_history)
        crp_note = latest_crp.get('date', '')
        if crp_change:
            crp_note = f"{crp_note} · {change_note(crp_change[0], crp_change[1], 'mg/L', precision=2)}"
    else:
        crp_display = "—"
        crp_note = "No CRP data yet"
    if latest_calprotectin:
        cal_value = latest_calprotectin.get("value", "")
        cal_unit = latest_calprotectin.get("unit", "")
        cal_display = f"{cal_value} {cal_unit}".strip()
        cal_history = latest_metric_values(data, "Calprotectin Level")
        cal_change = latest_numeric_change(cal_history)
        cal_note = latest_calprotectin.get('date', '')
        if cal_change:
            cal_note = f"{cal_note} · {change_note(cal_change[0], cal_change[1], 'mcg/g', precision=1)}"
    else:
        cal_display = "—"
        cal_note = "No calprotectin data yet"
    infusion_display = f"{latest_infusion_gap} day(s)" if latest_infusion_gap is not None else "—"
    infusion_note = "Since most recent infusion" if latest_infusion_gap is not None else "No infusion history yet"
    if latest_bmi and bmi_series is not None and not bmi_series.empty and len(bmi_series) > 1:
        bmi_values = bmi_series["bmi"].tolist()
        bmi_change = latest_numeric_change([{"value": value} for value in bmi_values])
    else:
        bmi_change = None

    c1.markdown(metric_card("Hemoglobin", hgb_display, hgb_note), unsafe_allow_html=True)
    c2.markdown(metric_card("CRP", crp_display, crp_note), unsafe_allow_html=True)
    c3.markdown(metric_card("Calprotectin Level", cal_display, cal_note), unsafe_allow_html=True)
    c4.markdown(metric_card("Days Since Infusion", infusion_display, infusion_note), unsafe_allow_html=True)
    bmi_note = "See BMI on Infusions"
    if bmi_change:
        bmi_note = f"{bmi_note} · {change_note(bmi_change[0], bmi_change[1], '', precision=1)}"
    c5.markdown(metric_card("BMI", f"{bmi_value:.1f}" if bmi_value is not None else "—", bmi_note), unsafe_allow_html=True)


def render_symptom_logger(data: Dict[str, Any]) -> None:
    render_section_anchor("symptom-log")
    st.markdown('<div class="section-title">Symptom Log</div>', unsafe_allow_html=True)
    with st.form("symptom_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            symptom_date = st.date_input("Date", value=today(), key="symptom_date")
            stool_frequency = st.number_input("Stool frequency", min_value=0, max_value=30, value=4, step=1)
        with c2:
            pain_scale = st.slider("Pain scale", min_value=1, max_value=10, value=5, step=1)
            fatigue_scale = st.slider("Fatigue scale", min_value=1, max_value=10, value=5, step=1)
        with c3:
            medications = st.text_input("Medications (comma separated)", value="Mesalamine")
            flare_flag = st.checkbox("Mark as flare day", value=False)

        notes = st.text_area("Symptom notes", value="")
        submitted = st.form_submit_button("Save symptom entry")
        if submitted:
            payload = {
                "date": date_to_str(symptom_date),
                "stool_frequency": int(stool_frequency),
                "pain_scale": int(pain_scale),
                "fatigue_scale": int(fatigue_scale),
                "medications": [item.strip() for item in medications.split(",") if item.strip()],
                "symptom_notes": notes.strip(),
                "flare_flag": bool(flare_flag or pain_scale >= 7),
                "source": "manual_entry",
            }
            add_symptom_entry(data, payload)
            st.success("Symptom entry saved.")
            rerun_app()

    render_section_anchor("symptom-trend")
    st.markdown('<div class="section-title">30-Day Symptom Trend</div>', unsafe_allow_html=True)
    daily_view = build_daily_view(data)
    if not daily_view.empty:
        chart_df = daily_view.copy()
        chart_df["date"] = pd.to_datetime(chart_df["date"])
        chart_df = chart_df.set_index("date")[["pain_scale", "stool_frequency", "fatigue_scale"]]
        st.line_chart(chart_df)
    else:
        st.info("No symptom trend data is available yet.")


def render_food_logger(data: Dict[str, Any]) -> None:
    render_section_anchor("food-log")
    st.markdown('<div class="section-title">Food Log</div>', unsafe_allow_html=True)
    with st.form("food_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        categories = food_catalog_categories(data)
        with c1:
            food_date = st.date_input("Meal date", value=today(), key="food_date")
            meal_type = st.selectbox("Meal type", ["Breakfast", "Lunch", "Dinner", "Snack"])
            food_category = st.selectbox("Food category", categories or ["Other"], key="food_category_select")
            food_search = st.text_input("Search food choices", value="", placeholder="Type to filter choices", key="food_choice_search")
        with c2:
            trigger_tags = st.multiselect("Trigger categories", TRIGGER_TAGS)
            other_tags = st.multiselect("Other tags", ["Low Residue", "High Protein", "Balanced", "Low Fat"])
            catalog_choices = food_catalog_choices(data, food_category)
            if food_search.strip():
                filtered_choices = [choice for choice in catalog_choices if food_search.strip().lower() in choice.lower()]
            else:
                filtered_choices = catalog_choices
            choice_options = filtered_choices + ["Add a new food choice"]
            food_choice_selection = st.selectbox(
                "Food choice",
                choice_options or ["Add a new food choice"],
                index=food_choice_default_index(choice_options, food_search),
                key=f"food_choice_selection_{food_category}_{food_search.strip().lower()}",
            )
            custom_food_choice = ""
            if food_choice_selection == "Add a new food choice":
                custom_food_choice = st.text_input("New food choice", value=food_search.strip(), placeholder="Type a new dish name")

        meal_notes = st.text_area("Meal notes", value="")
        portion_size = st.text_input("Portion size", value="1 serving")
        submitted = st.form_submit_button("Save food entry")
        if submitted:
            chosen_food = custom_food_choice.strip() if food_choice_selection == "Add a new food choice" else food_choice_selection
            chosen_food = chosen_food.strip()
            if not chosen_food:
                st.error("Please choose a food item or add a new one.")
                return
            canonical_food = ensure_food_choice_in_catalog(data, food_category, chosen_food)
            payload = {
                "date": date_to_str(food_date),
                "meal_type": meal_type,
                "food_category": food_category,
                "food_choice": canonical_food,
                "text_entry": canonical_food,
                "trigger_tags": trigger_tags,
                "other_tags": other_tags,
                "portion_size": portion_size.strip(),
                "meal_notes": meal_notes.strip(),
                "symptom_link_note": "",
                "source": "manual_entry",
            }
            add_food_entry(data, payload)
            st.success("Food entry saved.")
            rerun_app()

    st.markdown('<div class="section-title">Food Catalog</div>', unsafe_allow_html=True)
    catalog_df = food_catalog_rows(data)
    if catalog_df.empty:
        st.info("No food catalog entries yet.")
    else:
        st.caption("This index is maintained automatically when a new food choice is added.")
        edited_catalog = st.data_editor(
            catalog_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="food_catalog_editor",
        )
        if st.button("Save food catalog edits", use_container_width=True):
            update_food_catalog_from_rows(data, edited_catalog)
            st.success("Food catalog updated.")
            rerun_app()

def render_lab_logger(data: Dict[str, Any]) -> None:
    render_section_anchor("lab-log")
    st.markdown('<div class="section-title">Lab Log</div>', unsafe_allow_html=True)
    st.caption("Enter blood markers here, including CRP, ferritin, hemoglobin, ESR, calprotectin, and infliximab level.")
    with st.form("lab_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            lab_date = st.date_input("Lab date", value=today(), key="lab_date")
            metric = st.selectbox("Metric", LAB_MARKERS, key="lab_metric_select")
        with c2:
            value = st.number_input(
                "Value",
                value=0.0,
                step=lab_input_step(metric),
                format=lab_input_format(metric),
            )
            unit = st.text_input("Unit", value=lab_default_unit(metric), key=f"lab_unit_{metric}")
        with c3:
            default_min, default_max = lab_default_bounds(metric)
            normal_min = st.number_input(
                "Normal min",
                value=default_min,
                step=lab_input_step(metric),
                format=lab_input_format(metric),
                key=f"lab_normal_min_{metric}",
            )
            normal_max = st.number_input(
                "Normal max",
                value=default_max,
                step=lab_input_step(metric),
                format=lab_input_format(metric),
                key=f"lab_normal_max_{metric}",
            )
        comments = st.text_area("Lab comments", value="")
        submitted = st.form_submit_button("Save lab entry")
        if submitted:
            payload = {
                "date": date_to_str(lab_date),
                "metric": metric,
                "value": float(value),
                "unit": unit.strip(),
                "reference_range": {
                    "normal_min": float(normal_min),
                    "normal_max": float(normal_max),
                },
                "comments": comments.strip(),
                "flag": "normal",
                "source": "manual_entry",
            }
            add_lab_entry(data, payload)
            st.success("Lab entry saved.")
            rerun_app()

    st.markdown('<div class="section-title">Lab Records</div>', unsafe_allow_html=True)
    labs = _prepare_recent_lab_editor(data)
    if not labs.empty:
        st.caption("Edit the visible lab rows, then save your changes.")
        edited_labs = st.data_editor(
            labs,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key="lab_page_recent_labs_editor",
        )
        if st.button("Save lab edits", key="save_lab_page_edits", use_container_width=True):
            _save_recent_lab_editor(data, edited_labs)
            st.success("Lab records updated.")
            rerun_app()
        else:
            st.info("No lab biomarker records found.")

    render_section_anchor("lab-trends")
    st.markdown('<div class="section-title">Lab Trends</div>', unsafe_allow_html=True)
    chart_cols = st.columns(2)
    for idx, metric in enumerate(["Ferritin", "Hemoglobin", "ESR", "CRP", "Calprotectin Level", "Infliximab Level"]):
        series = build_lab_time_series(data, metric)
        with chart_cols[idx % 2]:
            st.caption(metric)
            if series.empty:
                st.info(f"No {metric.lower()} records available.")
            else:
                st.line_chart(series)
    lab_review = build_lab_review_table(data)
    if not lab_review.empty:
        st.markdown('<div class="section-title">Lab Review</div>', unsafe_allow_html=True)
        st.caption("Out-of-range results are highlighted for quick review.")
        st.dataframe(style_lab_review_table(lab_review), use_container_width=True, hide_index=True)


def render_infusion_logger(data: Dict[str, Any]) -> None:
    render_section_anchor("infusion-log")
    st.markdown('<div class="section-title">Infusion Log</div>', unsafe_allow_html=True)
    st.caption("Use this page to log infusion date, dose, infliximab level, weight, height, and BMI together.")
    with st.form("infusion_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            infusion_date = st.date_input("Infusion date", value=today(), key="infusion_date")
            medication = st.text_input("Medication", value=INFUSION_MEDICATION)
        with c2:
            dose_mg = st.number_input("Dose (mg)", min_value=0.0, value=300.0, step=5.0, format="%.1f")
            frequency_days = st.number_input("Frequency (days)", min_value=1, value=56, step=1)
        with c3:
            weight_kg = st.number_input("Weight (kg)", min_value=0.0, value=0.0, step=0.1, format="%.1f")
            height_cm = st.number_input("Height (cm)", min_value=0.0, value=0.0, step=0.1, format="%.1f")
        with c4:
            infliximab_level = st.number_input(
                "Infliximab level",
                value=0.0,
                step=lab_input_step("Infliximab Level"),
                format=lab_input_format("Infliximab Level"),
            )
            level_unit = st.text_input("Level unit", value=LAB_REFERENCE_RANGES.get("Infliximab Level", (0.0, 0.0, "mcg/mL"))[2])

        site = st.text_input("Infusion site", value="Outpatient infusion center")
        infusion_notes = st.text_area("Infusion notes", value="")
        bmi_preview = compute_bmi(weight_kg, height_cm)
        st.caption(f"Calculated BMI: {bmi_preview if bmi_preview is not None else '—'}")
        submitted = st.form_submit_button("Save infusion entry")
        if submitted:
            payload = {
                "date": date_to_str(infusion_date),
                "medication": medication.strip() or INFUSION_MEDICATION,
                "dose_mg": float(dose_mg),
                "frequency_days": int(frequency_days),
                "weight_kg": float(weight_kg) if weight_kg else None,
                "height_cm": float(height_cm) if height_cm else None,
                "infliximab_level": float(infliximab_level),
                "level_unit": level_unit.strip() or "mcg/mL",
                "site": site.strip(),
                "notes": infusion_notes.strip(),
                "source": "manual_entry",
            }
            add_infusion_entry(data, payload)
            st.success("Infusion entry saved.")
            rerun_app()

    st.markdown('<div class="section-title">Infusion Trends</div>', unsafe_allow_html=True)
    render_infusion_section(data)
    render_bmi_section(data)


def render_uploader(data: Dict[str, Any]) -> None:
    st.markdown('<div class="section-title">Upload PDFs, Images, and Lab Files</div>', unsafe_allow_html=True)
    st.caption("Files are saved locally, categorized, and archived by month. CSV and JSON lab files are also imported into the app.")

    sample_col_1, sample_col_2 = st.columns(2)
    with sample_col_1:
        st.download_button(
            "Download lab upload sample CSV",
            data=build_lab_upload_csv_sample(),
            file_name="lab_upload_sample.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with sample_col_2:
        st.download_button(
            "Download lab upload sample JSON",
            data=build_lab_upload_json_sample(),
            file_name="lab_upload_sample.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown(
        "Accepted lab upload columns: `date`, `metric`, `value`, `unit`, `normal_min`, `normal_max`, `comments`."
    )
    st.caption("Example metrics include `Infliximab Level` with units like `mcg/mL` and `Calprotectin Level` with units like `mcg/g`.")

    uploaded_files = st.file_uploader(
        "Choose files",
        type=["pdf", "png", "jpg", "jpeg", "gif", "bmp", "tif", "tiff", "csv", "json"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        structured_files = [uploaded_file for uploaded_file in uploaded_files if uploaded_file.name.lower().endswith((".csv", ".json"))]
        if structured_files:
            st.markdown('<div class="section-title">Upload Preview</div>', unsafe_allow_html=True)
            st.caption("Review how each structured file will be interpreted before importing it into the lab data.")
            for uploaded_file in structured_files:
                with st.expander(uploaded_file.name, expanded=True):
                    preview_df, preview_warnings = preview_structured_lab_upload(uploaded_file)
                    if preview_df.empty:
                        st.info("No valid lab rows were found in this file.")
                    else:
                        st.dataframe(preview_df, use_container_width=True, hide_index=True)
                    if preview_warnings:
                        st.warning(" ".join(preview_warnings))

            if st.button("Import uploaded files", use_container_width=True):
                saved_records = []
                imported_count = 0
                import_warnings: List[str] = []
                for uploaded_file in uploaded_files:
                    record = save_uploaded_file(uploaded_file)
                    data["file_library"].append(record)
                    saved_records.append(record)
                    if uploaded_file.name.lower().endswith((".csv", ".json")):
                        count, warnings = import_structured_lab_upload(data, uploaded_file)
                        imported_count += count
                        import_warnings.extend(warnings)
                save_data(data)
                message = f"Saved {len(saved_records)} file(s)."
                if imported_count:
                    message += f" Imported {imported_count} lab row(s)."
                st.success(message)
                if import_warnings:
                    st.warning(" ".join(import_warnings))
                rerun_app()
        else:
            if st.button("Save uploaded files", use_container_width=True):
                saved_records = []
                for uploaded_file in uploaded_files:
                    record = save_uploaded_file(uploaded_file)
                    data["file_library"].append(record)
                    saved_records.append(record)
                save_data(data)
                st.success(f"Saved {len(saved_records)} file(s).")
                rerun_app()

    st.markdown('<div class="section-title">Uploaded File Library</div>', unsafe_allow_html=True)
    if data.get("file_library"):
        files_df = pd.DataFrame(data["file_library"]).sort_values("date_added", ascending=False)
        st.dataframe(files_df, use_container_width=True, hide_index=True)
    else:
        st.info("No uploaded documents yet.")

    st.markdown("### Folder Targets")
    st.write(
        {
            "PDFs": str(PDFS_DIR.relative_to(ROOT_DIR)),
            "Images": str(IMAGES_DIR.relative_to(ROOT_DIR)),
            "Scans": str(SCANS_DIR.relative_to(ROOT_DIR)),
            "Archive": str(ARCHIVE_DIR.relative_to(ROOT_DIR)),
        }
    )


def _load_uploaded_json_data(uploaded_file: Any) -> Dict[str, Any]:
    raw_bytes = uploaded_file.getvalue()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("utf-8-sig", errors="ignore")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Backup file must contain a JSON object.")
    return payload


def render_backup_recovery(data: Dict[str, Any]) -> None:
    st.markdown('<div class="section-title">Backup & Recovery</div>', unsafe_allow_html=True)
    st.caption("Use this page to download a full JSON backup or restore the dashboard from a previously exported file.")
    backup_status = get_backup_status()
    if backup_status["count"]:
        st.info(
            f"Backup status: {backup_status['count']} backup(s) retained. "
            f"Latest backup: {backup_status['latest_name']} at {backup_status['latest_modified']}."
        )
    else:
        st.info("Backup status: no backups have been created yet.")

    export_json = _serialize_json(data)
    export_name = f"health_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    st.download_button(
        "Manual Data Export",
        data=export_json,
        file_name=export_name,
        mime="application/json",
        use_container_width=True,
    )

    st.markdown("### Disaster Recovery Upload")
    uploaded_backup = st.file_uploader(
        "Upload a previously exported JSON backup",
        type=["json"],
        accept_multiple_files=False,
        key="recovery_backup_upload",
    )
    if uploaded_backup is not None:
        fingerprint = f"{uploaded_backup.name}:{getattr(uploaded_backup, 'size', 0)}"
        processed_fingerprint = st.session_state.get("recovery_backup_processed_fingerprint")
        if processed_fingerprint != fingerprint:
            try:
                restored_data = _load_uploaded_json_data(uploaded_backup)
                restored_data = normalize_schema(restored_data)
                restored_data = ensure_mock_history(restored_data, target_days=30)
                recompute_derived_insights(restored_data)
                save_data(restored_data)
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                st.error(f"Restore failed: {exc}")
            except OSError as exc:
                st.error(f"Could not write the uploaded backup to disk: {exc}")
            else:
                st.session_state["recovery_backup_processed_fingerprint"] = fingerprint
                st.success("Backup uploaded successfully. Restoring dashboard now.")
                rerun_app()


def render_pattern_export(data: Dict[str, Any]) -> None:
    st.markdown('<div class="section-title">Correlation Analysis</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        start_date_value = st.date_input("Start date", value=today() - timedelta(days=29), key="pattern_start")
    with c2:
        end_date_value = st.date_input("End date", value=today(), key="pattern_end")
    with c3:
        pain_threshold = st.slider("High pain threshold", min_value=1, max_value=10, value=7, step=1)

    if start_date_value > end_date_value:
        st.error("Start date must be on or before end date.")
        return

    patterns = compute_tag_correlations(data, start_date_value, end_date_value, pain_threshold)
    if patterns:
        pattern_df = pd.DataFrame(patterns)
        st.dataframe(pattern_df, use_container_width=True, hide_index=True)
    else:
        st.info("No trigger-tag correlations were found for the selected date range.")

    export_package = build_export_package(data, start_date_value, end_date_value, patterns)
    export_json = json.dumps(export_package, indent=2, ensure_ascii=True)
    export_csv = doctor_export_csv(data, start_date_value, end_date_value)

    json_path = EXPORTS_DIR / "doctor_export_latest.json"
    csv_path = EXPORTS_DIR / "doctor_export_latest.csv"
    json_path.write_text(export_json, encoding="utf-8")
    if export_csv:
        csv_path.write_text(export_csv, encoding="utf-8")

    st.markdown('<div class="section-title">Doctor Export</div>', unsafe_allow_html=True)
    st.download_button(
        "Download doctor export JSON",
        data=export_json,
        file_name="doctor_export_latest.json",
        mime="application/json",
    )
    if export_csv:
        st.download_button(
            "Download doctor export CSV",
            data=export_csv,
            file_name="doctor_export_latest.csv",
            mime="text/csv",
        )
    else:
        st.info("CSV export is empty for the current date range.")

    st.caption(
        "The correlation score is a transparent co-occurrence measure: "
        "high-pain days with a tag divided by all days with that tag."
    )


def render_header(data: Dict[str, Any]) -> None:
    profile = data.get("patient_profile", {})
    title = profile.get("diagnosis", "IBD Tracker")
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_NAME}</h1>
            <p>
                Personalized tracking for symptoms, labs, food triggers, and clinician-ready exports.
                Built for a {title} workflow with local JSON persistence and offline-friendly storage.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_positive_header() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="💚", layout="wide")
    ensure_directories()
    render_styles()
    st.markdown('<div class="section-title">Today\'s Reminder</div>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="💚", layout="wide")
    ensure_directories()
    render_styles()
    data = load_data()

    if "entered_dashboard" not in st.session_state:
        st.session_state["entered_dashboard"] = False

    if not st.session_state["entered_dashboard"]:
        render_landing_page()
        return

    render_header(data)
    recovery_message = st.session_state.pop("recovery_message", None)
    if recovery_message:
        st.warning(recovery_message)

    tabs = st.tabs(
        [
            "Dashboard",
            "Symptom Log",
            "Food Log",
            "Labs",
            "Infusions",
            "File Uploader",
            "Pattern & Export",
            "Backup & Recovery",
            "About Crohn's",
        ]
    )
    with tabs[0]:
        render_dashboard(data)
    with tabs[1]:
        render_symptom_logger(data)
    with tabs[2]:
        render_food_logger(data)
    with tabs[3]:
        render_lab_logger(data)
    with tabs[4]:
        render_infusion_logger(data)
    with tabs[5]:
        render_uploader(data)
    with tabs[6]:
        render_pattern_export(data)
    with tabs[7]:
        render_backup_recovery(data)
    with tabs[8]:
        render_about_crohns()


if __name__ == "__main__":
    main()
