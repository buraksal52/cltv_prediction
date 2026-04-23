"""
FLO CLTV Prediction — Ana Pipeline

Kullanım:
    python main.py
    python main.py --config config.yaml
"""

import argparse
from pathlib import Path
import yaml

from src.logger import get_logger
from src.data_loader import load_data, preprocess
from src.cltv import create_cltv_df


def parse_args():
    parser = argparse.ArgumentParser(description="FLO CLTV Pipeline")
    parser.add_argument("--config", default="config.yaml")
    return parser.parse_args()


def run(config: dict):
    logger = get_logger(__name__, log_file="logs/cltv_pipeline.log")
    logger.info("=" * 60)
    logger.info("FLO CLTV Pipeline başlatıldı.")
    logger.info("=" * 60)

    df_raw = load_data(config["data"]["raw_path"])
    df = preprocess(df_raw, outlier_cols=config["outlier_cols"])

    cfg = config["analysis"]
    cltv_df = create_cltv_df(
        df,
        analysis_date=cfg["analysis_date"],
        penalizer_bgf=cfg["penalizer_bgf"],
        penalizer_ggf=cfg["penalizer_ggf"],
        discount_rate=cfg["discount_rate"],
        prediction_months=cfg["prediction_months"],
        n_segments=cfg["n_segments"],
    )

    out = config["data"]["processed_path"]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cltv_df.to_csv(out, index=False)
    logger.info(f"Çıktı kaydedildi → {out}")

    logger.info("Pipeline tamamlandı.")
    return cltv_df


if __name__ == "__main__":
    args = parse_args()
    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    run(config)