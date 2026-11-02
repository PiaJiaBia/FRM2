import numpy as np

def cal_arithmetic_return(df):
    result = df.copy()
    result["arithmetic_return"] = (
        (result["book_value"] + result["interim_payments"])
        / result["book_value"].shift(1)
        - 1
    )
    return result


def cal_geometric_return(df):
    result = df.copy()
    result["geometric_return"] = np.log(
        (result["book_value"] + result["interim_payments"])
        / result["book_value"].shift(1)
    )
    return result