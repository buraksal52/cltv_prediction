"""
Unit testler — çalıştırmak için:
    pytest tests/ -v
"""

import datetime as dt
import pandas as pd
import pytest

from src.data_loader import outlier_thresholds, replace_with_thresholds, preprocess
from src.cltv import build_cltv_dataframe, fit_bgf, fit_ggf, assign_segments, create_cltv_df


# ─── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def raw_df():
    """Minimal geçerli ham DataFrame."""
    return pd.DataFrame({
        "master_id": [f"C{i}" for i in range(20)],
        "order_channel": ["Android"] * 20,
        "last_order_channel": ["Android"] * 20,
        "first_order_date": ["2020-01-01"] * 20,
        "last_order_date": ["2021-01-01"] * 10 + ["2021-04-01"] * 10,
        "last_order_date_online": ["2021-01-01"] * 20,
        "last_order_date_offline": ["2021-01-01"] * 20,
        "order_num_total_ever_online": [3, 5, 2, 8, 4, 6, 3, 7, 2, 5,
                                        4, 3, 6, 2, 5, 8, 3, 4, 7, 2],
        "order_num_total_ever_offline": [2, 3, 1, 4, 2, 3, 1, 3, 1, 2,
                                         2, 1, 3, 1, 2, 4, 1, 2, 3, 1],
        "customer_value_total_ever_online": [300, 500, 200, 800, 400, 600, 300, 700, 200, 500,
                                             400, 300, 600, 200, 500, 800, 300, 400, 700, 200],
        "customer_value_total_ever_offline": [100, 200, 80, 300, 150, 200, 100, 250, 80, 150,
                                              150, 100, 200, 80, 150, 300, 100, 150, 250, 80],
        "interested_in_categories_12": ["[KADIN]"] * 20,
    })


@pytest.fixture
def processed_df(raw_df):
    outlier_cols = [
        "order_num_total_ever_online",
        "order_num_total_ever_offline",
        "customer_value_total_ever_offline",
        "customer_value_total_ever_online",
    ]
    return preprocess(raw_df, outlier_cols)


@pytest.fixture
def cltv_df(processed_df):
    return build_cltv_dataframe(processed_df, analysis_date="2021-06-01")


@pytest.fixture
def full_cltv_df(processed_df):
    return create_cltv_df(processed_df, analysis_date="2021-06-01")


# ─── data_loader testleri ────────────────────────────────────

class TestOutlierThresholds:
    def test_dönen_değerler_tuple(self, raw_df):
        result = outlier_thresholds(raw_df, "order_num_total_ever_online")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_alt_limit_ust_limitten_kucuk(self, raw_df):
        low, up = outlier_thresholds(raw_df, "order_num_total_ever_online")
        assert low < up


class TestPreprocess:
    def test_toplam_siparis_hesabi(self, processed_df):
        row = processed_df.iloc[0]
        assert row["order_num_total"] == (
            row["order_num_total_ever_online"] + row["order_num_total_ever_offline"]
        )

    def test_toplam_harcama_hesabi(self, processed_df):
        row = processed_df.iloc[0]
        assert row["customer_value_total"] == (
            row["customer_value_total_ever_online"] + row["customer_value_total_ever_offline"]
        )

    def test_tarih_sutunlari_datetime(self, processed_df):
        assert pd.api.types.is_datetime64_any_dtype(processed_df["last_order_date"])
        assert pd.api.types.is_datetime64_any_dtype(processed_df["first_order_date"])

    def test_orijinal_degismez(self, raw_df):
        outlier_cols = ["order_num_total_ever_online", "order_num_total_ever_offline",
                        "customer_value_total_ever_offline", "customer_value_total_ever_online"]
        _ = preprocess(raw_df, outlier_cols)
        assert "order_num_total" not in raw_df.columns


# ─── cltv testleri ───────────────────────────────────────────

class TestBuildCltvDataframe:
    def test_sutunlar_mevcut(self, cltv_df):
        expected = {"customer_id", "recency_cltv_weekly", "T_weekly",
                    "frequency", "monetary_cltv_avg"}
        assert expected.issubset(cltv_df.columns)

    def test_recency_pozitif_veya_sifir(self, cltv_df):
        assert (cltv_df["recency_cltv_weekly"] >= 0).all()

    def test_t_weekly_pozitif(self, cltv_df):
        assert (cltv_df["T_weekly"] > 0).all()

    def test_frequency_birden_buyuk(self, cltv_df):
        assert (cltv_df["frequency"] > 1).all()

    def test_monetary_pozitif(self, cltv_df):
        assert (cltv_df["monetary_cltv_avg"] > 0).all()

    def test_string_tarih_kabul(self, processed_df):
        df = build_cltv_dataframe(processed_df, analysis_date="2021-06-01")
        assert len(df) > 0

    def test_datetime_tarih_kabul(self, processed_df):
        df = build_cltv_dataframe(processed_df, analysis_date=dt.datetime(2021, 6, 1))
        assert len(df) > 0


class TestFitModels:
    def test_bgf_fit(self, cltv_df):
        bgf = fit_bgf(cltv_df)
        assert bgf.params_ is not None

    def test_ggf_fit(self, cltv_df):
        ggf = fit_ggf(cltv_df)
        assert ggf.params_ is not None


class TestAssignSegments:
    def test_segment_sutunu_var(self, full_cltv_df):
        assert "cltv_segment" in full_cltv_df.columns

    def test_segment_değerleri(self, full_cltv_df):
        assert set(full_cltv_df["cltv_segment"].unique()).issubset({"A", "B", "C", "D"})

    def test_tum_satirlarda_segment(self, full_cltv_df):
        assert full_cltv_df["cltv_segment"].notna().all()


class TestCreateCltvDf:
    def test_cikti_sutunlari(self, full_cltv_df):
        expected = {"customer_id", "recency_cltv_weekly", "T_weekly",
                    "frequency", "monetary_cltv_avg", "exp_sales_3_month",
                    "exp_sales_6_month", "exp_average_value", "cltv", "cltv_segment"}
        assert expected.issubset(full_cltv_df.columns)

    def test_cltv_pozitif(self, full_cltv_df):
        assert (full_cltv_df["cltv"] > 0).all()

    def test_6_ay_3_aydan_buyuk(self, full_cltv_df):
        assert (full_cltv_df["exp_sales_6_month"] >= full_cltv_df["exp_sales_3_month"]).all()