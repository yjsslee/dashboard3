import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="삼성전자 오늘 주가", page_icon="📈", layout="wide")

API_BASE = "https://api.kiwoom.com"
MOCK_API_BASE = "https://mockapi.kiwoom.com"
TOKEN_PATH = "/oauth2/token"
STOCK_INFO_PATH = "/api/dostk/stkinfo"
CHART_PATH = "/api/dostk/chart"


def get_secret(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return value or os.getenv(name, "")


def get_access_token(app_key: str, app_secret: str, base_url: str) -> str:
    response = requests.post(
        base_url + TOKEN_PATH,
        headers={"Content-Type": "application/json;charset=UTF-8"},
        json={
            "grant_type": "client_credentials",
            "appkey": app_key,
            "secretkey": app_secret,
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("return_code", 0) not in (0, "0", None):
        raise RuntimeError(data.get("return_msg", "토큰 발급에 실패했습니다."))
    if not data.get("token"):
        raise RuntimeError(data.get("return_msg", "접근토큰이 응답되지 않았습니다."))
    return data["token"]


def api_post(base_url, token, api_id, path, payload):
    response = requests.post(
        base_url + path,
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "api-id": api_id,
        },
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("return_code", 0) not in (0, "0", None):
        raise RuntimeError(data.get("return_msg", f"{api_id} 조회에 실패했습니다."))
    return data


@st.cache_data(ttl=30, show_spinner=False)
def get_dashboard_data(app_key, app_secret, use_mock):
    base_url = MOCK_API_BASE if use_mock else API_BASE
    token = get_access_token(app_key, app_secret, base_url)
    info = api_post(base_url, token, "ka10001", STOCK_INFO_PATH, {"stk_cd": "005930"})

    # 키움 차트 API는 일봉 데이터를 반환합니다. 최근 거래일을 기준으로 조회합니다.
    today = datetime.now().strftime("%Y%m%d")
    chart = api_post(
        base_url,
        token,
        "ka10081",
        CHART_PATH,
        {"stk_cd": "005930", "base_dt": today, "upd_stkpc_tp": "1"},
    )
    return info, chart


def first_value(data, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def fmt_number(value):
    if value in (None, ""):
        return "-"
    text = str(value).strip().replace(",", "")
    try:
        if "." in text:
            return f"{float(text):,.2f}"
        return f"{int(float(text)):,}"
    except ValueError:
        return str(value)


def to_positive_number(value):
    if value in (None, ""):
        return None
    try:
        return abs(float(str(value).replace(",", "")))
    except ValueError:
        return None


def extract_chart_df(raw):
    rows = None
    for key in ("stk_dt_pole", "stk_dt", "output", "data"):
        if isinstance(raw.get(key), list):
            rows = raw[key]
            break
    if rows is None:
        rows = []

    records = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        date = first_value(row, "dt", "date", "일자", "stck_bsop_date")
        close = first_value(row, "cur_prc", "현재가", "close", "종가")
        if not date or close in (None, ""):
            continue
        records.append(
            {
                "날짜": str(date),
                "종가": to_positive_number(close),
            }
        )

    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["날짜"] = pd.to_datetime(df["날짜"], format="%Y%m%d", errors="coerce")
    df["종가"] = pd.to_numeric(df["종가"], errors="coerce")
    df = df.dropna().drop_duplicates("날짜").sort_values("날짜").tail(120)
    return df.set_index("날짜")


st.title("삼성전자 오늘 주가 대시보드")
st.caption("키움증권 REST API · 삼성전자 005930")

with st.sidebar:
    st.subheader("API 설정")
    use_mock = st.toggle("모의투자 서버 사용", value=True)
    st.info(
        "API Key/Secret은 GitHub에 저장하지 않습니다.\n\n"
        "Streamlit Cloud의 Secrets에 KIWOOM_APP_KEY와 KIWOOM_APP_SECRET을 등록하세요."
    )

app_key = get_secret("KIWOOM_APP_KEY")
app_secret = get_secret("KIWOOM_APP_SECRET")

if not app_key or not app_secret:
    st.warning("키움증권 App Key와 App Secret이 설정되지 않았습니다.")
    st.code('KIWOOM_APP_KEY = "여기에_App_Key"\nKIWOOM_APP_SECRET = "여기에_App_Secret"', language="toml")
    st.stop()

if st.button("🔄 최신 데이터 조회", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("키움증권에서 삼성전자 데이터를 조회하고 있습니다..."):
        raw, chart_raw = get_dashboard_data(app_key, app_secret, use_mock)

    price = first_value(raw, "cur_prc", "현재가", "lastPrice", "last_prc")
    change = first_value(raw, "pre_rt", "전일대비등락율", "chg_rt")
    change_price = first_value(raw, "pred_pre", "전일대비", "pre_diff")
    high = first_value(raw, "high_pric", "고가")
    low = first_value(raw, "low_pric", "저가")
    open_price = first_value(raw, "open_pric", "시가")
    volume = first_value(raw, "trde_qty", "거래량")

    st.success("삼성전자(005930) 조회 완료")

    st.metric(
        "현재가",
        f"{fmt_number(price)}원",
        delta=f"{change_price or '-'} ({change or '-'}%)",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("시가", f"{fmt_number(open_price)}원")
    c2.metric("고가", f"{fmt_number(high)}원")
    c3.metric("저가", f"{fmt_number(low)}원")
    c4.metric("거래량", fmt_number(volume))

    st.divider()
    st.subheader("삼성전자 최근 주가 차트")
    chart_df = extract_chart_df(chart_raw)
    if chart_df.empty:
        st.warning("차트 데이터가 반환되지 않았습니다. 키움 API의 차트 TR 권한과 응답 형식을 확인해주세요.")
    else:
        st.line_chart(chart_df, y="종가", height=420)
        st.caption("최근 거래일 종가 기준. 키움증권 API에서 받은 데이터입니다.")

    st.caption(f"조회 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("※ 모의투자 서버를 선택하면 모의투자 환경의 데이터를 사용합니다.")

except requests.HTTPError as e:
    st.error(f"키움 API HTTP 오류: {e}")
except Exception as e:
    st.error(f"조회 오류: {e}")
