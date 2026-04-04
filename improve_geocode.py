# -*- coding: utf-8 -*-
"""
지오코딩 정확도 개선 도구
- vworld 지오코딩 항목을 Kakao Local Search로 재검증 후 좌표 교체

검색 전략:
  1) 지하철역 출구 → "역명 N번출구" 만 추출해서 검색 (구 접두사·"앞" 제거)
  2) 버스정류장    → 현재 좌표 반경 500m 내 "버스정류장" 카테고리 proximity 검색
  3) 일반 POI     → 현재 좌표 반경 500m + 이름 유사도 40% 이상

사용법:
  python improve_geocode.py
"""
import json, time, math, re, shutil, sys, urllib.request, urllib.parse
from datetime import datetime

KAKAO_API_KEY = "553e2e606a80c405fff3f61fa3adc613"
INPUT  = "data.json"
DELAY  = 0.12
MIN_DIST_TO_UPDATE = 50     # 50m 미만 차이는 교체 안 함
SEARCH_RADIUS      = 500    # 반경 검색 m
SEOUL_BOUNDS = (37.41, 37.72, 126.76, 127.19)

ARS_PATTERN    = re.compile(r'\((\d{2,3}-\d{3,4})\)')
SUBWAY_PATTERN = re.compile(r'(.+역)\s*(\d+번\s*출구)')
# 레이블 끝의 위치 부사 제거용
TRAILING_NOISE = re.compile(r'\s*(앞|옆|근처|인근|쪽|앞쪽|뒤|뒤쪽|건너편|맞은편)\s*$')


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((lat2 - lat1) * math.pi / 360)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin((lon2 - lon1) * math.pi / 360)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def in_seoul(lat, lon):
    return (SEOUL_BOUNDS[0] <= lat <= SEOUL_BOUNDS[1] and
            SEOUL_BOUNDS[2] <= lon <= SEOUL_BOUNDS[3])


def kakao_search(query, lat=None, lon=None, radius=None, size=5):
    """카카오 키워드 검색. lat/lon/radius 지정 시 반경 proximity 검색."""
    params = {"query": query, "size": size}
    if lat is not None:
        params["y"]      = lat
        params["x"]      = lon
        params["radius"] = radius or SEARCH_RADIUS
        params["sort"]   = "distance"
    url = "https://dapi.kakao.com/v2/local/search/keyword.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"KakaoAK {KAKAO_API_KEY}",
        "User-Agent":    "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read()).get("documents", [])


# ── 지하철 출구 ──────────────────────────────────────────
def handle_subway(label, cur_lat, cur_lon):
    """
    "복정역 3번출구 앞" → "복정역 3번출구" 로 정제해서 검색.
    구 접두사·위치부사 제거.
    """
    m = SUBWAY_PATTERN.search(label)
    if not m:
        return None
    query = m.group(1) + " " + m.group(2).strip()  # "복정역 3번출구"

    # 1) 순수 이름 검색 (전국 DB 활용)
    docs = kakao_search(query, size=5)
    best = _pick_subway(docs)
    if best:
        return best

    # 2) proximity 검색 (반경 1km)
    docs = kakao_search(query, lat=cur_lat, lon=cur_lon, radius=1000, size=5)
    return _pick_subway(docs)


def _pick_subway(docs):
    for d in docs:
        cat = d.get("category_name", "")
        if "지하철" in cat or "철도" in cat:
            return d
    return None


# ── 버스정류장 ───────────────────────────────────────────
def handle_busstop(label, cur_lat, cur_lon, district=""):
    """
    버스정류장 좌표 개선.
    vworld 지오코딩 오류가 클 수 있으므로 proximity + 전국검색 병행.
    """
    ars_m = ARS_PATTERN.search(label)
    ars   = ars_m.group(1) if ars_m else None
    clean = TRAILING_NOISE.sub("", ARS_PATTERN.sub("", label)).strip()

    # 1) 반경 500m proximity (현재 좌표가 얼추 맞을 때)
    if clean:
        docs = kakao_search(clean, lat=cur_lat, lon=cur_lon, radius=SEARCH_RADIUS, size=5)
        best = _pick_busstop(docs, ars)
        if best:
            return best

    # 2) 전국 검색 + 구 이름 보정 (현재 좌표가 많이 틀렸을 때)
    #    예: "삼성래미안아파트 후문 송파구" → 송파구 내 결과 우선
    if clean:
        query = f"{clean} {district}" if district else clean
        docs  = kakao_search(query, size=5)
        # 같은 구 결과 우선
        for d in docs:
            addr = d.get("address_name", "") + d.get("road_address_name", "")
            if district and district in addr:
                return d
        # 구 필터 없이 첫 번째 결과
        best = _pick_busstop(docs, ars)
        if best:
            return best

    # 3) 반경 2km proximity (오차가 큰 경우)
    docs = kakao_search("버스정류장",
                        lat=cur_lat, lon=cur_lon, radius=2000, size=5)
    best = _pick_busstop(docs, ars)
    if best:
        return best

    return None


