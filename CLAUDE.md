# Seoul Clean Map - 작업 가이드

## 프로젝트 개요
- **서비스명**: 서울 클린맵 (Seoul Clean Map)
- **목적**: 서울시 25개 자치구 공공 쓰레기통 위치를 지도에 표시하는 정적 웹서비스
- **배포**: GitHub Pages (Organization) — https://seoul-cleanmap.github.io
- **레포**: `seoul-cleanmap/seoul-cleanmap.github.io` (git remote는 아직 이전 URL이지만 자동 리다이렉트됨)

## 기술 스택
- **지도**: Leaflet 1.9.4 + MarkerCluster
- **타일**: Vworld WMTS (`89769725-F756-336D-B449-3060DDC54585`)
- **다크모드**: CSS filter (`invert(1) hue-rotate(180deg) brightness(0.85) contrast(0.9)`)
- **단일 파일**: `index.html`에 HTML/CSS/JS 모두 포함
- **데이터**: `data.json` (빌드 스크립트: `build_data.py`)
- **모바일 브레이크포인트**: `680px` (max-width: 680px = 모바일)

## 데이터 파이프라인

### 현재 구조 (data.json)
- 서울 25개 자치구, 2,917건 (2023.12 기준, 수동 수정 포함)
- 중복 제거 완료: 같은 위치의 일반/재활용쓰레기는 한 건으로 합침 (`kind: "일반쓰레기 + 재활용쓰레기"`)
- 좌표 출처:
  - `csv_official` (357건): 전국휴지통표준데이터 CSV의 GPS 좌표
  - `vworld` (2,560건): Vworld API 지오코딩
  - `manual` (소수): 수동으로 좌표를 직접 입력한 핀

### 수동 수정된 핀 (geocode=manual)
| 핀 ID | 내용 |
|-------|------|
| 0727 | 노원구, 수동 좌표 수정 |
| 1162 | 노원구, 수동 좌표 수정 |
| 1415 | 서초구, 수동 좌표 수정 |
| 0011 | 강동구, 수동 좌표 수정 (kko.to/XDqx6S9bgX) |
| 1684 | 종로구 서순라길 인근, 수동 좌표 수정 |
| 1685 | 종로구 서순라길 7, 수동 좌표 수정 |
| 1686 | 종로구 서순라길 3, 수동 좌표 수정 |
| 1606 | **삭제됨** — 현장에 쓰레기통 없음 |
| 0599 | 강남구 아셈회의장 버스정류장(23-191), 수동 좌표 수정 |
| 0600 | 강남구 무역센터 공항버스정류장(23-818), 수동 좌표 수정 |
| 0602 | 강남구 무역센터 도로변, 수동 좌표 수정 |
| 0601 | **삭제됨** — 0600(무역센터 버스정류장)과 위치 통합 |
| 0603 | **삭제됨** — 0599(아셈회의장 버스정류장)와 위치 통합, 23-905 정류장 미존재 |
| 0652 | 서초구 청계산입구역 2번 출구, 수동 좌표 수정 (kko.to/RKa4EcUdnB) |
| 0578 | 강남구 해성2빌딩 앞 버스정류장(23-523), 수동 좌표 수정 (kko.to/7jlLXKlBMv) |
| 0567 | 강남구 루첸타워, 수동 좌표 수정 (kko.to/mkCqiFCM8m) |
| 0559 | 강남구 K타워, 수동 좌표 수정 (kko.to/fXFkoPr6v4) |
| 1018 | 강남구 클래시스빌딩 앞 버스정류장(23-305), 수동 좌표 수정 (kko.to/YpT-tUdbtx) |
| 1050 | 강남구 GS빌딩 버스정류장(23-281), 수동 좌표 수정 (kko.to/koA26I9VYM) |
| 1054 | 강남구 역삼역1번출구 앞, 수동 좌표 수정 (kko.to/CRZseIIuqc) |
| 1058 | 강남구 아주빌딩 앞(역삼역 8번출구), 수동 좌표 수정 (kko.to/6UUbSO2mtU) |
| 1057 | **삭제됨** — 1058(아주빌딩 앞, 역삼역 8번출구)과 위치 통합 |
| 0003 | 강동구 한영중고한영외고 앞(25-181), 수동 좌표 수정 (kko.to/Sp87V9KUT6) |
| 0004 | 강동구 강동아트센터(25-179), 수동 좌표 수정 (kko.to/EgH6u4a4nZ) |
| 0005 | 강동구 남한산성 만남의장소 옆, 수동 좌표 수정 (kko.to/oTN7BTweU7) |
| 0006 | 강동구 명일동 이마트 앞 횡단보도, 수동 좌표 수정 (kko.to/b2bQ6ixSnk) |
| 0007 | **삭제됨** — 0006(명일동 이마트 앞 횡단보도)과 위치 통합 |

