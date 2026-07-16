import os
import smtplib
from email.mime.text import MIMEText
import yfinance as yf

# ── 실제 보유 수량 (2026-07-16 기준. 매수/매도 발생 시 여기만 갱신) ──

# 리밸런싱 대상 (신규 자금 유입 O, 목표 비중 있음)
ACTIVE_HOLDINGS = {
    "VOO": 0.195296,
    "VXUS": 0.697638,
    "BND": 0.807332,
    "QQQM": 0.13708,
    "SMH": 0.06961,
    "SCHD": 1.649254,
}

TARGET_WEIGHTS = {
    "VOO": 0.45,
    "VXUS": 0.15,
    "BND": 0.15,
    "QQQM": 0.10,
    "SMH": 0.10,
    "SCHD": 0.05,
}

# 관찰용 (신규 매수 중단, 시간 지나며 비중 자연 감소 대기 — VTI/VT는 VOO로 압축 결정)
LEGACY_HOLDINGS = {
    "VTI": 0.162431,
    "VT": 0.381653,
    "NVDA": 0.257968,
    "MSFT": 0.132221,
    "AMZN": 0.211713,
    "GOOGL": 0.14718,
    "AAPL": 0.186133,
}

# 별도 실험 계좌 (원화 종목, 리밸런싱 로직과 무관)
EXPERIMENT_HOLDINGS = {
    "003490.KS": 16,  # 대한항공
}

ALERT_THRESHOLD = 0.05  # ±5%p 벗어나면 이메일


def get_usd_krw_rate():
    return yf.Ticker("KRW=X").history(period="1d")["Close"].iloc[-1]


def get_last_price(ticker):
    return yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]


def build_report():
    fx = get_usd_krw_rate()

    active_values = {tk: shares * get_last_price(tk) * fx for tk, shares in ACTIVE_HOLDINGS.items()}
    legacy_values = {tk: shares * get_last_price(tk) * fx for tk, shares in LEGACY_HOLDINGS.items()}
    experiment_values = {tk: shares * get_last_price(tk) for tk, shares in EXPERIMENT_HOLDINGS.items()}

    active_total = sum(active_values.values())

    lines = [f"환율(USD/KRW): {fx:,.1f}", "", "=== 리밸런싱 대상 (목표 비중 있음) ==="]
    alerts = []
    for tk, val in active_values.items():
        weight = val / active_total
        target = TARGET_WEIGHTS[tk]
        diff = weight - target
        flag = ""
        if abs(diff) >= ALERT_THRESHOLD:
            flag = "  <- 임계값 초과"
            alerts.append((tk, weight, target, diff))
        lines.append(f"{tk}: {val:,.0f}원 | 현재 {weight*100:.1f}% / 목표 {target*100:.1f}% | 차이 {diff*100:+.1f}%p{flag}")
    lines.append(f"리밸런싱 풀 합계: {active_total:,.0f}원")
    lines.append("")

    lines.append("=== 관찰용 (신규매수 중단, 자연감소 대기) ===")
    for tk, val in legacy_values.items():
        lines.append(f"{tk}: {val:,.0f}원")
    lines.append(f"관찰용 합계: {sum(legacy_values.values()):,.0f}원")
    lines.append("")

    lines.append("=== 실험 계좌 (별도 트랙) ===")
    for tk, val in experiment_values.items():
        lines.append(f"{tk}: {val:,.0f}원")

    grand_total = active_total + sum(legacy_values.values()) + sum(experiment_values.values())
    lines.append("")
    lines.append(f"전체 포트폴리오 합계: {grand_total:,.0f}원")

    return "\n".join(lines), alerts


def send_email(subject, body):
    sender = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    to = os.environ["EMAIL_TO"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, [to], msg.as_string())


def main():
    body, alerts = build_report()
    print(body)  # GitHub Actions 로그에도 항상 남김

    if alerts:
        subject = f"[포트폴리오 알림] 목표 비중 이탈 {len(alerts)}건"
        send_email(subject, body)
    else:
        print("모든 종목이 목표 비중 ±5%p 이내 — 이메일 발송 안 함")


if __name__ == "__main__":
    main()
