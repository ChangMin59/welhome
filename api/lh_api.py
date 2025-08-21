import requests
from typing import List, Dict, Optional

BASE_URL_LIST = "http://apis.data.go.kr/B552555/lhLeaseNoticeInfo1/lhLeaseNoticeInfo1"

SERVICE_KEY = "7vXPD/NjWQN8i2+WYXCvpQVfowXrB8W1YFHf2mRHuvPSZxx2M+yYddqPSpZvo/a51IkboF0fJJnnKJOByy1F8Q=="

def get_notices_by_house_ids(house_ids: List[str], region_code: Optional[str] = None) -> List[Dict]:
    params = {
        "serviceKey": SERVICE_KEY,
        "PG_SZ": "100",
        "PAGE": "1",
        "UPP_AIS_TP_CD": "06",
        "PAN_SS": "공고중",
        "_type": "json"
    }
    if region_code:
        params["CNP_CD"] = region_code

    house_ids = list(set(map(str, house_ids)))
    print(f"\n🎯 필터링할 house_ids: {house_ids}")

    try:
        response = requests.get(BASE_URL_LIST, params=params, timeout=10)
        print(f"📡 응답 코드: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❗ API 요청 실패: {response.status_code} {response.reason}")
            print("🔍 응답 내용:\n", response.text)
            return []

        try:
            data = response.json()
        except ValueError:
            print("❗ JSON 파싱 실패! 응답 내용:\n", response.text)
            return []

        result = []
        iterable = data.values() if isinstance(data, dict) else data
        for block in iterable:
            if isinstance(block, dict) and "dsList" in block:
                for item in block["dsList"]:
                    if str(item.get("AIS_TP_CD")) in house_ids:
                        result.append({
                            "PAN_ID": item.get("PAN_ID"),
                            "PAN_NM": item.get("PAN_NM")
                        })
        return result

    except requests.exceptions.RequestException as e:
        print(f"❗ 요청 에러 발생: {e}")
        return []
