# -*- coding: utf-8 -*-
"""
지오코딩 검수 도구
- data.json의 vworld 좌표를 Kakao Local Search로 교차검증
- 거리 차이가 크거나 카카오에서 찾지 못한 항목을 CSV로 출력

사용법:
  1. KAKAO_API_KEY에 카카오 REST API 키 입력
  2. python verify_geocode.py
  3. verify_result.csv 확인 (Excel에서 열기 권장)

"""
import json, csv, time, math, urllib.request, urllib.parse, sys

KAKAO_API_KEY = "553e2e606a80c405fff3f61fa3adc613"
INPUT      = "data.json"
OUTPUT_CSV = "verify_result.csv"
THRESHOLD_SUSPECT = 200  # 이 거리(m) 이상 차이나면 SUSPECT
THRESHOLD_BAD     = 500  # 이 거리(m) 이상이면 BAD
DELAY = 0.12


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def kakao_search(query, size=3):
    params = {"query": query, "size": size}
    url = "https://dapi.kakao.com/v2/local/search/keyword.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"KakaoAK {KAKAO_API_KEY}",
        "User-Agent":    "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read()).get("documents", [])


def classify(dist_m):
    if dist_m is None:     return "NOT_FOUND"
    if dist_m < THRESHOLD_SUSPECT: return "OK"
    if dist_m < THRESHOLD_BAD:     return "SUSPECT"
    return "BAD"


def main():
    if not KAKAO_API_KEY:
        print("❌  KAKAO_API_KEY를 스크립트 상단에 입력하세요.")
        sys.exit(1)

    with open(INPUT, encoding="utf-8") as f:
        data = json.load(f)

    targets = [d for d in data if d.get("geocode") == "vworld"]
    print(f"vworld 항목 {len(targets)}건 검수 시작\n")

    rows = []
    counts = {"OK": 0, "SUSPECT": 0, "BAD": 0, "NOT_FOUND": 0, "ERROR": 0}

    for i, item in enumerate(targets):
        label    = item.get("label", "")
        district = item.get("district", "")
        cur_lat  = item.get("lat")
        cur_lon  = item.get("lon")

        try:
            docs = kakao_search(f"서울 {district} {label}", size=3)
            time.sleep(DELAY)
        except Exception as e:
            print(f"  [{i+1}] API 오류: {e}")
            counts["ERROR"] += 1
            continue

        if not docs:
            status   = "NOT_FOUND"
            dist_m   = None
            k_lat = k_lon = k_name = k_cat = ""
        else:
            best  = docs[0]
            k_lat = float(best["y"])
            k_lon = float(best["x"])
            k_name = best.get("place_name", "")
            k_cat  = best.get("category_name", "")
            dist_m = haversine(cur_lat, cur_lon, k_lat, k_lon)
            status = classify(dist_m)

        counts[status] += 1

        # OK는 CSV에서 제외 (의심 항목만 기록)
        if status == "OK":
            if (i + 1) % 200 == 0:
                print(f"  {i+1}/{len(targets)} | " +
                      " | ".join(f"{k}:{v}" for k, v in counts.items()), flush=True)
            continue

        rows.append({
            "status":    status,
            "district":  district,
            "label":     label,
            "road":      item.get("road", ""),
            "cur_lat":   cur_lat,
            "cur_lon":   cur_lon,
            "kakao_lat": k_lat,
            "kakao_lon": k_lon,
            "dist_m":    round(dist_m, 1) if dist_m is not None else "",
            "kakao_name": k_name,
            "kakao_cat":  k_cat,
            # 현재 좌표 카카오맵 링크
            "cur_map":   f"https://map.kakao.com/link/map/{label},{cur_lat},{cur_lon}",
            # 카카오 검색 결과 좌표 링크
            "kakao_map": f"https://map.kakao.com/link/map/{k_name},{k_lat},{k_lon}" if k_lat else "",
        })

        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(targets)} | " +
                  " | ".join(f"{k}:{v}" for k, v in counts.items()), flush=True)

    print(f"\n=== 검수 결과 ===")
    for k, v in counts.items():
        print(f"  {k:12s}: {v}건")

    # BAD → SUSPECT → NOT_FOUND 순 정렬
    order = {"BAD": 0, "SUSPECT": 1, "NOT_FOUND": 2}
    rows.sort(key=lambda r: (order.get(r["status"], 9),
                              -(r["dist_m"] or 0)))

    fields = ["status","district","label","road",
              "cur_lat","cur_lon","kakao_lat","kakao_lon",
              "dist_m","kakao_name","kakao_cat",
              "cur_map","kakao_map"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"\n→ {OUTPUT_CSV} 저장 완료 ({len(rows)}건, OK 제외)")
    print(f"  BAD+SUSPECT: {counts['BAD']+counts['SUSPECT']}건 → improve_geocode.py로 개선 가능")


if __name__ == "__main__":
    main()