### 원본 데이터 파일
| 파일 | 용도 |
|------|------|
| `서울특별시 가로쓰레기통 설치정보_202312.xlsx` | **주 데이터소스** — 25개구 5,381건, 좌표 없음 |
| `전국휴지통표준데이터.csv` | 좌표 있음, 서울은 6개구만 (강남·송파 없음) |
| `서울특별시_강남구_쓰레기통설치현황_20210622.csv` | 강남구 개별 CSV, 좌표 없음 |
| `서울특별시 송파구_가로휴지통 설치 위치_20240731.csv` | 송파구 개별 CSV, 좌표 없음 |
| `서울특별시 년도별 자치구별 가로쓰레기통 설치현황(2024.12.).xlsx` | 통계만 (개수), 위치 정보 없음 |

### 좌표 문제
- **강남구·송파구는 좌표를 공개하지 않음** — 전국휴지통표준데이터에도 빠져있고, 개별 CSV에도 위도/경도 없음
- 공공데이터포털 제공신청 넣어둔 상태 (승인 대기 중)
- API 키: `771f57a75cdf507e03f3823d8e654caf37bc0a5dff22698b104d6244be384508` — 아직 SERVICE KEY NOT REGISTERED 에러
- 승인되면 `fetch_api_data.py`로 좌표 포함 데이터 가져올 수 있음

### 빌드 방법
```bash
python build_data.py
```
1. Excel에서 중복 합치기 (5,381 → 3,675건)
2. 전국휴지통표준데이터 CSV에서 좌표 매칭
3. 나머지 Vworld API 지오코딩 (소요시간 ~5분)
4. 좌표 없는 항목 제거 → data.json 출력

## index.html 구조

### 주요 설정값
- `SOURCES`: 25개 자치구 배열 (이름, 색상, dongBg)
- `DONG_THRESHOLD = 14`: zoom < 14이면 동 버블, >= 14이면 개별 핀
- 지도 중심: `[37.5550, 126.9800]`, 초기 zoom: 11

### 뷰 모드
- **view-default**: 안내 + 가까운 쓰레기통 찾기
- **view-list**: 클러스터 클릭시 목록
- **view-detail**: 개별 쓰레기통 상세 (카카오 로드뷰 링크 포함)

### 모바일 3-state 패널 시스템
CSS 클래스로 상태 관리 (`setMobileState(state)` 함수):
- **map-only** (클래스 없음): 패널 완전히 숨김 (`translateY(100%)`)
- **mobile-overview**: 패널 55vh, 헤더·검색바·footer 표시
- **mobile-detail**: 패널 50vh 최대, 헤더·검색바·footer 숨김, body만 스크롤

패널 동작:
- 지도 클릭: map-only ↔ overview 토글, 상세정보 중엔 showDefault()
- 스와이프 다운 (dy > 60px): 패널 숨김(map-only)
- 핀 선택: mobile-detail 전환 + `panBy(panelH * 0.75)` 오프셋으로 핀 화면 상단 1/4에 위치

### 출처·배너 표시 방식 (이중 구조)
- **`.panel-footer`**: 데스크톱에서 패널 하단 고정 노출
- **`.detail-footer-scroll`**: 모바일에서 상세정보 스크롤 내부 포함
- `@media (min-width: 681px)` 에서 `.detail-footer-scroll { display: none; }` → 데스크톱 중복 방지
- `#panel.mobile-detail .panel-footer { display: none; }` → 모바일 detail 시 footer 숨김

