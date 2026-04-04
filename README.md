# 서울 클린맵 (Seoul Clean Map)

서울시 25개 자치구 공공 쓰레기통 위치를 지도로 표시하는 정적 웹앱.

**배포 주소**: https://seoul-cleanmap.github.io

---

## 기술 스택

- **Leaflet 1.9.4** — 지도 렌더링
- **Leaflet.markercluster 1.5.3** — 마커 클러스터링
- **Vworld WMTS** — 배경 지도 (국토지리정보원)
- **data.json** — 사전 지오코딩된 좌표 데이터 (정적 파일)
- 외부 API 없음 (순수 정적 사이트)

---

## 파일 구조

```
seoul_trashcanmap/
├── index.html              # 단일 파일 앱 (HTML/CSS/JS 일체형)
├── data.json               # 25개구 쓰레기통 데이터 (2,917건)
├── icon.png                # 커스텀 쓰레기통 아이콘
├── build_data.py           # data.json 빌드 스크립트
├── verify_geocode.py       # 지오코딩 검수 도구 (Kakao 교차검증)
├── improve_geocode.py      # 지오코딩 정확도 개선 도구 (Kakao 재지오코딩)
├── fetch_api_data.py       # 공공데이터포털 API 수집 (강남·송파, 승인 대기)
└── .claude-scripts/        # 구버전 스크립트 (참고용)
```

---

## data.json 구조

```json
[
  {
    "district": "종로구",
    "label": "경복궁역 4번출구",
    "road": "사직로 125",
    "detail": "경복궁역 4번출구",
    "place_type": "지하철역 입구",
    "kind": "일반쓰레기 + 재활용쓰레기",
    "lat": 37.576130,
    "lon": 126.972909,
    "geocode": "vworld"
  }
]
```

### geocode 값 의미

| 값 | 설명 |
|----|------|
| `csv_official` | 전국휴지통표준데이터 CSV의 공식 GPS 좌표 |
| `vworld` | Vworld API 지오코딩 (도로명주소 또는 POI 검색) |
| `kakao` | Kakao Local Search 재지오코딩 (improve_geocode.py 적용 시) |

---

## 주요 기능

### 지도
- **줌 레벨 < 14**: 구 단위 버블 (자치구별 색상 구분)
- **줌 레벨 ≥ 14**: 개별 마커 클러스터
- **클러스터 클릭**: 20개 이하면 리스트 뷰, 20개 초과면 줌인
- **마커 클릭**: 상세 정보 패널 표시

### 사이드 패널
- **기본 뷰**: 전체·자치구 통계, 내 위치 찾기
- **리스트 뷰**: 클러스터 내 목록
- **상세 뷰**: 도로명·장소유형·종류·좌표 표시, 카카오 로드뷰 링크, 내 위치까지 거리
- **다크모드** 지원

---

## 데이터 재생성 방법

Python 3.8+ 및 `openpyxl` 필요.

```bash
pip install openpyxl
python build_data.py
```

1. `서울특별시 가로쓰레기통 설치정보_202312.xlsx` 에서 중복 합치기 (5,381 → 3,675건)
2. `전국휴지통표준데이터.csv` 에서 공식 GPS 좌표 매칭 (357건)
3. 나머지는 Vworld API 지오코딩 (~5분 소요)
4. 좌표 없는 항목 제거 → `data.json` 출력

---

## 지오코딩 검수 및 개선

```bash
# 1) 현재 좌표 검수 (Kakao 교차검증 → verify_result.csv 출력)
python verify_geocode.py

# 2) 정확도 개선 (버스정류장·지하철역 우선, vworld 항목 Kakao 재지오코딩)
python improve_geocode.py
```

- `verify_result.csv`: BAD(500m↑) / SUSPECT(200m↑) / NOT_FOUND 항목 목록
- `improve_geocode.py` 실행 전 `data_backup_YYYYMMDD.json` 자동 백업

---

## 데이터 현황 (2023.12 기준)

| 항목 | 값 |
|------|----|
| 전체 | 2,917건 |
| 자치구 | 25개구 |
| 공식 좌표 (csv_official) | 357건 |
| Vworld 지오코딩 (vworld) | 2,560건 |
| 강남구·송파구 공식 좌표 | 공공데이터포털 API 승인 대기 중 |

---

## 개발 환경

- Windows 11
- Python 3.x (데이터 빌드 스크립트)
- 빌드 과정 없음 — `index.html` 수정 후 커밋/푸시
