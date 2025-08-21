import sqlite3
from typing import Optional

DB_PATH = "/home/alpaco/lyj0622/project_real/data/housing_type.db"

def get_region_code(region_name: str) -> Optional[str]:
    if not region_name:
        return None

    region_name = region_name.strip()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = """
            SELECT cnp_cd
            FROM region_code
            WHERE cnp_name LIKE ?
            LIMIT 1
        """
        cursor.execute(query, (f"%{region_name}%",))
        row = cursor.fetchone()

        return row[0] if row else None

    except Exception as e:
        print(f"❗ 지역 코드 조회 중 오류 발생: {e}")
        return None

    finally:
        if 'conn' in locals():
            conn.close()