def _pick_busstop(docs, ars=None):
    candidates = [d for d in docs
                  if "버스" in d.get("category_name", "")
                  or "정류" in d.get("place_name", "")]
    if not candidates:
        return None
    if ars:
        for d in candidates:
            if ars in d.get("place_name", ""):
                return d
    return candidates[0]


# ── 일반 POI ─────────────────────────────────────────────
def handle_poi(label, cur_lat, cur_lon):
    clean = TRAILING_NOISE.sub("", label).strip()
    if not clean:
        return None

    # proximity 검색
    docs = kakao_search(clean, lat=cur_lat, lon=cur_lon,
                        radius=SEARCH_RADIUS, size=5)
    for d in docs:
        if _name_overlap(clean, d.get("place_name", "")) >= 0.4:
            return d
    return None


def _name_overlap(label, kakao_name):
    stopwords = {'앞', '옆', '근처', '내', '및', '앞쪽', '쪽', '버스정류장', '정류장'}
    lw = set(re.findall(r'[가-힣a-zA-Z0-9]+', label)) - stopwords
    kw = set(re.findall(r'[가-힣a-zA-Z0-9]+', kakao_name))
    return len(lw & kw) / len(lw) if lw else 0.0


# ── 메인 ─────────────────────────────────────────────────
def main():
    with open(INPUT, encoding="utf-8") as f:
        data = json.load(f)

    backup = f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy(INPUT, backup)
    print(f"백업 완료: {backup}")

    targets = [(i, d) for i, d in enumerate(data) if d.get("geocode") == "vworld"]
    print(f"vworld 항목 {len(targets)}건 처리 시작\n")

    updated = skipped = error = 0
    log_lines = []

    for seq, (idx, item) in enumerate(targets):
        label   = item.get("label", "")
        cur_lat = item["lat"]
        cur_lon = item["lon"]

        is_subway  = bool(SUBWAY_PATTERN.search(label))
        is_busstop = (bool(ARS_PATTERN.search(label))
                      or "버스정류장" in label or "정류장" in label)

        try:
            if is_subway:
                best = handle_subway(label, cur_lat, cur_lon)
            elif is_busstop:
                best = handle_busstop(label, cur_lat, cur_lon, item.get("district", ""))
            else:
                best = handle_poi(label, cur_lat, cur_lon)
            time.sleep(DELAY)
        except Exception as e:
            error += 1
            if error <= 10:
                print(f"  API 오류({label[:20]}): {e}")
            continue

        if not best:
            skipped += 1
            continue

        new_lat = float(best["y"])
        new_lon = float(best["x"])

        if not in_seoul(new_lat, new_lon):
            skipped += 1
            continue

        dist = haversine(cur_lat, cur_lon, new_lat, new_lon)
        if dist < MIN_DIST_TO_UPDATE:
            skipped += 1
            continue

        item["lat"]     = new_lat
        item["lon"]     = new_lon
        item["geocode"] = "kakao"
        updated += 1

        log_lines.append(
            f"{item['district']} | {label[:35]:<35} | {dist:>6.0f}m | {best.get('place_name','')}"
        )
        if dist >= 300:
            print(f"  ✅ {item['district']} {label[:30]} | {dist:.0f}m → {best.get('place_name','')}")

        if (seq + 1) % 200 == 0:
            print(f"  {seq+1}/{len(targets)} | 교체:{updated} 스킵:{skipped} 오류:{error}", flush=True)

    print(f"\n=== 완료 ===")
    print(f"  교체: {updated}건")
    print(f"  스킵: {skipped}건")
    print(f"  오류: {error}건")

    with open(INPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n→ {INPUT} 저장 완료")

    log_file = f"improve_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"교체 항목 ({updated}건)\n" + "=" * 80 + "\n")
        f.write("\n".join(log_lines))
    print(f"→ {log_file} 저장 완료")
    print(f"\n다음: git add data.json && git commit && git push")


if __name__ == "__main__":
    main()
