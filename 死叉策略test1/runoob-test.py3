from kuanke.wizard import *
from jqdata import *
import numpy as np
import pandas as pd
import talib
import datetime

## 初始化函数，设定要操作的股票、基准等等
def initialize(context):
    # 设定基准
    set_benchmark('000300.XSHG')
    # 设定滑点
    set_slippage(FixedSlippage(0.02))
    # True为开启动态复权模式，使用真实价格交易
    set_option('use_real_price', True) 
    # 设定成交量比例
    set_option('order_volume_ratio', 1)
    # 股票类交易手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5), type='stock')
    # 个股最大持仓比重
    g.security_max_proportion = 1
    # 选股频率
    g.check_stocks_refresh_rate = 1
    # 买入频率
    g.buy_refresh_rate = 1
    # 卖出频率
    g.sell_refresh_rate = 1
    # 最大建仓数量
    g.max_hold_stocknum = 2

    # 选股频率计数器
    g.check_stocks_days = 0 
    # 买卖交易频率计数器
    g.buy_trade_days=0
    g.sell_trade_days=0 
    # 获取未卖出的股票
    g.open_sell_securities = [] 
    # 卖出股票的dict
    g.selled_security_list={}
    
    # 股票筛选初始化函数
    check_stocks_initialize()
    # 股票筛选排序初始化函数
    check_stocks_sort_initialize()
    # 出场初始化函数
    sell_initialize()
    # 入场初始化函数
    buy_initialize()
    # 风控初始化函数
    risk_management_initialize()

    # 关闭提示
    log.set_level('order', 'error')

    # 运行函数
    run_daily(sell_every_day,'open') #卖出未卖出成功的股票
    run_daily(risk_management, 'every_bar') #风险控制
    run_daily(check_stocks, 'open') #选股
    run_daily(trade, 'open') #交易  
    run_daily(selled_security_list_count, 'after_close') #卖出股票日期计数 
      

## 股票筛选初始化函数
def check_stocks_initialize():
    # 是否过滤停盘
    g.filter_paused = True
    # 是否过滤退市  
    g.filter_delisted = True
    # 是否只有ST
    g.only_st = False
    # 是否过滤ST
    g.filter_st = True
    # 股票池
    g.security_universe_index = ["000300.XSHG"]
    g.security_universe_user_securities = []
    # 行业列表
    g.industry_list = []
    # 概念列表
    g.concept_list = []

## 股票筛选排序初始化函数
def check_stocks_sort_initialize():
    # 总排序准则： desc-降序、asc-升序
    g.check_out_lists_ascending = 'asc'

## 出场初始化函数
def sell_initialize():
    # 设定是否卖出buy_lists中的股票
    g.sell_will_buy = True

    # 固定出仓的数量或者百分比
    g.sell_by_amount = None
    g.sell_by_percent = None

## 入场初始化函数
def buy_initialize():
    # 是否可重复买入
    g.filter_holded = True

    # 委托类型
    g.order_style_str = 'by_cap_mean'
    g.order_style_value = 100

## 风控初始化函数
def risk_management_initialize():
    # 策略风控信号
    g.risk_management_signal = True

    # 策略当日触发风控清仓信号
    g.daily_risk_management = True

    # 单只最大买入股数或金额
    g.max_buy_value = None
    g.max_buy_amount = None


## 卖出未卖出成功的股票
def sell_every_day(context):
    g.open_sell_securities = list(set(g.open_sell_securities))
    open_sell_securities = [s for s in context.portfolio.positions.keys() if s in g.open_sell_securities]
    if len(open_sell_securities)&gt;0:
        for stock in open_sell_securities:
            order_target_value(stock, 0)
    g.open_sell_securities = [s for s in g.open_sell_securities if s in context.portfolio.positions.keys()]
    return

## 风控
def risk_management(context):
    ### _风控函数筛选-开始 ###
    ### _风控函数筛选-结束 ###
    return

## 股票筛选
def check_stocks(context):
    if g.check_stocks_days%g.check_stocks_refresh_rate != 0:
        # 计数器加一
        g.check_stocks_days += 1
        return
    # 股票池赋值
    g.check_out_lists = get_security_universe(context, g.security_universe_index, g.security_universe_user_securities)
    # 行业过滤
    g.check_out_lists = industry_filter(context, g.check_out_lists, g.industry_list)
    # 概念过滤
    g.check_out_lists = concept_filter(context, g.check_out_lists, g.concept_list)
    # 过滤ST股票
    g.check_out_lists = st_filter(context, g.check_out_lists)
    # 过滤退市股票
    g.check_out_lists = delisted_filter(context, g.check_out_lists)
    # 财务筛选
    g.check_out_lists = financial_statements_filter(context, g.check_out_lists)
    # 行情筛选
    g.check_out_lists = situation_filter(context, g.check_out_lists)
    # 技术指标筛选
    g.check_out_lists = technical_indicators_filter(context, g.check_out_lists)
    # 形态指标筛选函数
    g.check_out_lists = pattern_recognition_filter(context, g.check_out_lists)
    # 其他筛选函数
    g.check_out_lists = other_func_filter(context, g.check_out_lists)

    # 排序
    input_dict = get_check_stocks_sort_input_dict()
    g.check_out_lists = check_stocks_sort(context,g.check_out_lists,input_dict,g.check_out_lists_ascending)

    # 计数器归一
    g.check_stocks_days = 1
    return

