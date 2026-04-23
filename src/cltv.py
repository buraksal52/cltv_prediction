"""
BG/NBD + Gamma-Gamma ile CLTV hesaplama ve segmentasyon.
"""

import datetime as dt
import pandas as pd
from lifetimes import BetaGeoFitter, GammaGammaFitter
from src.logger import get_logger

logger = get_logger(__name__)


def build_cltv_dataframe(df: pd.DataFrame, analysis_date: str | dt.datetime) -> pd.DataFrame:
    """
    Ham veriden CLTV model girdilerini hazırlar.
    Frequency > 1 olan müşteriler alınır (model gereği).
    """
    if isinstance(analysis_date, str):
        analysis_date = pd.to_datetime(analysis_date)

    cltv_df = pd.DataFrame()
    cltv_df["customer_id"] = df["master_id"]
    cltv_df["recency_cltv_weekly"] = (
        (df["last_order_date"] - df["first_order_date"]).dt.days / 7
    )
    cltv_df["T_weekly"] = (
        (analysis_date - df["first_order_date"]).dt.days / 7
    )
    cltv_df["frequency"] = df["order_num_total"]
    cltv_df["monetary_cltv_avg"] = df["customer_value_total"] / df["order_num_total"]

    # Geçersiz kayıtları çıkar
    cltv_df = cltv_df[cltv_df["frequency"] > 1].reset_index(drop=True)
    logger.info(f"CLTV DataFrame hazır — {len(cltv_df):,} müşteri (frequency > 1)")
    return cltv_df


def fit_bgf(cltv_df: pd.DataFrame, penalizer: float = 0.001) -> BetaGeoFitter:
    bgf = BetaGeoFitter(penalizer_coef=penalizer)
    bgf.fit(cltv_df["frequency"], cltv_df["recency_cltv_weekly"], cltv_df["T_weekly"])
    logger.info("BG/NBD modeli fit edildi.")
    return bgf


def fit_ggf(cltv_df: pd.DataFrame, penalizer: float = 0.01) -> GammaGammaFitter:
    ggf = GammaGammaFitter(penalizer_coef=penalizer)
    ggf.fit(cltv_df["frequency"], cltv_df["monetary_cltv_avg"])
    logger.info("Gamma-Gamma modeli fit edildi.")
    return ggf


def predict_purchases(
    cltv_df: pd.DataFrame,
    bgf: BetaGeoFitter,
    months: list[int],
) -> pd.DataFrame:
    """Her ay için beklenen satın alma tahminini ekler."""
    for m in months:
        col = f"exp_sales_{m}_month"
        cltv_df[col] = bgf.predict(
            4 * m,
            cltv_df["frequency"],
            cltv_df["recency_cltv_weekly"],
            cltv_df["T_weekly"],
        )
        logger.info(f"{m} aylık satış tahmini eklendi.")
    return cltv_df


def predict_cltv(
    cltv_df: pd.DataFrame,
    bgf: BetaGeoFitter,
    ggf: GammaGammaFitter,
    time: int = 6,
    discount_rate: float = 0.01,
) -> pd.DataFrame:
    """Ortalama değer ve 6 aylık CLTV tahminlerini ekler."""
    cltv_df["exp_average_value"] = ggf.conditional_expected_average_profit(
        cltv_df["frequency"], cltv_df["monetary_cltv_avg"]
    )
    cltv_df["cltv"] = ggf.customer_lifetime_value(
        bgf,
        cltv_df["frequency"],
        cltv_df["recency_cltv_weekly"],
        cltv_df["T_weekly"],
        cltv_df["monetary_cltv_avg"],
        time=time,
        freq="W",
        discount_rate=discount_rate,
    )
    logger.info(f"{time} aylık CLTV hesaplandı.")
    return cltv_df


def assign_segments(cltv_df: pd.DataFrame, n_segments: int = 4) -> pd.DataFrame:
    labels = [chr(ord("A") + n_segments - 1 - i) for i in range(n_segments)][::-1]
    # ["D","C","B","A"] için n_segments=4
    labels = sorted(labels, reverse=True)
    cltv_df["cltv_segment"] = pd.qcut(cltv_df["cltv"], n_segments, labels=labels)
    counts = cltv_df["cltv_segment"].value_counts().sort_index()
    logger.info(f"Segmentler oluşturuldu:\n{counts.to_string()}")
    return cltv_df


def create_cltv_df(
    df: pd.DataFrame,
    analysis_date: str,
    penalizer_bgf: float = 0.001,
    penalizer_ggf: float = 0.01,
    discount_rate: float = 0.01,
    prediction_months: list[int] = None,
    n_segments: int = 4,
) -> pd.DataFrame:
    """Tek fonksiyonda uçtan uca CLTV pipeline'ı."""
    if prediction_months is None:
        prediction_months = [3, 6]

    cltv_df = build_cltv_dataframe(df, analysis_date)
    bgf = fit_bgf(cltv_df, penalizer_bgf)
    ggf = fit_ggf(cltv_df, penalizer_ggf)
    cltv_df = predict_purchases(cltv_df, bgf, prediction_months)
    cltv_df = predict_cltv(cltv_df, bgf, ggf, time=6, discount_rate=discount_rate)
    cltv_df = assign_segments(cltv_df, n_segments)
    return cltv_df