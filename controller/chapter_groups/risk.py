"""第2–7章网页调用边界；公式全部复用教材 service，输入不自动删行。"""
import math
import numpy as np
import pandas as pd
from scipy.stats import norm
from service import load_chapter


def number(name, label, default, minimum=None, maximum=None):
    return dict(name=name, label=label, type='number', default=default, min=minimum, max=maximum)


def column(name, default, label=None):
    return dict(name=name, label=label or name, type='column', default=default)


def choice(name, label, values, default):
    return dict(name=name, label=label, type='select', default=default,
                options=[dict(value=v, label=t) for v, t in values])


def structured(name, label, default):
    return dict(name=name, label=label, type='json', default=default)


ALPHA = number('confidence_level', '风险置信水平', .95, .001, .9999)
SEED = number('seed', '随机种子', 42, 0, 4294967295)
TARGET = column('target_column', 'loss', '目标列')
COLS = dict(name='target_columns', label='按矩阵顺序选择因子列', type='columns', default=['x', 'y'])
PAGES = {2:'18–34', 3:'36–47', 4:'50–57', 5:'60–72', 6:'74–84', 7:'89–100'}


def operations():
    definitions = [
        (2, 'distribution', '历史 / 核分布风险', 'VaRα=Q(α); ESα=∫α¹Q(p)dp/(1−α)',
         [TARGET, ALPHA, choice('model','损失分布',[('historical','等权历史'),('age','时间衰减'),('weighted','自定义权重'),('kernel','高斯核')],'historical'),
          column('weight_column','weight','权重列（自定义权重）'),number('decay','时间衰减系数',.97,.001,.99999),
          number('bandwidth','KDE带宽因子',.3,.001,10),structured('bracket','KDE求根区间 [下界,上界]',[-10,20]),number('interval_confidence','顺序统计区间置信水平',.95,.001,.999)]),
        (2, 'scenarios', '因子情景与波动调整', 'x*=Lforecast Lhistory⁻¹x; r*=r σforecast/σhistory',
         [choice('method','情景方法',[('levels','当前水平映射'),('volatility','波动调整'),('correlation','相关调整'),('filtered','单期过滤抽样')],'volatility'),
          TARGET,COLS,column('volatility_column','vol','历史波动率列'),number('forecast_volatility','预测波动率',2,.000001,100),
          structured('current_levels','当前水平一行数组（所选因子顺序）',[100,200]),
          structured('historical_covariance','历史协方差矩阵',[[1,.3],[.3,1]]),structured('forecast_covariance','预测协方差矩阵',[[1,.9],[.9,1]]),
          number('n_scenarios','情景数量',200,1,10000),SEED]),
        (2, 'garch', '非对称GARCH与过滤路径', 'hₜ=ω+α(εₜ₋₁+γ)²+βhₜ₋₁',
         [column('target_column','x','收益率列'),choice('method','估计方式',[('specified','指定参数'),('fit','高斯QMLE拟合')],'specified'),
          structured('initial_parameters','参数 [omega,alpha,beta,gamma,mean]',[.01,.1,.8,.02,0]),
          structured('bounds','拟合参数边界（依参数顺序）',[[.000001,1],[0,.99],[0,.99],[-1,1],[-1,1]]),
          number('initial_variance','初始方差',.04,.000001,100),number('horizon','模拟步数',5,1,100),number('n_paths','路径数量',100,1,1000),SEED]),
        (2, 'bootstrap', 'IID / 区块Bootstrap', '整行同步 circular moving-block 重采样',
         [TARGET,ALPHA,choice('estimator','估计量',[('var','历史VaR'),('es','历史ES'),('mean','样本均值')],'var'),
          number('block_size','区块长度（1为IID）',1,1,10000),number('n_resamples','重采样次数',200,2,2000),SEED]),
        (3, 'gev', '区块极值 / GEV', 'Fmax(x)=Fparent(x)^m; ξ 为教材尾指数',
         [TARGET,column('block_column','block','区块分组列'),choice('sample_mode','样本类型',[('maxima','输入已经是区块最大值'),('raw','按分组列提取最大值')],'maxima'),
          choice('method','GEV估计',[('specified','指定参数'),('mle','最大似然'),('moments','Gumbel矩估计'),('regression','Gumbel分位数回归'),('quantile','GEV非线性分位数回归')],'specified'),
          structured('initial_parameters','参数 [location,scale,shape]',[2,.7,.3]),structured('bounds','分位数回归 [下界数组,上界数组]',[[-10,.001,-.9],[10,10,.9]]),
          number('block_size','母分布区块大小',100,1,10000),number('confidence_level','母分布风险置信水平',.995,.001,.99999)]),
        (3, 'pot', '阈值超越 / GPD', 'qα=u+β/ξ[(Nu/n/(1−α))^ξ−1]',
         [TARGET,choice('method','参数来源',[('specified','指定参数'),('mle','最大似然'),('moments','矩估计')],'specified'),
          number('threshold','损失阈值',2),number('scale','尺度β',.8,.000001,100),number('shape','尾指数ξ',.15,-5,.999),
          number('tail_probability','阈值超越概率',.04,.00001,.99999),number('confidence_level','风险置信水平',.995,.001,.99999)]),
        (3, 'tail', 'Hill / Pickands与尾外推', 'ξHill=mean(log(Xi/Xk+1)); qα=u[pTail/(1−α)]^ξ',
         [TARGET,number('tail_count','尾部阶数k',5,1,10000),number('threshold','外推阈值',2,.000001,100000),number('tail_probability','阈值超越概率',.1,.00001,.99999),ALPHA]),
        (4, 'coverage', 'VaR覆盖率回测', 'LRuc; LRind; LRcc=LRuc+LRind',
         [choice('input_mode','异常数据来源',[('loss_var','比较损失与提前预测VaR'),('hits','已有0/1异常序列')],'loss_var'),
          TARGET,column('var_column','var','VaR列'),column('hit_column','hit','异常指示列'),ALPHA]),
        (4, 'counts', '异常次数与教材交通灯', 'X∼Binomial(n,1−α)',
         [number('sample_size','样本期间数',250,1,100000),number('confidence_level','风险置信水平',.99,.001,.9999),number('exception_count','异常次数',7,0,100000)]),
        (5, 'linear', '线性映射 / 成分 / 跟踪VaR', 'VaR=zα√(xᵀΣx); component=x·marginal',
         [column('target_column','value','因子敞口列'),column('benchmark_column','benchmark','基准敞口列'),structured('covariance','同序因子协方差矩阵',[[.04,.01],[.01,.09]]),ALPHA]),
        (5, 'cashflows', '现金流折现与久期映射', 'PV=CF/(1+r/f)^(ft); w=(Dupper−D)/(Dupper−Dlower)',
         [column('cashflow_column','cash','现金流列'),column('rate_column','rate','小数利率列'),column('maturity_column','time','期限列（年）'),
          column('duration_column','duration','久期列（年）'),number('frequency','每年复利次数',1,1,365),number('lower_duration','下节点久期',1),number('upper_duration','上节点久期',3)]),
        (5, 'derivatives', '外汇远期 / FRA / 互换映射', '远期=外币零息资产−本币零息负债；FRA=Nδ(F−K)DF',
         [choice('instrument','工具',[('forward','外汇远期'),('fra','FRA'),('swap','重置日互换')],'forward'),number('spot','即期汇率',1.2,.000001),number('strike','远期约定汇率',1.25,.000001),
          number('domestic_rate','本币连续利率',.04),number('foreign_rate','外币连续利率',.02),number('maturity','期限（年）',2,0),number('quantity','外币数量',1),
          number('notional','名义本金',100,0),number('forward_rate','远期利率',.04),number('contract_rate','合约利率',.03),number('accrual','计息年分数',.5,.000001),number('payment_discount','支付折现因子',.97,.000001),column('accrual_column','accrual','逐期计息年分数列')]),
        (5, 'delta_gamma', 'Delta–Gamma损益', 'ΔV≈δΔS+½γ(ΔS)²',
         [column('target_column','change','标的绝对价格变动列'),number('delta','Delta',.5),number('gamma','Gamma',.2)]),
        (6, 'sensitivity', '有限差分参数敏感度', 'dV/dx≈[V(x+h)−V(x−h)]/(2h)',
         [column('target_column','value','逐行因子敞口参数列'),structured('covariance','同序因子协方差矩阵',[[.04,.01],[.01,.09]]),ALPHA,number('bump','中心差分步长',.001,.00000001,10)]),
        (6, 'intervals', '分位数 / 排序 / 异常率区间', 'SE(q)=√[p(1−p)/n]/f(q); F(Xrank)∼Beta(rank,n+1−rank)',
         [choice('method','区间类型',[('quantile','分位数渐近区间'),('order','顺序统计概率区间'),('exceptions','精确异常率区间')],'quantile'),
          number('estimate','分位数估计',1.645),number('probability','分位数概率',.95,.001,.999),number('density','分位点密度',.103,.000001),
          number('sample_size','样本数',100,2,1000000),number('rank','顺序统计量阶数（从1开始）',50,1,1000000),number('exceptions','异常次数',5,0,1000000),number('interval_confidence','区间置信水平',.95,.001,.999)]),
        (6, 'benchmark', '估计与基准比较', 'difference=estimate−benchmark; ratio=estimate/benchmark',
         [column('target_column','value','估计列'),column('benchmark_column','benchmark','同口径基准列')]),
        (7, 'pit', 'PIT变换与分布诊断', 'uₜ=Fₜ(xₜ); KS / CVM / AD',
         [column('target_column','x','观测列 / PIT列'),choice('input_mode','输入模式',[('normal','逐期正态预测分布'),('pit','已有PIT')],'normal'),
          column('mean_column','mean','提前预测均值列'),column('std_column','std','提前预测标准差列')]),
        (7, 'dependence', 'PIT / 异常动态与持续期', 'Ljung–Box Q; 正态化PIT回归; LPM / logit / Weibull LR',
         [choice('method','检验方法',[('ljung_box','Ljung–Box'),('pit_regression','正态化PIT回归'),('lpm','线性概率模型'),('logit','异常Logit'),('duration','完整异常间隔')],'ljung_box'),
          column('target_column','hit','检验目标列（按方法选择）'),dict(name='predictor_columns',label='已对齐预测变量列',type='columns',default=['x']),number('max_lag','最大滞后',5,1,1000),number('exception_probability','异常发生概率',.05,.00001,.99999)]),
    ]
    return [dict(id=f'ch{n}_{key}',chapter=n,name=name,workspace=f'ch{n}_{key}',description=name,
                 formula=formula,pages=PAGES[n],assumptions=[
                     '收益率与利率用小数；输入列须同口径、有限且已按时间对齐，不自动删行或改变符号。',
                     '示例为固定种子演示或已注明的教材构造值；不是实际市场数据。'],
                 parameters=params,example_id=f'ch{n}_{key}') for n,key,name,formula,params in definitions]


