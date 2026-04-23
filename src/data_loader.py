"""
Veri yükleme, aykırı değer baskılama ve ön işleme.
"""

import pandas as pd
from pathlib import Path
from src.logger import get_logger

logger = get_logger(__name__)


def outlier_thresholds(dataframe: pd.DataFrame, variable: str) -> tuple:
    q1 = dataframe[variable].quantile(0.01)
    q3 = dataframe[variable].quantile(0.99)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def replace_with_thresholds(dataframe: pd.DataFrame, variable: str) -> None:
    low, up = outlier_thresholds(dataframe, variable)
    dataframe.loc[dataframe[variable] < low, variable] = round(low, 0)
    dataframe.loc[dataframe[variable] > up, variable] = round(up, 0)


def load_data(path: str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dosya bulunamadı: {path}")
    df = pd.read_csv(path)
    logger.info(f"Veri yüklendi — {df.shape[0]:,} satır, {df.shape[1]} sütun")
    return df


def preprocess(df: pd.DataFrame, outlier_cols: list) -> pd.DataFrame:
    df = df.copy()

    for col in outlier_cols:
        replace_with_thresholds(df, col)
    logger.info("Aykırı değerler baskılandı.")

    df["order_num_total"] = (
        df["order_num_total_ever_online"] + df["order_num_total_ever_offline"]
    )
    df["customer_value_total"] = (
        df["customer_value_total_ever_online"] + df["customer_value_total_ever_offline"]
    )

    date_cols = df.columns[df.columns.str.contains("date")]
    df[date_cols] = df[date_cols].apply(pd.to_datetime)
    logger.info("Ön işleme tamamlandı.")
    return df