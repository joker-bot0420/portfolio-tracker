# 포트폴리오 리밸런싱 트래커

매일 GitHub Actions가 자동으로 실행돼서 VOO/VXUS/BND/QQQM/SMH/SCHD 6종목의 현재 비중을
목표 비중과 비교하고, ±5%p 이상 벗어난 게 있으면 이메일로 알려주는 스크립트.

## 설정 방법

### 1. GitHub 리포지토리 만들기
이 폴더 전체를 새 GitHub 리포에 push. (public이어도 상관없음 — 보유 수량/이메일은
secrets로 따로 관리하니까 코드 자체엔 민감정보 없음. 원하면 private으로 해도 됨)

```bash
cd portfolio-tracker
git init
git add .
git commit -m "init"
git remote add origin <니 리포 URL>
git push -u origin main
```

### 2. Gmail 앱 비밀번호 발급
일반 구글 비밀번호로는 smtplib 로그인이 안 됨. 앱 비밀번호가 필요함:
1. 구글 계정 → 보안 → 2단계 인증 켜기 (안 켜져 있으면 먼저 켜야 함)
2. 구글 계정 → 보안 → "앱 비밀번호" 메뉴에서 16자리 비밀번호 발급
3. 이 16자리를 아래 EMAIL_PASSWORD로 사용 (일반 로그인 비밀번호 아님)

### 3. GitHub 리포 Secrets 등록
리포 → Settings → Secrets and variables → Actions → New repository secret

| Name | Value |
|---|---|
| EMAIL_ADDRESS | 알림 보낼 지메일 주소 |
| EMAIL_PASSWORD | 2번에서 발급한 16자리 앱 비밀번호 |
| EMAIL_TO | 알림 받을 이메일 주소 (본인 것도 가능) |

### 4. 워크플로우 권한 설정 (중요, 한 번만 하면 됨)
이제 스크립트가 매일 기록(`data/history.json`)을 리포에 직접 커밋해야 해서,
Actions가 리포에 쓰기 권한이 있어야 함:

리포 → Settings → Actions → General → 아래로 스크롤 →
"Workflow permissions" → **"Read and write permissions"** 선택 → Save

이거 안 해두면 마지막 "기록 파일 커밋" 단계에서 push 실패함.

### 5. 확인
Actions 탭 → daily_check 워크플로우 → "Run workflow" 버튼으로 수동 실행해서
정상 작동하는지 먼저 테스트. 로그에 현재 비중이 다 찍히면 정상.
성공하면 리포에 `data/history.json` 파일이 자동 생성/갱신된 걸 볼 수 있음.

## 전일대비 / 추세 기능
매일 실행될 때마다 `data/history.json`에 그날의 평가금액을 기록하고, 다음 실행부터는:
- **전일대비**: 어제 기록과 비교한 증감액/증감률
- **최근 5회 기록 대비 추세**: 상승 추세 / 하락 추세 / 횡보 (±2%p 기준)

를 이메일 본문에 같이 보여줌. 첫 실행 때는 비교할 과거 기록이 없어서 이 부분은 빈 채로
나오는 게 정상이고, 며칠 지나면서 자동으로 채워짐.

## 매주 매수 반영하는 법 (제일 중요, 이제 여기만 건드리면 됨)
`pending_buys.json` 파일 하나만 수정하면 돼. 이번 주 실제로 각 종목에 얼마 샀는지
원 단위 금액만 적어 넣으면 됨. 예를 들어 위젯이 알려준 대로 VOO에 8만원, SMH에 3만원
샀다면:

```json
{
  "VOO": 80000,
  "VXUS": 0,
  "BND": 0,
  "QQQM": 0,
  "SMH": 30000,
  "SCHD": 0
}
```

이렇게 고치고 push만 하면 끝. 다음 자동 실행(또는 수동 Run workflow) 때 스크립트가:
1. 그날 시세로 이 금액을 몇 주 샀는지 자동 계산
2. `data/holdings.json`(실제 보유 주수 기록)에 자동으로 더해서 저장
3. `pending_buys.json`은 다시 전부 0으로 리셋

즉, 주수 계산은 니가 할 필요 없고, 이번 주 얼마 썼는지 금액만 적으면 끝. 아무것도 안 사고
넘어간 주는 `pending_buys.json`을 그대로(전부 0) 둬도 됨.

## 보유 수량 초기값
`tracker.py` 상단의 `SEED_ACTIVE_HOLDINGS`는 `data/holdings.json`이 아직 없을 때만 쓰이는
최초 시작값이야. 한번 `data/holdings.json`이 생성된 이후로는 이 파일이 실제 보유 수량의
기준이 되고, `SEED_ACTIVE_HOLDINGS`를 다시 손댈 일은 없음.

`LEGACY_HOLDINGS`(VTI/VT/개별주 5종목)는 여전히 `tracker.py`를 직접 고쳐서 관리 —
여긴 신규매수 자동화 대상이 아니라서 그대로 둠.

## 대한항공(실험 계좌) 관리하는 법
이건 사고팔고를 반복하는 스윙 매매라 "이번 주 산 금액만 더하기" 방식이 안 맞음
(팔았는데 계속 더해지면 숫자가 꼬임). 그래서 `experiment_holdings.json`에
**그때그때 실제로 보유 중인 정확한 주수**를 덮어써 넣는 방식으로 관리함.

매수·매도 체결될 때마다:
```json
{
  "003490.KS": 20
}
```
이런 식으로 지금 실제 보유 주수 그대로 고쳐서 push. 더하기/빼기 계산 니가 미리 할 필요 없이,
그냥 "지금 몇 주 갖고 있는지" 결과값만 넣으면 됨.

## 목표 비중 바꾸고 싶으면
`TARGET_WEIGHTS` 딕셔너리 값만 수정. 합이 1.0(100%)이 되게만 맞추면 됨.

## 알림 기준 바꾸고 싶으면
`ALERT_THRESHOLD = 0.05` 숫자를 원하는 %p로 수정 (0.05 = ±5%p).
