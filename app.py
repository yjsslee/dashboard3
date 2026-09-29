import os
from datetime import datetime

import requests
import streamlit as st

# 삼성전자(005930) 오늘 현재가 조회용 Streamlit 앱
# App Key / App Secret은 GitHub에 저장하지 않습니다.
# Streamlit Cloud에서는 Settings > Secrets에 KIWOOM_APP_KEY, KIWOOM_APP_SECRET를 등록하세요.

st.set_page_config(page_title="삼성전자 오늘 주가", page_icon="📈", layout="centered")

API_BASE = "https://api.kiwoom.com"
MOCK_API_BASE = "https://mockapi.kiwoom.com"
TOKEN_PATH = "/oauth2/token"
STOCK_INFO_PATH = "/api/dostk/stkinfo"


def get_secret(name: str) -> str:
    """Streamlit secrets 또는 환경변수에서 키를 읽습니다."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return value or os.getenv(name, "")


def get_access_token(app_key: str, app_secret: str, base_url: str) -> str:
    """Kiwoom OAuth 2.0 client-credentials 방식으로 접근토큰을 발급합니다."""
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
    token = data.get("token")
    if not token:
        raise RuntimeError(data.get("return_msg", "접근토큰이 응답되지 않았습니다."))
    return token


@st.cache_data(ttl=30, show_spinner=False)
def get_samsung_price(app_key: str, app_secret: str, use_mock: bool):
    """삼성전자 기본정보에서 현재가를 가져옵니다. 30초 동안 결과를 캐시합니다."""
    base_url = MOCK_API_BASE if use_mock else API_BASE
    token = get_access_token(app_key, app_secret, base_url)

    response = requests.post(
        base_url + STOCK_INFO_PATH,
        headers={
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "api-id": "ka10001",
        },
        json={"stk_cd": "005930"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("return_code", 0) not in (0, "0", None):
        raise RuntimeError(data.get("return_msg", "주가 조회에 실패했습니다."))

    return data


def first_value(data: dict, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


st.title("삼성전자 오늘 주가")
st.caption("키움증권 REST API · 삼성전자 005930")

with st.sidebar:
    st.subheader("API 설정")
    use_mock = st.toggle("모의투자 서버 사용", value=True)
    st.info(
        "GitHub에는 API Key/Secret을 저장하지 않습니다.\n\n"
        "Streamlit Cloud의 Secrets에 KIWOOM_APP_KEY와 KIWOOM_APP_SECRET을 등록하세요."
    )

app_key = get_secret("KIWOOM_APP_KEY")
app_secret = get_secret("KIWOOM_APP_SECRET")

if not app_key or not app_secret:
    st.warning("키움증권 App Key와 App Secret이 설정되지 않았습니다.")
    st.markdown(
        "**Streamlit Cloud 설정 예시**\n"
        "```toml\n"
        'KIWOOM_APP_KEY = "여기에_App_Key"\n'
        'KIWOOM_APP_SECRET = "여기에_App_Secret"\n'
        "```"
    )
    st.stop()

if st.button("🔄 삼성전자 현재가 조회", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

try:
    with st.spinner("키움증권에서 삼성전자 주가를 조회하고 있습니다..."):
        raw = get_samsung_price(app_key, app_secret, use_mock)

    # ka10001 응답은 현재가 필드가 환경/응답 형식에 따라 문자열로 내려올 수 있습니다.
    price = first_value(raw, "cur_prc", "현재가", "lastPrice", "last_prc")
    change = first_value(raw, "pre_rt", "전일대비등락율", "chg_rt")
    change_price = first_value(raw, "pred_pre", "전일대비", "pre_diff")
    high = first_value(raw, "high_pric", "고가")
    low = first_value(raw, "low_pric", "저가")
    open_price = first_value(raw, "open_pric", "시가")
    volume = first_value(raw, "trde_qty", "거래량")

    def fmt_number(value):
        if value in (None, ""):
            return "-"
        text = str(value).strip()
        try:
            if "." in text:
                return f"{float(text):,.2f}"
            return f"{int(text.replace(',', '')):,}"
        except ValueError:
            return text

    st.success("삼성전자(005930) 조회 완료")
    st.metric("현재가", f"{fmt_number(price)}원", delta=f"{change_price or '-'} ({change or '-'}%)")

    c1, c2, c3 = st.columns(3)
    c1.metric("시가", f"{fmt_number(open_price)}원")
    c2.metric("고가", f"{fmt_number(high)}원")
    c3.metric("저가", f"{fmt_number(low)}원")

    st.write(f"거래량: **{fmt_number(volume)}**")
    st.caption(f"조회 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("※ 키움증권 API 응답을 그대로 기반으로 표시합니다. 모의투자 서버를 선택하면 모의투자 환경을 사용합니다.")

except requests.HTTPError as e:
    st.error(f"키움 API HTTP 오류: {e}")
except Exception as e:
    st.error(f"조회 오류: {e}")
