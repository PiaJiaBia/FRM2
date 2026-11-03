"""第 11 章：Regression Hedging and Principal Component Analysis。
教材 pp. 136–145；PDF 页序 = 教材页码 + 11。
输入由调用方保证有效；利率/收益率均用小数，时间以年为单位（另注除外）。
"""
import numpy as np
import pandas as pd

class RegressionHedge:
    """pp.136–141：单变量和多变量 OLS 共用同一接口；输入已对齐。"""
    def __init__(self, df, target_column, predictor_columns):
        self.predictor_columns=list(predictor_columns)
        x=np.column_stack([np.ones(len(df)),df[predictor_columns]])
        y=df[target_column].to_numpy()
        self.coefficients=np.linalg.lstsq(x,y,rcond=None)[0]
        residual=y-x@self.coefficients
        self.residual_variance=residual@residual/(len(y)-x.shape[1])
        self.covariance=self.residual_variance*np.linalg.inv(x.T@x)

    def predict(self, df):
        return pd.Series(np.column_stack([np.ones(len(df)),df[self.predictor_columns]])@self.coefficients,index=df.index)

    def hedge_positions(self, target_dv01, hedges, dv01_column):
        # 对冲头寸的带符号数量；同一方向定义 DV01 时需反向交易。
        return pd.Series(-target_dv01*self.coefficients[1:]/hedges[dv01_column].to_numpy(),index=self.predictor_columns)

    def summary(self):
        se=np.sqrt(np.diag(self.covariance))
        return pd.DataFrame({'coefficient':self.coefficients,'standard_error':se},index=['intercept',*self.predictor_columns])

class PrincipalComponents:
    """pp.142–145：对原始变动的协方差做 PCA；不自动标准化成相关矩阵。"""
    def __init__(self, df, target_columns):
        self.columns=list(target_columns)
        self.mean=df[target_columns].mean()
        covariance=df[target_columns].cov().to_numpy()
        values,vectors=np.linalg.eigh(covariance)
        order=np.argsort(values)[::-1]
        self.eigenvalues=values[order]
        self.eigenvectors=vectors[:,order]

    def transform(self, df, n_components):
        scores=(df[self.columns]-self.mean).to_numpy()@self.eigenvectors[:,:n_components]
        return pd.DataFrame(scores,index=df.index,columns=[f'PC{i+1}' for i in range(n_components)])

    def loadings(self):
        # 每一列是一个标准差冲击；特征向量整体正负号没有经济区别。
        return pd.DataFrame(self.eigenvectors*np.sqrt(self.eigenvalues),index=self.columns)

    def explained_variance(self):
        return pd.Series(self.eigenvalues/self.eigenvalues.sum(),name='explained_variance')

    def hedge_positions(self, target, hedges):
        """p.145：target 一行 k 因子敞口，hedges 为 k 个工具的 k 因子敞口。"""
        return pd.Series(np.linalg.solve(hedges.to_numpy().T,-target.to_numpy().ravel()),index=hedges.index)
