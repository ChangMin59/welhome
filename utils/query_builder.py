def escape(value: str) -> str:
    return value.replace("'", "''")

def build_where_clause(user_state: dict) -> str:
    conditions = []

    if user_state.get("계층"):
        user_type = escape(user_state["계층"])
        conditions.append(f"('{user_type}' = p.eligible_user_type OR p.eligible_user_type = '전체')")

    if user_state.get("무주택") is True:
        conditions.append("p.is_no_house = 1")

    if user_state.get("세대주") is True:
        conditions.append("p.is_householder = 1")
    elif user_state.get("세대주") is False:
        conditions.append("p.is_householder = 0")

    if user_state.get("총자산") is not None:
        conditions.append(f"{user_state['총자산']} <= ar.max_asset")

    if user_state.get("자동차가액") is not None:
        conditions.append(f"{user_state['자동차가액']} <= ar.max_car_value")

    if user_state.get("소득") is not None:
        try:
            income = int(user_state["소득"])
            conditions.append(
                f"{income} <= ref.income * ("
                f"CASE WHEN p.has_bonus_score = 1 THEN ir.income_limit_pct + IFNULL(br.point, 0) "
                f"ELSE ir.income_limit_pct END)"
            )
        except ValueError:
            pass

    return "WHERE " + " AND ".join(conditions) if conditions else ""
