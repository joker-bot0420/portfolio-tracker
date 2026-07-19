import json
import os
import smtplib
from datetime import date
from email.mime.text import MIMEText
import yfinance as yf

# ── 실제 보유 수량 (매수/매도 발생 시 여기만 갱신) ──

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

LEGACY_HOLDINGS = {
    "VTI": 0.162431,
    "VT": 0.381653,
    "NVDA": 0.257968,
    "MSFT": 0.132221,
    "AMZN": 0.211713,
    "GOOGL": 0.14718,
    "AAPL": 0.186133,
}

EXPERIMENT_HOLDINGS = {
    "003490.KS": 16,  # 대한항공
}

ALERT_THRESHOLD = 0.05  # ±5%p 벗어나면 이메일

HISTORY_PATH = "data/history.json"
HISTORY_KEEP = 30       # 최근 30일치만 보관
TREND_WINDOW = 5        # 추세 판단에 쓸 기록 개수 (약 5거래일)
TREND_THRESHOLD = 2.0   # %p 이상 움직이면 추세로 판단


def get_usd_krw_rate():
    return yf.Ticker("KRW=X").history(period="1d")["Close"].iloc[-1]


def get_last_price(ticker):
    return yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history[-HISTORY_KEEP:], f, ensure_ascii=False, indent=2)


def trend_label(pct):
    if pct >= TREND_THRESHOLD:
        return "상승 추세"
    elif pct <= -TREND_THRESHOLD:
        return "하락 추세"
    return "횡보"


def fmt_change(changes, trends, tk):
    parts = []
    if tk in changes:
        d, p = changes[tk]
        parts.append(f"전일대비 {d:+,.0f}원 ({p:+.2f}%)")
    if tk in trends:
        p = trends[tk]
        parts.append(f"최근{TREND_WINDOW}일 {p:+.2f}% ({trend_label(p)})")
    return " | " + " | ".join(parts) if parts else ""


def build_report():
    fx = get_usd_krw_rate()

    active_values = {tk: shares * get_last_price(tk) * fx for tk, shares in ACTIVE_HOLDINGS.items()}
    legacy_values = {tk: shares * get_last_price(tk) * fx for tk, shares in LEGACY_HOLDINGS.items()}
    experiment_values = {tk: shares * get_last_price(tk) for tk, shares in EXPERIMENT_HOLDINGS.items()}

    all_values = {}
    all_values.update(active_values)
    all_values.update(legacy_values)
    all_values.update(experiment_values)

    history = load_history()
    today_str = date.today().isoformat()

    # 전일(직전 기록) 대비 변화
    changes = {}
    if history:
        prev = history[-1]["values"]
        for tk, val in all_values.items():
            if tk in prev and prev[tk]:
                diff = val - prev[tk]
                changes[tk] = (diff, diff / prev[tk] * 100)

    # 최근 N개 기록 대비 누적 변화 (추세)
    trends = {}
    if history:
        base_entry = history[max(0, len(history) - TREND_WINDOW)]
        base_values = base_entry["values"]
        for tk, val in all_values.items():
            if tk in base_values and base_values[tk]:
                trends[tk] = (val / base_values[tk] - 1) * 100

    active_total = sum(active_values.values())

    lines = [f"환율(USD/KRW): {fx:,.1f}", "", "=== 리밸런싱 대상 (목표 비중 있음) ==="]
    alerts = []
    for tk, val in active_values.items():
        weight = val / active_total
        target = TARGET_WEIGHTS[tk]
        diff_w = weight - target
        flag = ""
        if abs(diff_w) >= ALERT_THRESHOLD:
            flag = "  <- 임계값 초과"
            alerts.append((tk, weight, target, diff_w))
        lines.append(
            f"{tk}: {val:,.0f}원 | 현재 {weight*100:.1f}% / 목표 {target*100:.1f}% | "
            f"차이 {diff_w*100:+.1f}%p{flag}{fmt_change(changes, trends, tk)}"
        )
    lines.append(f"리밸런싱 풀 합계: {active_total:,.0f}원")
    lines.append("")

    lines.append("=== 관찰용 (신규매수 중단, 자연감소 대기) ===")
    for tk, val in legacy_values.items():
        lines.append(f"{tk}: {val:,.0f}원{fmt_change(changes, trends, tk)}")
    lines.append(f"관찰용 합계: {sum(legacy_values.values()):,.0f}원")
    lines.append("")

    lines.append("=== 실험 계좌 (별도 트랙) ===")
    for tk, val in experiment_values.items():
        lines.append(f"{tk}: {val:,.0f}원{fmt_change(changes, trends, tk)}")

    grand_total = active_total + sum(legacy_values.values()) + sum(experiment_values.values())
    lines.append("")
    lines.append(f"전체 포트폴리오 합계: {grand_total:,.0f}원")

    if history and history[-1]["date"] == today_str:
        history[-1]["values"] = all_values
    else:
        history.append({"date": today_str, "values": all_values})
    save_history(history)

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
    print(body)

    if alerts:
        subject = f"[포트폴리오 알림] 목표 비중 이탈 {len(alerts)}건"
        send_email(subject, body)
    else:
        print("모든 종목이 목표 비중 ±5%p 이내 — 이메일 발송 안 함")


if __name__ == "__main__":
    main()
