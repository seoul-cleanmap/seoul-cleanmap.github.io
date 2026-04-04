# -*- coding: utf-8 -*-
"""
서울 25개구 쓰레기통 data.json 빌드
1) Excel(서울시 가로쓰레기통 설치정보)에서 중복 합치기
2) 전국휴지통표준데이터 CSV에서 좌표 있으면 매칭
3) 나머지는 Vworld API 지오코딩
"""
import json, csv, time, re, urllib.request, urllib.parse, sys
import openpyxl

# ── 설정 ──────────────────────────────────────────────
VWORLD_KEY = "89769725-F756-336D-B449-3060DDC54585"
EXCEL_FILE = "서울특별시 가로쓰레기통 설치정보_202312.xlsx"
CSV_FILE   = "전국휴지통표준데이터.csv"
OUTPUT     = "data.json"
DELAY      = 0.12

# 서울시 유효 좌표 범위
SEOUL_BOUNDS = (37.41, 37.72, 126.76, 127.19)  # lat_min, lat_max, lon_min, lon_max


def in_seoul(lat, lon):
    return (SEOUL_BOUNDS[0] <= lat <= SEOUL_BOUNDS[1] and
            SEOUL_BOUNDS[2] <= lon <= SEOUL_BOUNDS[3])


def vworld_geocode(address):
    """도로명주소 -> (lat, lon) or None"""
    params = {
        "service": "address", "request": "getcoord", "crs": "epsg:4326",
        "address": address, "type": "road", "refine": "false",
        "simple": "false", "format": "json", "key": VWORLD_KEY,
    }
    url = "https://api.vworld.kr/req/address?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        res = json.loads(r.read())
    if res.get("response", {}).get("status") == "OK":
        pt = res["response"]["result"]["point"]
        lat, lon = float(pt["y"]), float(pt["x"])
        if in_seoul(lat, lon):
            return lat, lon
    return None


def vworld_search(query):
    """POI 검색 -> (lat, lon) or None"""
    params = {
        "service": "search", "request": "search", "version": "2.0",
        "crs": "epsg:4326", "size": "1", "format": "json",
        "type": "place", "query": query,
        "bbox": "126.76,37.41,127.19,37.72",
        "key": VWORLD_KEY,
    }
    url = "https://api.vworld.kr/req/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        res = json.loads(r.read())
    items = res.get("response", {}).get("result", {}).get("items", [])
    if items:
        pt = items[0].get("point", {})
        y, x = pt.get("y"), pt.get("x")
        if y and x:
            lat, lon = float(y), float(x)
            if in_seoul(lat, lon):
                return lat, lon
    return None


# ── 1단계: Excel -> 중복 합치기 ─────────────────────
def load_excel():
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active
    merged = {}  # key: (gu, addr, detail) -> merged item

    for row in ws.iter_rows(min_row=5, values_only=True):
        gu = str(row[1] or "").strip()
        if not gu or "구" not in gu:
            continue
        addr = str(row[2] or "").strip()
        detail = str(row[3] or "").strip()
        place_type = str(row[4] or "").strip()
        kind = str(row[5] or "").strip()

        key = (gu, addr, detail)
        if key not in merged:
            merged[key] = {
                "district": gu,
                "road": addr,
                "detail": detail,
                "place_type": place_type,
                "kinds": set(),
            }
        if kind:
            merged[key]["kinds"].add(kind)

    items = []
    for key, m in merged.items():
        items.append({
            "district": m["district"],
            "label": m["detail"] if m["detail"] else m["road"],
            "road": m["road"],
            "detail": m["detail"],
            "place_type": m["place_type"],
            "kind": " + ".join(sorted(m["kinds"])) if m["kinds"] else "",
            "lat": None,
            "lon": None,
            "geocode": "",
        })
    return items


# ── 2단계: CSV 좌표 매칭 ─────────────────────────────
def load_csv_coords():
    """전국휴지통표준데이터에서 서울 좌표 로드 -> {(gu, road_normalized): (lat, lon)}"""
    coords = {}
    with open(CSV_FILE, "rb") as f:
        text = f.read().decode("cp949")
    reader = csv.DictReader(text.splitlines())
    for row in reader:
        if row.get("시도명", "") != "서울특별시":
            continue
        sgg = row.get("시군구명", "").strip()
        road = row.get("소재지도로명주소", "").strip()
        lat = row.get("위도", "")
        lon = row.get("경도", "")
        if not lat or not lon:
            continue
        try:
            lat_f, lon_f = float(lat), float(lon)
        except (ValueError, TypeError):
            continue
        if lat_f == 0 or lon_f == 0 or not in_seoul(lat_f, lon_f):
            continue
        # road에서 "서울특별시 XX구" 접두사 제거 후 정규화
        road_norm = re.sub(r"^서울특별시\s+\S+구\s+", "", road).strip()
        road_norm = re.sub(r"\s+", " ", road_norm)
        key = (sgg, road_norm)
        if key not in coords:
            coords[key] = (lat_f, lon_f)
    return coords


