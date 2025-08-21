import sqlite3
from typing import List, Dict
from utils.query_builder import build_where_clause

DEFAULT_DB_PATH = "/home/alpaco/lyj0622/project_real/data/housing_type.db"

def search_housing_by_condition(user_state: dict, db_path: str = DEFAULT_DB_PATH) -> List[Dict]:
    """
    사용자 상태 기반 WHERE 조건을 붙여 임대주택 유형 검색
    Returns: [{house_id: ..., house_name: ..., supply_type: ...}, ...]
    """
    where_clause = build_where_clause(user_state)
    household_size = user_state.get("가구원수") or 1

    query = f"""
        SELECT DISTINCT p.house_id, p.house_name, p.supply_type
        FROM program p
        JOIN income_rule ir ON p.income_rule_id = ir.income_rule_id
        JOIN income_reference ref 
          ON ir.income_code = ref.income_code
          AND ref.house_id = p.house_id
          AND ref.household_size = :household_size
        JOIN asset_rule ar ON p.asset_rule_id = ar.asset_rule_id
        LEFT JOIN bonus_rule br 
          ON p.house_id = br.house_id 
          AND br.household_size = :household_size
        {where_clause}
    """

    print("\n📤 [생성된 SQL 쿼리문]:")
    print(query)
    print(f"\n📌 household_size = {household_size}\n")

    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, {"household_size": household_size})
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"❌ [DB 오류] 조건 검색 중 문제가 발생했습니다: {e}")
        return []
