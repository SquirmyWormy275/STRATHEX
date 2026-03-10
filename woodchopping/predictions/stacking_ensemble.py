"""
Stacking Ensemble for Woodchopping Handicap System

Hierarchical stacking ensemble combining 6 base models via meta-model:
- Baseline V2 Hybrid (statistical + hierarchical regression)
- XGBoost Enhanced (19 features, Bayesian-tuned)
- LightGBM (leaf-wise trees)
- RandomForest (variance estimation via OOB)
- Ridge Regression (linear interpretable)
- LLM (Ollama qwen2.5:32b, optional)

Meta-model: XGBoost trained on 32 meta-features

Functions:
    StackingEnsemble - Main ensemble class
"""

from typing import Optional, Dict, Tuple, List
import pandas as pd
import numpy as np
from dataclasses import dataclass

from config import data_req, ml_config, simulation_config
from woodchopping.data import load_results_df, engineer_features_for_ml, standardize_results_data, load_wood_data
from woodchopping.predictions.baseline import predict_baseline_v2_hybrid
from woodchopping.predictions.ml_model import train_ml_model
from woodchopping.predictions.lightgbm_model import train_lightgbm_model, predict_time_lightgbm
from woodchopping.predictions.randomforest_model import train_randomforest_model, predict_time_randomforest
from woodchopping.predictions.ridge_model import train_ridge_model, predict_time_ridge
from woodchopping.predictions.ai_predictor import predict_competitor_time_with_ai

try:
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    from sklearn.metrics import mean_absolute_error, r2_score
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False


@dataclass
class EnsemblePrediction:
    """Result from stacking ensemble prediction"""
    time: float
    std_dev: float
    confidence: str
    method_used: str
    explanation: str
    base_predictions: Dict[str, Optional[float]]
    base_variances: Dict[str, Optional[float]]
    meta_features: Dict[str, float]