def normalize_road(road):
    """Excel 도로명에서 비교용 정규화"""
    s = re.sub(r"\s+", " ", road).strip()
    return s


def match_csv_coords(items, csv_coords):
    matched = 0
    for item in items:
        if item["lat"] is not None:
            continue
        road_norm = normalize_road(item["road"])
        key = (item["district"], road_norm)
        if key in csv_coords:
            item["lat"], item["lon"] = csv_coords[key]
            item["geocode"] = "csv_official"
            matched += 1
    return matched


# ── 3단계: Vworld 지오코딩 ───────────────────────────
def geocode_items(items):
    need = [i for i, d in enumerate(items) if d["lat"] is None]
    print(f"Vworld geocoding: {len(need)}건", flush=True)

    # 같은 도로명주소는 한 번만 호출
    addr_cache = {}  # "서울특별시 XX구 도로명" -> (lat, lon) or False
    success = 0
    fail = 0

    for seq, idx in enumerate(need):
        item = items[idx]
        gu = item["district"]
        road = item["road"]
        detail = item["detail"]

        # 캐시 키: 구 + 도로명주소
        full_addr = f"서울특별시 {gu} {road}"
        result = None

        # 1) 도로명주소로 지오코딩 (캐시 활용)
        if full_addr not in addr_cache:
            try:
                r = vworld_geocode(full_addr)
                addr_cache[full_addr] = r if r else False
                time.sleep(DELAY)
            except Exception:
                addr_cache[full_addr] = False

        cached = addr_cache[full_addr]
        if cached:
            result = cached

        # 2) 세부위치 POI 검색 (도로명 결과 없을 때)
        if not result and detail:
            poi_query = f"서울 {gu} {detail}"
            try:
                r = vworld_search(poi_query)
                if r:
                    result = r
                time.sleep(DELAY)
            except Exception:
                pass

        if result:
            item["lat"], item["lon"] = result
            item["geocode"] = "vworld"
            success += 1
        else:
            fail += 1

        if (seq + 1) % 100 == 0:
            print(f"  {seq+1}/{len(need)} ({(seq+1)/len(need)*100:.0f}%) "
                  f"| ok: {success} | fail: {fail} | cache: {len(addr_cache)}", flush=True)

    return success, fail


# ── 메인 ─────────────────────────────────────────────
def main():
    print("1) Excel loading + dedup...", flush=True)
    items = load_excel()
    print(f"   -> {len(items)}건 (deduplicated)", flush=True)

    print("2) CSV coord matching...", flush=True)
    csv_coords = load_csv_coords()
    print(f"   CSV coords loaded: {len(csv_coords)}건", flush=True)
    matched = match_csv_coords(items, csv_coords)
    print(f"   -> {matched}건 matched", flush=True)

    print("3) Vworld geocoding...", flush=True)
    ok, ng = geocode_items(items)
    print(f"   -> ok: {ok}, fail: {ng}", flush=True)

    # 좌표 없는 항목 제거
    before = len(items)
    items = [d for d in items if d["lat"] is not None]
    print(f"\n4) Result: {len(items)}/{before} (removed {before - len(items)} without coords)", flush=True)

    # 통계
    by_district = {}
    by_geocode = {}
    for d in items:
        by_district[d["district"]] = by_district.get(d["district"], 0) + 1
        by_geocode[d["geocode"]] = by_geocode.get(d["geocode"], 0) + 1

    print("\n=== By district ===", flush=True)
    for k, v in sorted(by_district.items()):
        print(f"  {k}: {v}", flush=True)
    print(f"\n=== By geocode ===", flush=True)
    for k, v in sorted(by_geocode.items()):
        print(f"  {k}: {v}", flush=True)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"\n{OUTPUT} saved ({len(items)} items)", flush=True)


if __name__ == "__main__":
    main()
