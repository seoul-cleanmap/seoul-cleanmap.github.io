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

## 데이터 파이프라인

### 현재 구조 (data.json)
- 서울 25개 자치구, 2,917건 (2023.12 기준)
- 중복 제거 완료: 같은 위치의 일반/재활용쓰레기는 한 건으로 합침 (`kind: "일반쓰레기 + 재활용쓰레기"`)
- 좌표 출처:
  - `csv_official` (357건): 전국휴지통표준데이터 CSV의 GPS 좌표
  - `vworld` (2,560건): Vworld API 지오코딩

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

### 대시보드
- 지도 위 상단: 전체/현재 화면 카운트 + 테마 토글
- 사이드 패널: 전체 개수, 자치구 수, 내 위치 거리

## 사용자 규칙

### 말투
- **존댓말 사용** (사용자가 명시적으로 요청함)

### 작업 방식
- 지오코딩보다 **공식 좌표를 우선** 사용할 것
- 중복 핀 배치 금지 — 같은 위치에 동일 내용의 핀이 여러 개 찍히면 안 됨
- 배너(Ember and Blade)는 패널 하단, about 텍스트 위에 배치, 너비는 패널에 맞추고 높이는 잘리지 않게
- 로드뷰 URL: `https://map.kakao.com/link/roadview/${lat},${lon}`

### 삭제 가능한 파일
- `regeocode.py`, `regeocode2.py` — 과거 지오코딩 스크립트, 더 이상 불필요
- `fetch_api_data.py` — API 승인 전까지 대기용
- `seoul_trashcan_2023.xlsx` — 다운로드 실패 빈 파일

## 미완료 작업
- [ ] 공공데이터포털 API 승인 후 강남구·송파구 공식 좌표로 교체
- [ ] git remote를 새 org URL로 업데이트 (`seoul-cleanmap/seoul-cleanmap.github.io`)
- [ ] 데이터 업데이트 시 build_data.py 재실행 필요
