import re
import pandas as pd
import numpy as np
from pathlib import Path

# 0. CẤU HÌNH
INPUT_FILE  = "data/shopee_sale_5_5_data.xlsx"   # file gốc
OUTPUT_FILE = "data/shopee_cleaned.xlsx"          # file sạch
SHEET_NAME  = 0                              # 0 = sheet đầu tiên

# 1. ĐỌC DỮ LIỆU
print("📂 Đang đọc file...")
df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME, dtype=str)

# Loại bỏ khoảng trắng thừa ở tên cột
df.columns = df.columns.str.strip()

print(f"   → {len(df)} dòng, {len(df.columns)} cột")
print(f"   → Các cột: {list(df.columns)}\n")

# 2. CHUẨN HÓA campaign_name
print("🏷  Chuẩn hóa campaign_name...")

def normalize_campaign(name: str) -> str:
    if pd.isna(name):
        return np.nan
    # Loại bỏ khoảng trắng, chuyển về lowercase để so sánh
    n = str(name).strip().lower()
    # Regex bắt các biến thể: "super flash sale 5.5", "shopee 5.5", v.v.
    if re.search(r"(super\s*flash|flash\s*sale)", n):
        return "Super Flash Sale 5.5"
    if re.search(r"shopee\s*(mega\s*)?sale\s*5\.5", n):
        return "Shopee Sale 5.5"
    if re.search(r"shopee\s*mega\s*sale\s*5\.5", n):
        return "Shopee Mega Sale 5.5"
    if re.search(r"shopee\s*5\.5\s*flash\s*sale", n):
        return "Shopee 5.5 Flash Sale"
    # Giữ nguyên nếu không nhận dạng được
    return str(name).strip()

df["campaign_name"] = df["campaign_name"].apply(normalize_campaign)
print(f"   → Các giá trị duy nhất: {df['campaign_name'].unique()}\n")


# 3. CHUẨN HÓA platform
#    fb/FB/Facebook/FaceBook → "Facebook Ads"
#    gg/GG/google/GOOGLE     → "Google Ads"
#    insta/ig/IG/Instagram   → "Instagram"
#    tiktok/TikTok/tiktok ads → "TikTok Ads"
#    SP Ads/sp ads           → "Shopee Ads"
print("📱 Chuẩn hóa platform...")

# Mapping: key là regex pattern (lowercase), value là tên chuẩn
PLATFORM_MAP = {
    r"^(fb|facebook|facebook_ads|facebook\s*ads)$": "Facebook Ads",
    r"^(ig|insta|instagram|instagram\s*ads)$":       "Instagram",
    r"^(gg|google|google\s*ads)$":                   "Google Ads",
    r"^(tiktok|tik\s*tok|tiktok\s*ads|tt|tt\s*ads)$":"TikTok Ads",
    r"^(sp\s*ads|shopee\s*ads|shopee)$":             "Shopee Ads",
    r"^youtube":                                     "YouTube Ads",
}

def normalize_platform(val: str) -> str:
    if pd.isna(val):
        return np.nan
    v = str(val).strip().lower()
    for pattern, standard in PLATFORM_MAP.items():
        if re.match(pattern, v):
            return standard
    # Trả về dạng title case nếu không match
    return str(val).strip().title()

df["platform"] = df["platform"].apply(normalize_platform)
print(f"   → Các platform sau khi chuẩn hóa: {sorted(df['platform'].dropna().unique())}\n")

# 4. CHUẨN HÓA CÁC CỘT SỐ
print("🔢 Chuẩn hóa các cột số...")

NUMERIC_COLS = ["spend", "clicks", "impressions", "conversions", "revenue"]

# Bộ chuyển đổi tiếng Anh
WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    "one hundred": 100, "two hundred": 200,
}

NULL_VALUES = {"n/a", "na", "null", "none", "-", "", "nan", "#n/a", "missing"}

def parse_number(val) -> float:
    """Chuyển đổi mọi dạng chuỗi số về float, trả về np.nan nếu không hợp lệ."""
    if pd.isna(val):
        return np.nan

    raw = str(val).strip()

    # Kiểm tra null/N/A
    if raw.lower() in NULL_VALUES:
        return np.nan

    # Thử chuyển text tiếng Anh
    if raw.lower() in WORD_TO_NUM:
        return float(WORD_TO_NUM[raw.lower()])

    # Loại bỏ ký tự không phải số (giữ dấu chấm, dấu phẩy, ký tự k/K/m/M)
    cleaned = re.sub(r"[^0-9.,kKmMbB\-]", "", raw)

    if not cleaned:
        return np.nan

    # Xử lý dấu chấm/phẩy theo kiểu châu Âu hay Mỹ
    # Nếu có cả hai: "1,035.50" → kiểu Mỹ; "1.035,50" → kiểu EU
    if "," in cleaned and "." in cleaned:
        # Xác định vị trí: dấu cuối là thập phân
        if cleaned.rfind(",") > cleaned.rfind("."):
            # EU style: "1.035,50" → "1035.50"
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # US style: "1,035.50" → "1035.50"
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Chỉ có dấu phẩy: kiểm tra xem có phải thập phân không
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # "1,5" → thập phân
            cleaned = cleaned.replace(",", ".")
        else:
            # "1,035" → phân cách nghìn
            cleaned = cleaned.replace(",", "")

    # Xử lý k/K (nghìn), m/M (triệu)
    multiplier = 1
    if cleaned.lower().endswith("k"):
        multiplier = 1_000
        cleaned = cleaned[:-1]
    elif cleaned.lower().endswith("m"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]
    elif cleaned.lower().endswith("b"):
        multiplier = 1_000_000_000
        cleaned = cleaned[:-1]

    try:
        return float(cleaned) * multiplier
    except ValueError:
        return np.nan