def examples():
    return [dict(id=o['example_id'],chapter=o['chapter'],name=f"第{o['chapter']}章 · {o['name']}",
                 description=f"教材 pp. {o['pages']} 的接口演示；固定种子或构造样本，不是教材原始观测。") for o in operations()]


def example_frame(example_id):
    op=next((o for o in operations() if o['example_id']==example_id),None)
    if op is None: raise ValueError('未知第2–7章示例')
    rng=np.random.default_rng(42)
    n=300
    x=rng.normal(0,.2,n)
    frame=pd.DataFrame(dict(x=x,y=rng.normal(0,.2,n),loss=rng.exponential(1,n)+2,
                            vol=np.full(n,.2),weight=np.ones(n),block=np.arange(n)//10))
    if op['chapter']==4:
        loss=rng.normal(size=250)
        frame=pd.DataFrame(dict(loss=loss,var=np.full(250,norm.ppf(.95)),hit=(loss>norm.ppf(.95)).astype(int)))
    if example_id in ('ch5_linear','ch6_sensitivity','ch6_benchmark'):
        frame=pd.DataFrame(dict(value=[100.,50.],benchmark=[80.,40.]))
    if example_id in ('ch5_cashflows','ch5_derivatives'):
        frame=pd.DataFrame(dict(cash=[5.,105.],rate=[.05,.05],time=[1.,2.],duration=[1.,2.],accrual=[.5,.5]))
    if example_id=='ch5_delta_gamma': frame=pd.DataFrame(dict(change=[-1.,0.,1.]))
    if op['chapter']==7:
        x=rng.normal(size=500)
        frame=pd.DataFrame(dict(x=x,mean=np.zeros(500),std=np.ones(500),pit=norm.cdf(x),hit=(rng.random(500)<.1).astype(int)))
    metadata={'chapter':op['chapter'],'example_id':example_id,'source':'固定种子42/构造样本；非实际行情',
              'fields':{str(c):dict(kind='other',unit='other',sign='none') for c in frame.columns}}
    return frame,metadata


def _numbers(df, columns, minimum=1):
    if len(df)<minimum: raise ValueError(f'至少需要{minimum}行')
    if isinstance(columns,str): columns=[columns]
    if not columns or len(set(columns))!=len(columns): raise ValueError('请选择不重复的数据列')
    for c in columns:
        if c not in df or not pd.api.types.is_numeric_dtype(df[c]) or not np.isfinite(df[c].to_numpy(dtype=float)).all():
            raise ValueError(f'{c}须为无缺失的有限数值列')
    return df[columns]


def _matrix(value,n,positive=False):
    a=np.asarray(value,dtype=float)
    if a.shape!=(n,n) or not np.isfinite(a).all() or not np.allclose(a,a.T): raise ValueError('矩阵须为与因子数相符的有限对称方阵')
    eigen=np.linalg.eigvalsh(a)
    if np.min(eigen)<-1e-12 or (positive and np.min(eigen)<=0): raise ValueError('协方差矩阵须半正定（Cholesky要求正定）')
    return pd.DataFrame(a)


def _scalar(x):
    if isinstance(x,np.generic): x=x.item()
    if isinstance(x,float) and not math.isfinite(x): return None if math.isnan(x) else str(x)
    return x


def _result(value,notes=None,metrics=None):
    metrics=metrics or []
    tables=[]; charts=[]
    if isinstance(value,pd.Series): metrics += [dict(name=str(k),value=_scalar(v)) for k,v in value.items()]
    elif isinstance(value,pd.DataFrame):
        frame=value.copy(); frame.columns=frame.columns.map(str)
        if not isinstance(frame.index,pd.RangeIndex): frame=frame.reset_index(names='row')
        tables=[dict(name='计算结果',columns=list(frame.columns),rows=[{str(k):_scalar(v) for k,v in row.items()} for row in frame.to_dict('records')])]
        numeric=list(frame.select_dtypes(include=np.number).columns)[:8]
        positions=np.unique(np.linspace(0,len(frame)-1,min(len(frame),600)).astype(int)) if len(frame) else []
        charts=[dict(title='结果序列（最多8列、600点；完整值见表格）',x_label='结果行序号',y_label='原始单位',series=[dict(name=c,type='line',data=[[int(i),float(frame[c].iloc[i]) if np.isfinite(frame[c].iloc[i]) else None] for i in positions]) for c in numeric])] if numeric else []
    else: metrics.append(dict(name='计算值',value=_scalar(value)))
    return dict(metrics=metrics,tables=tables,charts=charts,notes=(notes or [])+['未自动删行、补值或变更单位；NaN为空，无穷值保留字符串。'])


def calculate(df,metadata,request):
    op=next((o for o in operations() if o['id']==request.get('operation')),None)
    if op is None: raise ValueError('未知第2–7章操作')
    supplied=request.get('parameters') or {}
    if not isinstance(supplied,dict): raise ValueError('参数须为对象')
    p={v['name']:v.get('default') for v in op['parameters']}; p.update(supplied)
    for spec in op['parameters']:
        v=p[spec['name']]
        if spec['type']=='number':
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v): raise ValueError(f"{spec['label']}须为有限数值")
            if spec.get('min') is not None and v<spec['min'] or spec.get('max') is not None and v>spec['max']: raise ValueError(f"{spec['label']}超出允许范围")
        if spec['type']=='select' and v not in [s['value'] for s in spec['options']]: raise ValueError(f"未知{spec['label']}")
    integers={'seed','n_scenarios','horizon','n_paths','n_resamples','block_size','tail_count','sample_size','exception_count','frequency','rank','exceptions','max_lag'}
    for key in integers & p.keys():
        if int(p[key])!=p[key]: raise ValueError(f'{key}须为整数')
        p[key]=int(p[key])
    n=op['chapter']; key=op['id'].split('_',1)[1]; m=load_chapter(n)
    c=p.get('target_column'); alpha=p.get('confidence_level',.95)
    notes=[f"教材 pp. {op['pages']}；当前输入元数据不代替口径核对。"]
    metrics=[]
    if n==2:
        if key=='distribution':
            _numbers(df,c,2); model=p['model']
            if model=='kernel':
                if df[c].std()==0: raise ValueError('KDE样本方差须为正')
                distribution=m.KernelDistribution(df,c,p['bandwidth'])
                bracket=np.asarray(p['bracket'],dtype=float)
                if bracket.shape!=(2,) or not np.isfinite(bracket).all() or bracket[0]>=bracket[1]: raise ValueError('求根区间须为递增有限数对')
                q=distribution.quantile(alpha,bracket); es=distribution.expected_shortfall(alpha,bracket)
            else:
                weighted=m.age_weights(df,p['decay']) if model=='age' else df
                weight='weight' if model=='age' else p['weight_column'] if model=='weighted' else None
                if weight:
                    w=_numbers(weighted,weight).iloc[:,0]
                    if (w<0).any() or w.sum()<=0: raise ValueError('概率权重须非负且总和为正')
                distribution=m.HistoricalDistribution(weighted,c,weight); q=distribution.quantile(alpha); es=distribution.expected_shortfall(alpha)
            interval=m.quantile_interval(df,c,alpha,p['interval_confidence'])
            value=pd.Series(dict(VaR=q,ES=es,unweighted_interval_lower=interval['lower'],unweighted_interval_upper=interval['upper']))
            notes+=['输入已经是损失，正值表示亏损。顺序统计区间针对原始等权样本，不是加权/KDE区间。']
        elif key=='scenarios':
            method=p['method']
            if method in ('volatility','filtered'):
                _numbers(df,[c,p['volatility_column']])
                if (df[p['volatility_column']]<=0).any(): raise ValueError('历史波动率须为正')
                value=m.volatility_scale(df,c,p['volatility_column'],p['forecast_volatility']) if method=='volatility' else m.filtered_scenarios(df,c,p['volatility_column'],p['forecast_volatility'],p['n_scenarios'],np.random.default_rng(p['seed']))
            else:
                cols=p['target_columns']; _numbers(df,cols)
                if method=='levels':
                    levels=np.asarray(p['current_levels'],dtype=float)
                    if levels.shape!=(len(cols),) or not np.isfinite(levels).all(): raise ValueError('当前水平数量须与因子列相同')
                    value=m.historical_scenarios(df,cols,pd.DataFrame([levels],columns=cols))
                else:
                    value=m.correlation_scale(df,cols,_matrix(p['historical_covariance'],len(cols),True),_matrix(p['forecast_covariance'],len(cols),True))
                    notes+=['相关调整要求输入已中心化；界面不会隐式减均值。']
        elif key=='garch':
            _numbers(df,c,3)
            args=np.asarray(p['initial_parameters'],dtype=float)
            if args.shape!=(5,) or not np.isfinite(args).all() or args[0]<=0 or min(args[1:3])<0 or args[1]+args[2]>=1: raise ValueError('GARCH参数须ω>0、αβ≥0、α+β<1')
            model=m.AsymmetricGARCH(*args)
            if p['method']=='fit':
                bounds=np.asarray(p['bounds'],dtype=float)
                if bounds.shape!=(5,2) or not np.isfinite(bounds).all() or (bounds[:,0]>=bounds[:,1]).any() or bounds[0,0]<=0 or (bounds[1:3,0]<0).any(): raise ValueError('拟合边界须为有效5×2数组，ω下界>0且αβ下界非负')
                model,fit=m.AsymmetricGARCH.fit(df,c,args,p['initial_variance'],bounds)
                if not fit.success: raise ValueError(f'GARCH拟合未收敛：{fit.message}')
            filtered=model.filter(df,c,p['initial_variance'])
            paths=model.filtered_paths(filtered,'standardized_residual',p['initial_variance'],p['horizon'],p['n_paths'],np.random.default_rng(p['seed']))
            output=_result(filtered,notes,[dict(name=k,value=getattr(model,k)) for k in ['omega','alpha','beta','gamma','mean']])
            path_result=_result(paths)
            path_result['tables'][0]['name']='过滤路径（每列一条路径）'
            output['tables']+=path_result['tables']; output['charts']+=path_result['charts']; return output
        else:
            _numbers(df,c,2)
            if p['block_size']>len(df): raise ValueError('区块长度不能超过样本数')
            estimator=lambda frame:frame[c].mean() if p['estimator']=='mean' else getattr(m.HistoricalDistribution(frame,c),'quantile' if p['estimator']=='var' else 'expected_shortfall')(alpha)
            value=m.bootstrap_estimates(df,estimator,p['n_resamples'],np.random.default_rng(p['seed']),p['block_size'])
            metrics=[dict(name='重采样标准误',value=value.estimate.std(ddof=1))]
    elif n==3:
        _numbers(df,c,5)
        if key=='gev':
            sample=df
            if p['sample_mode']=='raw':
                if p['block_column'] not in df or df[p['block_column']].isna().any(): raise ValueError('区块列缺失')
                sizes=df.groupby(p['block_column']).size()
                if (sizes!=p['block_size']).any(): raise ValueError('各区块行数须等于母分布区块大小')
                sample=m.block_maxima(df,c,p['block_column']); _numbers(sample,c,5)
            method=p['method']; args=np.asarray(p['initial_parameters'],dtype=float)
            if args.shape!=(3,) or not np.isfinite(args).all() or args[1]<=0: raise ValueError('GEV参数须为有限[位置,正尺度,尾指数]')
            if method=='specified': model=m.GeneralizedExtremeValue(*args)
            elif method=='quantile':
                bounds=np.asarray(p['bounds'],dtype=float)
                if bounds.shape!=(2,3) or not np.isfinite(bounds).all() or (bounds[0]>=bounds[1]).any() or bounds[0,1]<=0: raise ValueError('回归边界须为2×3且尺度下界为正')
                model,fit=m.GeneralizedExtremeValue.fit_quantile_regression(sample,c,args,bounds)
                if not fit.success: raise ValueError('GEV分位数回归未收敛')
            else:
                name={'mle':'fit','moments':'fit_gumbel_moments','regression':'fit_gumbel_regression'}[method]
                if sample[c].std()==0: raise ValueError('拟合需要非零样本方差')
                model=getattr(m.GeneralizedExtremeValue,name)(sample,c)
            if model.shape>=1: raise ValueError('拟合尾指数≥1，ES不存在')
            value=pd.Series(dict(location=model.location,scale=model.scale,shape=model.shape,block_VaR=model.quantile(alpha),parent_VaR=model.parent_quantile(alpha,p['block_size']),parent_ES=model.expected_shortfall(alpha,p['block_size'])))
        elif key=='pot':
            if p['method']=='specified': model=m.PeaksOverThreshold(p['threshold'],p['scale'],p['shape'],p['tail_probability'])
            else:
                excess=df.loc[df[c]>p['threshold'],c]-p['threshold']
                if len(excess)<5 or excess.var()==0: raise ValueError('阈值以上至少需要5个非恒定观测')
                model=getattr(m.PeaksOverThreshold,'fit' if p['method']=='mle' else 'fit_moments')(df,c,p['threshold'])
            if alpha<=1-model.tail_probability: raise ValueError('风险置信水平须落在阈值以上的尾部')
            if model.shape>=1 or model.scale<=0: raise ValueError('ES需要尾指数<1且尺度为正')
            value=pd.Series(dict(scale=model.scale,shape=model.shape,tail_probability=model.tail_probability,VaR=model.quantile(alpha),ES=model.expected_shortfall(alpha)))
        else:
            k=p['tail_count']
            if 4*k>len(df) or (df[c]<=0).any() or df[c].nunique()!=len(df): raise ValueError('Hill/Pickands需要正损失、无并列阶统计量且4k≤样本数')
            if alpha<=1-p['tail_probability']: raise ValueError('外推概率须位于阈值尾部')
            hill=m.hill_index(df,c,k); pick=m.pickands_index(df,c,k)
            value=pd.Series(dict(Hill=hill,Pickands=pick,extrapolated_VaR=m.tail_extrapolation(p['threshold'],p['tail_probability'],alpha,hill)))
    elif n==4:
        if key=='coverage':
            if p['input_mode']=='loss_var':
                _numbers(df,[c,p['var_column']],2); hits=m.exception_series(df,c,p['var_column']); hit='exception'
            else: hits=df;hit=p['hit_column'];_binary(hits,hit)
            model=m.CoverageBacktest(hits,hit,alpha)
            value=pd.DataFrame([model.unconditional(),model.independence(),model.conditional()],index=['unconditional','independence','conditional'])
            metrics=[dict(name='异常次数',value=int(hits[hit].sum())),dict(name='观测数',value=len(hits))]
        else:
            if p['exception_count']>p['sample_size']: raise ValueError('异常次数不能超过样本数')
            value=m.exception_count_probabilities(p['sample_size'],alpha,p['exception_count'])
            if p['sample_size']==250 and alpha==.99: value=pd.concat([value,m.traffic_light(p['exception_count'])])
            notes+=['交通灯只对250日/99%显示教材旧Basel规则，不表示当前监管要求。']
    elif n==5:
        if key=='linear':
            _numbers(df,[c,p['benchmark_column']]); model=m.LinearRiskMapping(df,c,_matrix(p['covariance'],len(df)))
            if model.var(alpha)==0: raise ValueError('成分VaR需要非零组合风险')
            value=model.components(alpha)
            metrics=[dict(name='VaR',value=model.var(alpha)),dict(name='tracking_VaR',value=model.tracking_var(df,p['benchmark_column'],alpha))]
        elif key=='cashflows':
            cols=[p[k] for k in ['cashflow_column','rate_column','maturity_column','duration_column']];_numbers(df,cols)
            if (1+df[p['rate_column']]/p['frequency']<=0).any() or (df[p['maturity_column']]<0).any() or p['upper_duration']<=p['lower_duration']: raise ValueError('折现基数须为正、期限非负且上久期大于下久期')
            value=m.cashflow_present_values(df,*cols[:3],p['frequency']);value=m.duration_map(value,'present_value',p['duration_column'],p['lower_duration'],p['upper_duration'])
            metrics=[dict(name='总现值',value=value.present_value.sum())]
        elif key=='derivatives':
            if p['instrument']=='forward': value=m.forward_exposures(*[p[k] for k in ['spot','strike','domestic_rate','foreign_rate','maturity','quantity']])
            elif p['instrument']=='fra': value=m.fra_value(*[p[k] for k in ['notional','forward_rate','contract_rate','accrual','payment_discount']])
            else:
                _numbers(df,p['accrual_column'])
                if (df[p['accrual_column']]<=0).any(): raise ValueError('计息年分数须为正')
                value=m.swap_cashflows(df,p['accrual_column'],p['notional'],p['contract_rate']);notes+=['互换重置日另有时点0浮息债价值+notional；结果表未来固定债现金流不含该项。']
        else: _numbers(df,c);value=m.delta_gamma_pnl(df,c,p['delta'],p['gamma'])
    elif n==6:
        if key=='sensitivity':
            _numbers(df,c)
            if len(df)>100: raise ValueError('逐参数差分最多100行')
            cov=_matrix(p['covariance'],len(df)); mapping=load_chapter(5)
            estimator=lambda frame:mapping.LinearRiskMapping(frame,c,cov).var(alpha)
            value=m.finite_difference_sensitivity(df,c,estimator(df),estimator,p['bump'])
            notes+=['当前估计器为第5章线性组合VaR；逐行扰动因子敞口，其余敞口和协方差固定。']
        elif key=='intervals':
            if p['rank']>p['sample_size'] or p['exceptions']>p['sample_size']: raise ValueError('阶数或异常次数不能超过样本数')
            if p['method']=='quantile': value=m.quantile_confidence_interval(p['estimate'],p['probability'],p['density'],p['sample_size'],p['interval_confidence'])
            elif p['method']=='order': value=m.order_probability_interval(p['sample_size'],p['rank'],p['interval_confidence'])
            else: value=m.exception_probability_interval(p['exceptions'],p['sample_size'],p['interval_confidence'])
        else:
            _numbers(df,[c,p['benchmark_column']])
            if (df[p['benchmark_column']]==0).any(): raise ValueError('基准不能为零')
            value=m.benchmark_comparison(df,c,p['benchmark_column'])
    else:
        _numbers(df,c,4)
        if key=='pit':
            if p['input_mode']=='normal':
                _numbers(df,[p['mean_column'],p['std_column']])
                if (df[p['std_column']]<=0).any(): raise ValueError('预测标准差须为正')
                frame=m.probability_integral_transform(df,c,lambda x,d:norm.cdf(x,loc=d[p['mean_column']],scale=d[p['std_column']]));target='pit'
            else: frame=df;target=c
            _pit(frame,target)
            output=_result(frame,notes)
            output['metrics']=[dict(name=str(k),value=_scalar(v)) for k,v in m.pit_diagnostics(frame,target).items()]
            return output
        method=p['method']
        if method=='ljung_box':
            if p['max_lag']>=len(df) or df[c].var()==0: raise ValueError('滞后须小于样本数且样本方差为正')
            value=m.ljung_box(df,c,p['max_lag'])
        elif method=='duration':
            _binary(df,c)
            durations=np.diff(np.flatnonzero(df[c].to_numpy()))
            if len(durations)<3 or np.var(durations)==0: raise ValueError('至少需要3个非恒定完整异常间隔')
            value=m.duration_test(df,c,p['exception_probability']);notes+=['持续期检验仅包含完整相邻异常间隔，首尾未完成区间不纳入。']
        else:
            predictors=p['predictor_columns'];_numbers(df,predictors)
            x=np.column_stack([np.ones(len(df)),df[predictors]])
            if len(df)<=x.shape[1] or np.linalg.matrix_rank(x)<x.shape[1]: raise ValueError('回归设计矩阵须满列秩且样本数大于参数数')
            if method=='pit_regression': _pit(df,c);value=m.pit_independence(df,c,predictors)
            else:
                _binary(df,c)
                if df[c].nunique()<2: raise ValueError('异常回归需要两种结果')
                value=getattr(m,'linear_probability_model' if method=='lpm' else 'exception_logit')(df,c,predictors)
            notes+=['预测变量应是调用方提前对齐的滞后/已知信息；不自动shift或使用未来预测。']
    return _result(value,notes,metrics)


def _binary(df,c):
    _numbers(df,c,2)
    if not df[c].isin([0,1]).all(): raise ValueError('异常指示列必须为0或1')


def _pit(df,c):
    _numbers(df,c,4)
    if ((df[c]<=0)|(df[c]>=1)).any(): raise ValueError('PIT须严格在(0,1)，不会自动裁剪端点')