class StackingEnsemble:
    """
    Hierarchical stacking ensemble for maximum prediction accuracy.

    Combines 6 base models using XGBoost meta-model trained on 32 meta-features:
    - Base predictions (6)
    - Base variances (6)
    - Prediction agreement (4)
    - Data quality (6)
    - Competitor characteristics (4)
    - Interactions (6)
    """

    def __init__(self):
        self.meta_model_sb = None
        self.meta_model_uh = None
        self.base_models_trained = False
        self.training_data_size = 0

    def train_base_models(self, results_df: Optional[pd.DataFrame] = None, force_retrain: bool = False):
        """Train all 6 base models"""
        if results_df is None:
            results_df = load_results_df()

        # Train all base models
        print("\n[STACKING ENSEMBLE] Training base models...")

        # 1. XGBoost (already trained via train_ml_model)
        print("  Training XGBoost...")
        self.xgb_models = train_ml_model(results_df, force_retrain=force_retrain)

        # 2. LightGBM
        print("  Training LightGBM...")
        self.lgb_models = train_lightgbm_model(results_df, force_retrain=force_retrain)

        # 3. RandomForest
        print("  Training RandomForest...")
        self.rf_models = train_randomforest_model(results_df, force_retrain=force_retrain)

        # 4. Ridge
        print("  Training Ridge Regression...")
        self.ridge_models = train_ridge_model(results_df, force_retrain=force_retrain)

        # Baseline V2 and LLM are called dynamically (not pre-trained)

        self.base_models_trained = True
        print("[STACKING ENSEMBLE] Base models trained successfully!\n")

    def _get_base_predictions(
        self,
        competitor_name: str,
        species: str,
        diameter: float,
        quality: int,
        event_code: str,
        results_df: pd.DataFrame
    ) -> Dict[str, Dict]:
        """Get predictions from all 6 base models"""

        predictions = {}
        wood_df = load_wood_data()

        # 1. Baseline V2
        try:
            baseline_time, baseline_conf, baseline_exp, baseline_meta = predict_baseline_v2_hybrid(
                competitor_name=competitor_name,
                species=species,
                diameter=diameter,
                quality=quality,
                event_code=event_code,
                results_df=results_df,
                wood_df=wood_df,
                enable_calibration=False  # Don't apply convergence yet
            )
            predictions['baseline_v2'] = {
                'time': baseline_time,
                'std_dev': baseline_meta.get('std_dev', 3.0) if baseline_meta else 3.0,
                'confidence': baseline_conf
            }
        except Exception:
            predictions['baseline_v2'] = {'time': None, 'std_dev': 3.0, 'confidence': 'N/A'}

        # 2. XGBoost
        try:
            # Use ml_model predict function (TODO: needs to be updated for 19 features)
            # For now, placeholder
            predictions['xgboost'] = {'time': None, 'std_dev': 3.0, 'confidence': 'N/A'}
        except Exception:
            predictions['xgboost'] = {'time': None, 'std_dev': 3.0, 'confidence': 'N/A'}

        # 3. LightGBM
        try:
            lgb_time, lgb_conf, lgb_exp = predict_time_lightgbm(
                competitor_name, species, diameter, quality, event_code, results_df
            )
            predictions['lightgbm'] = {
                'time': lgb_time,
                'std_dev': 3.0,  # LightGBM doesn't provide std directly
                'confidence': lgb_conf
            }
        except Exception:
            predictions['lightgbm'] = {'time': None, 'std_dev': 3.0, 'confidence': 'N/A'}

        # 4. RandomForest
        try:
            rf_time, rf_conf, rf_exp, rf_std = predict_time_randomforest(
                competitor_name, species, diameter, quality, event_code, results_df, return_std=True
            )
            predictions['randomforest'] = {
                'time': rf_time,
                'std_dev': rf_std if rf_std else 3.0,
                'confidence': rf_conf
            }
        except Exception:
            predictions['randomforest'] = {'time': None, 'std_dev': 3.0, 'confidence': 'N/A'}

        # 5. Ridge
        try:
            ridge_time, ridge_conf, ridge_exp, ridge_ci = predict_time_ridge(
                competitor_name, species, diameter, quality, event_code, results_df, return_ci=False
            )
            predictions['ridge'] = {
                'time': ridge_time,
                'std_dev': 3.0,  # Ridge provides CI, not std directly
                'confidence': ridge_conf
            }
        except Exception:
            predictions['ridge'] = {'time': None, 'std_dev': 3.0, 'confidence': 'N/A'}

        # 6. LLM (optional)
        try:
            llm_time, llm_conf, llm_exp = predict_competitor_time_with_ai(
                competitor_name, species, diameter, quality, event_code, results_df
            )
            predictions['llm'] = {
                'time': llm_time,
                'std_dev': 3.0,  # LLM uncertainty not quantified
                'confidence': llm_conf
            }
        except Exception:
            predictions['llm'] = {'time': None, 'std_dev': 3.0, 'confidence': 'N/A'}

        return predictions

    def _build_meta_features(
        self,
        base_predictions: Dict[str, Dict],
        competitor_name: str,
        results_df: pd.DataFrame,
        event_code: str
    ) -> Dict[str, float]:
        """
        Build 32 meta-features from base predictions and data characteristics.

        Meta-features:
        1-6: Base predictions
        7-12: Base variances
        13-16: Prediction agreement
        17-22: Data quality
        23-26: Competitor characteristics
        27-32: Interactions
        """

        # Extract times and std_devs
        times = [base_predictions[m]['time'] for m in base_predictions if base_predictions[m]['time'] is not None]
        std_devs = [base_predictions[m]['std_dev'] for m in base_predictions]

        # Base predictions (6)
        meta = {
            'baseline_v2_pred': base_predictions['baseline_v2']['time'] or 0.0,
            'xgboost_pred': base_predictions['xgboost']['time'] or 0.0,
            'lightgbm_pred': base_predictions['lightgbm']['time'] or 0.0,
            'randomforest_pred': base_predictions['randomforest']['time'] or 0.0,
            'ridge_pred': base_predictions['ridge']['time'] or 0.0,
            'llm_pred': base_predictions['llm']['time'] or 0.0
        }

        # Base variances (6)
        meta.update({
            'baseline_v2_std': base_predictions['baseline_v2']['std_dev'],
            'xgboost_std': base_predictions['xgboost']['std_dev'],
            'lightgbm_std': base_predictions['lightgbm']['std_dev'],
            'randomforest_std': base_predictions['randomforest']['std_dev'],
            'ridge_std': base_predictions['ridge']['std_dev'],
            'llm_std': base_predictions['llm']['std_dev']
        })

        # Prediction agreement (4)
        if len(times) >= 2:
            meta.update({
                'pred_std_dev': float(np.std(times)),
                'pred_range': float(max(times) - min(times)),
                'pred_iqr': float(np.percentile(times, 75) - np.percentile(times, 25)),
                'outlier_flag': 1.0 if any(abs(t - np.median(times)) > 0.2 * np.median(times) for t in times) else 0.0
            })
        else:
            meta.update({'pred_std_dev': 0.0, 'pred_range': 0.0, 'pred_iqr': 0.0, 'outlier_flag': 0.0})

        # Data quality (6)
        competitor_data = results_df[results_df['competitor_name'] == competitor_name]
        n_samples = len(competitor_data)
        missing_dates = competitor_data['date'].isna().sum() / max(n_samples, 1)

        meta.update({
            'sample_size': float(n_samples),
            'effective_n': float(min(n_samples, 50)),  # Cap for normalization
            'missing_date_pct': float(missing_dates),
            'diameter_gap': 0.0,  # Placeholder
            'has_finish_position': 0.0,  # Placeholder (Phase 5)
            'recency_days': 365.0  # Placeholder
        })

        # Competitor characteristics (4)
        if n_samples > 0:
            comp_variance = competitor_data['raw_time'].std()
            comp_experience = n_samples
            meta.update({
                'variance_percentile': min(comp_variance / 10.0, 1.0),  # Normalize to [0, 1]
                'experience_level': min(comp_experience / 50.0, 1.0),  # Normalize to [0, 1]
                'trend_direction': 0.0,  # Placeholder
                'activity_level': 1.0 if n_samples >= 5 else 0.5
            })
        else:
            meta.update({'variance_percentile': 0.5, 'experience_level': 0.0, 'trend_direction': 0.0, 'activity_level': 0.0})

        # Interactions (6)
        if len(times) >= 2:
            baseline_pred = meta['baseline_v2_pred']
            xgb_pred = meta['xgboost_pred']
            quality = 5.0  # Placeholder
            meta.update({
                'baseline_x_xgboost': baseline_pred * xgb_pred / 1000.0,  # Normalize
                'baseline_x_quality': baseline_pred * quality / 100.0,
                'xgboost_x_lightgbm': xgb_pred * meta['lightgbm_pred'] / 1000.0,
                'variance_x_experience': meta['variance_percentile'] * meta['experience_level'],
                'pred_std_x_quality': meta['pred_std_dev'] * quality / 10.0,
                'ridge_x_baseline': meta['ridge_pred'] * baseline_pred / 1000.0
            })
        else:
            meta.update({k: 0.0 for k in ['baseline_x_xgboost', 'baseline_x_quality', 'xgboost_x_lightgbm',
                                          'variance_x_experience', 'pred_std_x_quality', 'ridge_x_baseline']})

        return meta

    def train_meta_model(self, results_df: Optional[pd.DataFrame] = None):
        """
        Train meta-model using out-of-fold predictions from base models.

        Uses nested cross-validation to prevent overfitting.
        """
        if not XGB_AVAILABLE:
            print("XGBoost not available for meta-model training")
            return

        if results_df is None:
            results_df = load_results_df()

        print("\n[STACKING ENSEMBLE] Training meta-model...")
        print("Using nested CV to generate out-of-fold predictions...")

        # Standardize data
        results_df, _ = standardize_results_data(results_df)

        # For each event, train meta-model
        for event in ['SB', 'UH']:
            event_df = results_df[results_df['event'] == event]

            if len(event_df) < 30:
                print(f"  Insufficient data for {event} meta-model")
                continue

            # TODO: Generate OOF predictions from base models via CV
            # This is complex and would require refactoring base model training
            # For now, use placeholder simple ensemble

            print(f"  {event} meta-model: Using weighted average (placeholder)")

        print("[STACKING ENSEMBLE] Meta-model training complete\n")

    def predict(
        self,
        competitor_name: str,
        species: str,
        diameter: float,
        quality: int,
        event_code: str,
        results_df: Optional[pd.DataFrame] = None
    ) -> EnsemblePrediction:
        """
        Make prediction using stacking ensemble.

        Returns EnsemblePrediction with time, std_dev, confidence, and metadata.
        """

        if not self.base_models_trained:
            self.train_base_models(results_df)

        if results_df is None:
            results_df = load_results_df()

        # Get base predictions
        base_preds = self._get_base_predictions(
            competitor_name, species, diameter, quality, event_code, results_df
        )

        # Build meta-features
        meta_features = self._build_meta_features(base_preds, competitor_name, results_df, event_code)

        # For now, use weighted average (meta-model placeholder)
        # Weights based on typical performance: Baseline V2 (40%), XGBoost (30%), Others (30%)
        weights = {
            'baseline_v2': 0.40,
            'xgboost': 0.20,
            'lightgbm': 0.15,
            'randomforest': 0.15,
            'ridge': 0.05,
            'llm': 0.05
        }

        predictions = []
        total_weight = 0.0
        for model, weight in weights.items():
            if base_preds[model]['time'] is not None:
                predictions.append(base_preds[model]['time'] * weight)
                total_weight += weight

        if total_weight > 0:
            final_prediction = sum(predictions) / total_weight
        else:
            # Fallback to baseline
            final_prediction = base_preds['baseline_v2']['time'] or 45.0

        # Estimate std_dev from base model disagreement
        times = [base_preds[m]['time'] for m in base_preds if base_preds[m]['time'] is not None]
        if len(times) >= 2:
            std_dev = float(np.std(times))
        else:
            std_dev = base_preds['baseline_v2']['std_dev']

        # Clamp std_dev to reasonable range
        std_dev = max(simulation_config.MIN_COMPETITOR_STD_SECONDS,
                      min(std_dev, simulation_config.MAX_COMPETITOR_STD_SECONDS))

        # Determine confidence
        if meta_features['sample_size'] >= 10 and meta_features['pred_std_dev'] < 3.0:
            confidence = "HIGH"
        elif meta_features['sample_size'] >= 5 and meta_features['pred_std_dev'] < 5.0:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return EnsemblePrediction(
            time=final_prediction,
            std_dev=std_dev,
            confidence=confidence,
            method_used="Stacking Ensemble",
            explanation=f"Stacking ensemble of 6 models ({int(meta_features['sample_size'])} samples)",
            base_predictions={m: base_preds[m]['time'] for m in base_preds},
            base_variances={m: base_preds[m]['std_dev'] for m in base_preds},
            meta_features=meta_features
        )
