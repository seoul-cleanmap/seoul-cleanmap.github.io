# -*- coding: utf-8 -*-
"""
지오코딩 정확도 개선 도구
- vworld 지오코딩 항목을 Kakao Local Search로 재검증 후 좌표 교체
- 신뢰 전략:
    1) 버스정류장 (ARS 번호 포함): 카카오 버스정류장 카테고리 결과 우선
    2) 지하철역 출구: 카카오 지하철 카테고리 결과 우선
    3) 일반 POI: 50m 이상 차이 + 카카오 결과가 서울 내 + 이름 유사할 때만 교체
- data.json 덮어쓰기 전 자동 백업

사용법:
  1. KAKAO_API_KEY에 카카오 REST API 키 입력
  2. python improve_geocode.py
  3. 완료 후 python build_data.py 없이 바로 data.json 사용 가능

"""
import json, time, math, re, shutil, sys, urllib.request, urllib.parse
from datetime import datetime

KAKAO_API_KEY = "553e2e606a80c405fff3f61fa3adc613"
INPUT  = "data.json"
DELAY  = 0.12
MIN_DIST_TO_UPDATE = 50    # 50m 미만 차이는 교체하지 않음 (오히려 나빠질 수 있음)
SEOUL_BOUNDS = (37.41, 37.72, 126.76, 127.19)

# 버스정류장 ARS 번호 패턴: (08-010), (23-233) 등
ARS_PATTERN   = re.compile(r'\((\d{2,3}-\d{3,4})\)')
# 지하철역 출구 패턴
SUBWAY_PATTERN = re.compile(r'.+역\s*\d+번\s*출구')


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def in_seoul(lat, lon):
    return (SEOUL_BOUNDS[0] <= lat <= SEOUL_BOUNDS[1] and
            SEOUL_BOUNDS[2] <= lon <= SEOUL_BOUNDS[3])


def kakao_search(query, size=5):
    params = {"query": query, "size": size}
    url = "https://dapi.kakao.com/v2/local/search/keyword.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"KakaoAK {KAKAO_API_KEY}",
        "User-Agent":    "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read()).get("documents", [])


def find_busstop(docs, label):
    """버스정류장 결과 선택 - ARS 번호 일치 > 카테고리 일치"""
    ars_m = ARS_PATTERN.search(label)
    ars   = ars_m.group(1) if ars_m else None

    candidates = [d for d in docs
                  if "버스" in d.get("category_name", "")
                  or "정류장" in d.get("place_name", "")]
    if not candidates:
        return None

    # ARS 번호가 장소명에 포함된 결과 우선
    if ars:
        for d in candidates:
            if ars in d.get("place_name", ""):
                return d

    return candidates[0]


def find_subway(docs):
    """지하철역 출구 결과 선택"""
    for d in docs:
        cat = d.get("category_name", "")
        if "지하철" in cat or "철도" in cat:
            return d
    return None


def name_overlap(label, kakao_name):
    """label과 kakao_name의 한글 어절 겹침 비율 (간단한 유사도)"""
    def words(s):
        return set(re.findall(r'[가-힣a-zA-Z0-9]+', s))
    lw = words(label)
    kw = words(kakao_name)
    # 1~2글자 불용어 제거
    stopwords = {'앞', '옆', '근처', '내', '및', '앞쪽', '쪽'}
    lw -= stopwords
    if not lw:
        return 0.0
    return len(lw & kw) / len(lw)


def main():
    if not KAKAO_API_KEY:
        print("❌  KAKAO_API_KEY를 스크립트 상단에 입력하세요.")
        sys.exit(1)

    with open(INPUT, encoding="utf-8") as f:
        data = json.load(f)

    # 백업
    backup = f"data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    shutil.copy(INPUT, backup)
    print(f"백업 완료: {backup}")

    targets = [(i, d) for i, d in enumerate(data) if d.get("geocode") == "vworld"]
    print(f"vworld 항목 {len(targets)}건 처리 시작\n")

    updated = skipped = error = 0
    log_lines = []  # 교체된 항목 로그

    for seq, (idx, item) in enumerate(targets):
        label    = item.get("label", "")
        district = item.get("district", "")
        cur_lat  = item["lat"]
        cur_lon  = item["lon"]

        is_busstop = bool(ARS_PATTERN.search(label)) or "버스정류장" in label or "정류장" in label
        is_subway  = bool(SUBWAY_PATTERN.match(label))

        try:
            query = f"서울 {district} {label}"
            docs  = kakao_search(query, size=5)
            time.sleep(DELAY)
        except Exception as e:
            error += 1
            if error <= 10:
                print(f"  API 오류({label[:20]}): {e}")
            continue

        # --- 후보 선택 ---
        best = None
        if is_busstop:
            best = find_busstop(docs, label)
        elif is_subway:
            best = find_subway(docs)
        else:
            # 일반 POI: 이름 유사도가 40% 이상인 첫 번째 결과
            for d in docs[:3]:
                if name_overlap(label, d.get("place_name", "")) >= 0.4:
                    best = d
                    break

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

        # 교체
        item["lat"]     = new_lat
        item["lon"]     = new_lon
        item["geocode"] = "kakao"
        updated += 1

        log_lines.append(
            f"{district} | {label[:35]:<35} | {dist:>6.0f}m | {best.get('place_name','')}"
        )
        if dist >= 300:
            print(f"  ✅ {district} {label[:30]} | {dist:.0f}m 이동 → {best.get('place_name','')}")

        if (seq + 1) % 200 == 0:
            print(f"  {seq+1}/{len(targets)} | 교체:{updated} 스킵:{skipped} 오류:{error}", flush=True)

    print(f"\n=== 완료 ===")
    print(f"  교체: {updated}건")
    print(f"  스킵: {skipped}건 (카카오 미발견 or 50m 미만 차이)")
    print(f"  오류: {error}건")

    with open(INPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n→ {INPUT} 저장 완료")

    # 교체 로그 저장
    log_file = f"improve_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"교체 항목 ({updated}건)\n")
        f.write("="*80 + "\n")
        f.write("\n".join(log_lines))
    print(f"→ {log_file} 저장 완료")
    print(f"\n다음 단계: 검수 후 이상 없으면 git add data.json && git push")


if __name__ == "__main__":
    main()