### 핀 강조 방식
- `renderMarkers()`에서 `item._marker = marker` 저장
- 선택 시: `marker.setIcon(highlightIcon)`, 원본 `marker._origIcon`에 저장
- 해제 시: `marker.setIcon(marker._origIcon)` 복원
- 클러스터 안에 있는 핀 (`!item._marker._icon`): `markerCluster.zoomToShowLayer(item._marker)` 호출

### 대시보드
- 지도 위 상단: 전체/현재 화면 카운트 + 테마 토글
- 사이드 패널: 전체 개수, 자치구 수, 내 위치 거리

## admin.html 구조

### 탭 목록
- **submissions**: 신고 접수 (Firestore `submissions` 컬렉션)
- **approved / rejected**: 처리 완료 신고
- **review**: 좌표 검수 (review_data.json 기반 BAD/SUSPECT 핀)
- **pin-search**: 핀 수정 (전체 핀 검색 후 kko.to 제출)

### Firestore 연동
- **프로젝트**: `seoul-cleanmap`
- **컬렉션**: `submissions` (신고), `coord_reviews` (좌표 수정 제출)
- `coord_reviews` 문서 구조: `{ pinId, kkoTo, status:'pending', district, label, road, curLat, curLon, submittedAt }`
- Firestore REST API: `https://firestore.googleapis.com/v1/projects/seoul-cleanmap/databases/(default)/documents/coord_reviews`

### review_data.json
- 생성: `tools/verify_geocode.py` → `verify_result.csv` → `tools/build_review_data.py` → `review_data.json`
- BAD(500m+), SUSPECT(200-500m) 핀만 포함
- `geocode=manual` 핀 제외 (이미 수동 수정됨)
- 현재 약 130건
- 핀 ID 매칭: label + road + district 기준 (좌표는 수정될 수 있으므로)

### 좌표 검수 워크플로우
1. 사용자가 admin.html → 좌표 검수 탭에서 kko.to 링크 확인 후 제출
2. Firestore `coord_reviews`에 저장됨
3. 사용자가 Claude에게 반영 요청 (admin 하단 "📋 Claude에게 반영 요청 복사" 버튼으로 텍스트 복사)
4. Claude가 Firestore REST API로 pending 항목 조회 → kko.to 링크 resolve → data.json 수정
5. 수정 후 `geocode=manual`로 변경, review_data.json 재생성, commit+push

### 로드뷰 URL 형식
`https://map.kakao.com/link/roadview/${lat},${lon}`

## 사용자 규칙

### 말투
- **존댓말 사용** (사용자가 명시적으로 요청함)

### 작업 방식
- **작업 후 반드시 git push** — 미리보기 패널은 무한로딩으로 확인 불가, 사용자가 직접 도메인에서 확인하므로 푸시까지 완료해야 작업 끝
- 지오코딩보다 **공식 좌표를 우선** 사용할 것
- 중복 핀 배치 금지 — 같은 위치에 동일 내용의 핀이 여러 개 찍히면 안 됨
- 배너(Ember and Blade)는 패널 하단, about 텍스트 위에 배치, 너비는 패널에 맞추고 높이는 잘리지 않게
- 로드뷰 URL: `https://map.kakao.com/link/roadview/${lat},${lon}`
- review_data.json 재생성 시 `geocode=manual` 핀은 항상 제외할 것

### 삭제 가능한 파일
- `regeocode.py`, `regeocode2.py` — 과거 지오코딩 스크립트, 더 이상 불필요
- `fetch_api_data.py` — API 승인 전까지 대기용
- `seoul_trashcan_2023.xlsx` — 다운로드 실패 빈 파일

## 미완료 작업
- [ ] 공공데이터포털 API 승인 후 강남구·송파구 공식 좌표로 교체
- [ ] git remote를 새 org URL로 업데이트 (`seoul-cleanmap/seoul-cleanmap.github.io`)
- [ ] 데이터 업데이트 시 build_data.py 재실행 필요
- [ ] 좌표 검수 진행 중 — BAD 핀 위주로 kko.to 제출 후 Claude에게 반영 요청
- [ ] verify_geocode.py 결과: OK=253, BAD=116, SUSPECT=18, NOT_FOUND=1593 (vworld 1980건 기준)