## 交易函数
def trade(context):
   # 初始化买入列表
    buy_lists = []

    # 买入股票筛选
    if g.buy_trade_days%g.buy_refresh_rate == 0:
        # 获取 buy_lists 列表
        buy_lists = g.check_out_lists
        # 过滤ST股票
        buy_lists = st_filter(context, buy_lists)
        # 过滤停牌股票
        buy_lists = paused_filter(context, buy_lists)
        # 过滤退市股票
        buy_lists = delisted_filter(context, buy_lists)
        # 过滤涨停股票
        buy_lists = high_limit_filter(context, buy_lists)

        ### _入场函数筛选-开始 ###
        buy_lists = [security for security in buy_lists if MA_judge_jincha(security, 5, 10)]
        ### _入场函数筛选-结束 ###

    # 卖出操作
    if g.sell_trade_days%g.sell_refresh_rate != 0:
        # 计数器加一
        g.sell_trade_days += 1
    else:
        # 卖出股票
        sell(context, buy_lists)
        # 计数器归一
        g.sell_trade_days = 1


    # 买入操作
    if g.buy_trade_days%g.buy_refresh_rate != 0:
        # 计数器加一
        g.buy_trade_days += 1
    else:
        # 卖出股票
        buy(context, buy_lists)
        # 计数器归一
        g.buy_trade_days = 1

## 卖出股票日期计数
def selled_security_list_count(context):
    g.daily_risk_management = True
    if len(g.selled_security_list)&gt;0:
        for stock in g.selled_security_list.keys():
            g.selled_security_list[stock] += 1

##################################  选股函数群 ##################################

## 财务指标筛选函数
def financial_statements_filter(context, security_list):
    ### _财务指标筛选函数-开始 ###
    ### _财务指标筛选函数-结束 ###

    # 返回列表
    return security_list

## 行情筛选函数
def situation_filter(context, security_list):
    ### _行情筛选函数-开始 ###
    ### _行情筛选函数-结束 ###

    # 返回列表
    return security_list

## 技术指标筛选函数
def technical_indicators_filter(context, security_list):
    ### _技术指标筛选函数-开始 ###
    security_list = [security for security in security_list if MA_judge_jincha(security, 5, 10)]
    ### _技术指标筛选函数-结束 ###

    # 返回列表
    return security_list

## 形态指标筛选函数
def pattern_recognition_filter(context, security_list):
    ### _形态指标筛选函数-开始 ###
    ### _形态指标筛选函数-结束 ###

    # 返回列表
    return security_list

## 其他方式筛选函数
def other_func_filter(context, security_list):
    ### _其他方式筛选函数-开始 ###
    ### _其他方式筛选函数-结束 ###

    # 返回列表
    return security_list

# 获取选股排序的 input_dict
def get_check_stocks_sort_input_dict():
    input_dict = {
        }
    # 返回结果
    return input_dict

##################################  交易函数群 ##################################
# 交易函数 - 出场
def sell(context, buy_lists):
    # 获取 sell_lists 列表
    init_sl = context.portfolio.positions.keys()
    sell_lists = context.portfolio.positions.keys()

    # 判断是否卖出buy_lists中的股票
    if not g.sell_will_buy:
        sell_lists = [security for security in sell_lists if security not in buy_lists]
    
    ### _出场函数筛选-开始 ###
    sell_lists = [security for security in sell_lists if MA_judge_sicha(security, 5, 10)]
    ### _出场函数筛选-结束 ###
    
    # 卖出股票
    if len(sell_lists)&gt;0:
        for stock in sell_lists:
            sell_by_amount_or_percent_or_none(context,stock, g.sell_by_amount, g.sell_by_percent, g.open_sell_securities)
    
    # 获取卖出的股票, 并加入到 g.selled_security_list中
    selled_security_list_dict(context,init_sl)
    
    return

# 交易函数 - 入场
def buy(context, buy_lists):
    # 风控信号判断
    if not g.risk_management_signal:
        return
    
    # 判断当日是否触发风控清仓止损
    if not g.daily_risk_management:
        return
    # 判断是否可重复买入
    buy_lists = holded_filter(context,buy_lists)
    
    # 获取最终的 buy_lists 列表
    Num = g.max_hold_stocknum - len(context.portfolio.positions)
    buy_lists = buy_lists[:Num]

    # 买入股票
    if len(buy_lists)&gt;0:
        # 分配资金
        result = order_style(context,buy_lists,g.max_hold_stocknum, g.order_style_str, g.order_style_value)
        for stock in buy_lists:
            if len(context.portfolio.positions) &lt; g.max_hold_stocknum:
                # 获取资金
                Cash = result[stock]
                # 判断个股最大持仓比重
                value = judge_security_max_proportion(context,stock,Cash,g.security_max_proportion)
                # 判断单只最大买入股数或金额
                amount = max_buy_value_or_amount(stock,value,g.max_buy_value,g.max_buy_amount)
                # 下单
                order(stock, amount, MarketOrderStyle())
    return

###################################  公用函数群 ##################################
## 排序
def check_stocks_sort(context,security_list,input_dict,ascending='desc'):
    if (len(security_list) == 0) or (len(input_dict) == 0):
        return security_list
    else:
        # 生成 key 的 list
        idk = list(input_dict.keys())
        # 生成矩阵
        a = pd.DataFrame()
        for i in idk:
            b = get_sort_dataframe(security_list, i, input_dict[i])
            a = pd.concat([a,b],axis = 1)
        # 生成 score 列
        a['score'] = a.sum(1,False)
        # 根据 score 排序
        if ascending == 'asc':# 升序
            a = a.sort(['score'],ascending = True)
        elif ascending == 'desc':# 降序