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

### 4. 확인
Actions 탭 → daily_check 워크플로우 → "Run workflow" 버튼으로 수동 실행해서
정상 작동하는지 먼저 테스트. 로그에 현재 비중이 다 찍히면 정상.

## 보유 수량 갱신
`tracker.py` 상단의 `ACTIVE_HOLDINGS` / `LEGACY_HOLDINGS` / `EXPERIMENT_HOLDINGS` 딕셔너리가
전부다. 매수·매도할 때마다 여기 숫자만 손으로 고쳐서 다시 push하면 됨.

## 목표 비중 바꾸고 싶으면
`TARGET_WEIGHTS` 딕셔너리 값만 수정. 합이 1.0(100%)이 되게만 맞추면 됨.

## 알림 기준 바꾸고 싶으면
`ALERT_THRESHOLD = 0.05` 숫자를 원하는 %p로 수정 (0.05 = ±5%p).
