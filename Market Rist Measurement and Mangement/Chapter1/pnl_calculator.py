def cal_pnl(df):
    result = df.copy()
    result["pnl"] = (
        result["book_value"]
        + result["interim_payments"]
        - result["book_value"].shift(1)
    )
    return result


def cal_pvpnl(df):
    result = df.copy()
    daily_rate = result["discount_rate"] / 252

    result["pvpnl"] = (
        (result["book_value"] + result["interim_payments"])
        / (1 + daily_rate)
        - result["book_value"].shift(1)
    )
    return result


def cal_fvpnl(df):
    result = df.copy()
    daily_rate = result["discount_rate"] / 252

    result["fvpnl"] = (
        result["book_value"]
        + result["interim_payments"]
        - result["book_value"].shift(1) * (1 + daily_rate)
    )
    return result
