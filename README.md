#  FLO CLTV Prediction

FLO müşterilerinin gelecekte şirkete sağlayacağı potansiyel değeri
**BG/NBD** ve **Gamma-Gamma** modelleriyle tahmin eden, müşterileri
segmentlere ayıran uçtan uca bir makine öğrenmesi pipeline'ı.

---

## İçindekiler

- [Proje Hakkında](#proje-hakkında)
- [Proje Yapısı](#proje-yapısı)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Metodoloji](#metodoloji)
- [Segment Tanımları](#segment-tanımları)
- [Çıktılar](#çıktılar)

---

## Proje Hakkında

**Veri Seti:** 2020–2021 yılları arasında hem online hem offline (OmniChannel)
alışveriş yapan FLO müşterilerinin geçmiş davranış verileri (~20.000 müşteri).

**Amaç:** Şirketin orta-uzun vadeli pazarlama roadmap'i oluşturabilmesi için
her müşterinin 6 aylık tahmini yaşam boyu değerini (CLTV) hesaplamak ve
müşterileri bu değere göre segmentlere ayırmak.

---

## Proje Yapısı

```
flo_cltv/
│
├── config.yaml               # Tüm parametreler tek yerden
├── main.py                   # Pipeline giriş noktası
├── requirements.txt
├── .gitignore
│
├── data/
│   └── raw/
│       └── flo_data_20K.csv  # Ham veri (git'e eklenmez)
│
├── src/
│   ├── __init__.py
│   ├── logger.py             # Merkezi logging
│   ├── data_loader.py        # Veri yükleme, aykırı değer, ön işleme
│   └── cltv.py               # BG/NBD + Gamma-Gamma pipeline
│
├── notebooks/
│   └── eda.ipynb             # Keşifsel veri analizi
│
├── outputs/
│   └── exports/              # CLTV çıktı CSV'si
│
└── logs/                     # Çalışma logları
```

---

## Kurulum

```bash
# 1. Repoyu klonla
git clone https://github.com/kullaniciadi/flo-cltv.git
cd flo-cltv

# 2. Sanal ortam oluştur
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Ham veriyi yerleştir
cp /yol/flo_data_20K.csv data/raw/
```

---

## Kullanım

### Pipeline'ı çalıştır

```bash
python main.py
```

Tüm adımları sırasıyla işler ve çıktıyı `outputs/exports/cltv_output.csv`
olarak kaydeder.

### Parametreleri değiştir

Kodu açmadan `config.yaml` üzerinden ayarlama yapılabilir:

```yaml
analysis:
  analysis_date: "2021-06-01"
  penalizer_bgf: 0.001
  penalizer_ggf: 0.01
  discount_rate: 0.01
  prediction_months: [3, 6]
  n_segments: 4
```

### Notebook

```bash
jupyter lab notebooks/eda.ipynb
```

### Modülleri doğrudan kullan

```python
import yaml
from src.data_loader import load_data, preprocess
from src.cltv import create_cltv_df

with open("config.yaml") as f:
    config = yaml.safe_load(f)

df = preprocess(load_data(config["data"]["raw_path"]), config["outlier_cols"])
cltv_df = create_cltv_df(df, **config["analysis"])
print(cltv_df.head())
```

---

## Metodoloji

### 1. Veri Ön İşleme

Online ve offline sipariş/harcama değerleri toplanarak müşteri bazında
birleştirilir. Dört sayısal değişkende IQR yöntemiyle aykırı değerler
%1–%99 eşiklerine baskılanır (frequency integer olmalıdır).

### 2. CLTV Veri Yapısı

| Değişken | Açıklama |
|---|---|
| `recency_cltv_weekly` | İlk ve son alışveriş arasındaki süre (hafta) |
| `T_weekly` | Müşterinin şirketle geçirdiği toplam süre (hafta) |
| `frequency` | Toplam tekrar satın alma sayısı (> 1) |
| `monetary_cltv_avg` | Satın alma başına ortalama harcama (₺) |

### 3. BG/NBD Modeli

Müşterinin gelecekte kaç satın alma yapacağını tahmin eder.
Her müşteri için ayrı ayrı aktif olma olasılığı ve beklenen satın alma
sayısı hesaplanır.

- 3 aylık tahmin → `exp_sales_3_month`
- 6 aylık tahmin → `exp_sales_6_month`

### 4. Gamma-Gamma Modeli

Aktif bir müşterinin satın alma başına bırakacağı ortalama değeri tahmin
eder. BG/NBD ile birleştirilerek 6 aylık CLTV üretilir.

```
CLTV = BG/NBD (beklenen satın alma) × Gamma-Gamma (beklenen değer)
```

---

## Segment Tanımları

Müşteriler 6 aylık CLTV skoruna göre `pd.qcut` ile 4 eşit gruba ayrılır:

| Segment | Tanım | Önerilen Aksiyon |
|---|---|---|
| **A** | En yüksek CLTV — şirketin en değerli müşterileri | Sadakat programları, özel kampanyalar, erken erişim teklifleri |
| **B** | Yüksek potansiyelli müşteriler | Cross-sell / upsell fırsatları, kişiselleştirilmiş öneriler |
| **C** | Orta segment — geliştirilebilir | Aktivasyon kampanyaları, kategori genişletme teklifleri |
| **D** | Düşük CLTV — yeni veya seyrek alışveriş yapanlar | Düşük maliyetli dokunuşlar, yeniden aktivasyon e-postaları |

---

## Çıktılar

### `outputs/exports/cltv_output.csv`

| Sütun | Açıklama |
|---|---|
| `customer_id` | Eşsiz müşteri numarası |
| `recency_cltv_weekly` | Recency (hafta) |
| `T_weekly` | Müşteri yaşı (hafta) |
| `frequency` | Satın alma sayısı |
| `monetary_cltv_avg` | Ortalama sepet değeri (₺) |
| `exp_sales_3_month` | 3 aylık beklenen satın alma |
| `exp_sales_6_month` | 6 aylık beklenen satın alma |
| `exp_average_value` | Beklenen ortalama sipariş değeri |
| `cltv` | 6 aylık CLTV tahmini |
| `cltv_segment` | A / B / C / D segmenti |

### `logs/cltv_pipeline.log`

Her çalışmada pipeline adımları, uyarılar ve hata mesajları buraya yazılır.