for col in NUMERIC_COLS:
    if col not in df.columns:
        print(f"   Không tìm thấy cột '{col}', bỏ qua.")
        continue

    original_nulls = df[col].isna().sum()
    df[col] = df[col].apply(parse_number)
    new_nulls = df[col].isna().sum()

    print(f"   {col}: {new_nulls} giá trị null "
          f"(trước: {original_nulls}, mới: {new_nulls - original_nulls})")

    # Ép kiểu về float
    df[col] = pd.to_numeric(df[col], errors="coerce")

print()


# 5. CHUẨN HÓA DATE
#    "2024-05-06", "05-02-2024", "May 6 2024",
#    "May 2 2024", "09/05/2024", "May-09-2024",
#    "Apr 28 2024", "9-May-2024", v.v.
print("📅 Chuẩn hóa cột date...")

def normalize_date(val) -> pd.Timestamp:
    if pd.isna(val):
        return pd.NaT
    s = str(val).strip()
    if s.lower() in NULL_VALUES:
        return pd.NaT

    # Loại bỏ các ký tự lạ phổ biến: dấu "." thay cho "-"
    s = re.sub(r"(\d{4})\.(\d{2})\.(\d{2})", r"\1-\2-\3", s)

    # Thử nhiều định dạng phổ biến
    formats = [
        "%Y-%m-%d",      # 2024-05-06
        "%d-%m-%Y",      # 06-05-2024
        "%m-%d-%Y",      # 05-06-2024
        "%d/%m/%Y",      # 06/05/2024
        "%m/%d/%Y",      # 05/06/2024
        "%Y/%m/%d",      # 2024/05/06
        "%B %d %Y",      # May 06 2024
        "%b %d %Y",      # May 6 2024
        "%d-%b-%Y",      # 06-May-2024
        "%d %b %Y",      # 06 May 2024
        "%b-%d-%Y",      # May-06-2024
        "%d %B %Y",      # 06 May 2024 (full)
        "%Y%m%d",        # 20240506
        "%m.%d.%Y",      # 05.06.2024
        "%d.%m.%Y",      # 06.05.2024
    ]

    for fmt in formats:
        try:
            return pd.to_datetime(s, format=fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(s, dayfirst=True)
    except Exception:
        return pd.NaT

df["date"] = df["date"].apply(normalize_date)

# Chuyển về định dạng date thuần
df["date"] = pd.to_datetime(df["date"]).dt.date

null_dates = df["date"].isna().sum()
print(f"   → {null_dates} dòng không parse được date\n")

# 6. XỬ LÝ BỔ SUNG
print("🧹 Xử lý bổ sung...")

# Chuẩn hóa ad_set (strip khoảng trắng)
if "ad_set" in df.columns:
    df["ad_set"] = df["ad_set"].str.strip()

# Chuẩn hóa campaign_id (strip)
if "campaign_id" in df.columns:
    df["campaign_id"] = df["campaign_id"].str.strip().str.upper()

# Số: fill bằng median của cùng platform
for col in ["spend", "clicks", "impressions", "conversions", "revenue"]:
    df[col] = df.groupby("platform")[col].transform(
        lambda x: x.fillna(x.median() if x.notna().any() else df[col].median())
    )
print("\n Kiểm tra null sau khi fill:")
print(df[NUMERIC_COLS].isnull().sum())

# Date: drop riêng dòng null date
df = df.dropna(subset=["date"])  # date null không có cách fill hợp lý

# Loại bỏ dòng hoàn toàn trống
before = len(df)
df.dropna(how="all", inplace=True)
print(f"   → Xóa {before - len(df)} dòng hoàn toàn trống\n")

# 7. XUẤT FILE
print(f"\n💾 Xuất file ra '{OUTPUT_FILE}'...")
 
with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl", datetime_format="YYYY-MM-DD") as writer:
    df.to_excel(writer, index=False, sheet_name="cleaned_data")
 
print(f"✅ Hoàn thành! → {OUTPUT_FILE}")