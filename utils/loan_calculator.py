import sqlite3
import pandas as pd

DB_PATH = "/home/alpaco/lyj0622/project/data/loan_type.db"

def calculate_cost_total(row, amount, years):
    rate = row["rate_avg_prev"]
    repay_type = row["repay_type"]
    r = rate / 100

    if repay_type == "만기일시상환":
        total = amount + (amount * r * years)
        return round(total)

    elif repay_type == "원리금분할상환":
        monthly_rate = r / 12
        n = years * 12
        if monthly_rate == 0:
            monthly_payment = amount / n
        else:
            monthly_payment = amount * monthly_rate * (1 + monthly_rate) ** n / ((1 + monthly_rate) ** n - 1)
        total = monthly_payment * n
        return round(total)

    elif repay_type == "원금분할상환":
        n = years * 12
        monthly_principal = amount / n
        total = 0
        for i in range(1, n + 1):
            remaining_principal = amount - monthly_principal * (i - 1)
            interest = remaining_principal * (r / 12)
            total += monthly_principal + interest
        return round(total)
    else:
        return None

def get_table_text(loan_amount, loan_years, db_path):
    conn = sqlite3.connect(db_path)
    query = """
        SELECT 
            bank,
            product,
            repay_type,
            rate_avg_prev,
            limit_amt
        FROM loan_products
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["cost_total"] = df.apply(
        lambda row: calculate_cost_total(row, loan_amount, loan_years),
        axis=1
    )

    df_filtered = df[df["limit_amt"] >= loan_amount]
    df_sorted = df_filtered.sort_values(["bank", "cost_total"])
    best_two = df_sorted.groupby("bank").head(2).reset_index(drop=True)

    if best_two.empty:
        return None
    
    return best_two.to_markdown(index=False)
