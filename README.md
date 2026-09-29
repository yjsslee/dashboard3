# 삼성전자 오늘 주가 Streamlit

키움증권 REST API를 이용해 삼성전자(005930)의 오늘 현재가와 기본 시세를 Streamlit에서 보여주는 프로그램입니다.

## 보안

App Key와 App Secret은 GitHub 저장소에 넣지 않습니다.

Streamlit Cloud를 사용하는 경우 앱의 **Settings → Secrets**에 다음을 등록하세요.

```toml
KIWOOM_APP_KEY = "여기에_App_Key"
KIWOOM_APP_SECRET = "여기에_App_Secret"
```

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

기본값은 키움 **모의투자 서버**입니다. 실전 키를 사용하는 경우 앱의 사이드바에서 모의투자 서버 사용을 끄세요.

## 참고

키움 REST API 공식 문서의 OAuth 토큰 발급 및 국내주식 종목정보 API를 사용합니다.
