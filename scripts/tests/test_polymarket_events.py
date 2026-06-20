"""polymarket_events 纯逻辑单测:相关性过滤 / 市场解析 / longshot 标记。不触网。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from polymarket_events import history_features, is_relevant, longshot_flag, parse_market  # noqa: E402

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


print("== is_relevant ==")
ok("Fed 降息相关", is_relevant("Will the Fed cut rates in March?"))
ok("衰退相关", is_relevant("US recession in 2026?"))
ok("BTC 相关", is_relevant("Will Bitcoin hit $150k in 2026?"))
ok("CPI 相关", is_relevant("Will CPI inflation be above 3%?"))
ok("体育被排除(即便含 'apple'?无)", not is_relevant("Will South Korea win the FIFA World Cup?"))
ok("无关被排除", not is_relevant("Will it rain in London tomorrow?"))
ok("体育排除优先于关键词", not is_relevant("Super Bowl: will the Eagles win?"))

print("== longshot_flag ==")
ok("0.95 是 longshot", longshot_flag(0.95))
ok("0.03 是 longshot", longshot_flag(0.03))
ok("0.6 不是", not longshot_flag(0.6))
ok("None 安全", not longshot_flag(None))

print("== parse_market ==")
m = {"question": "Will the Fed cut rates in March?",
     "outcomes": '["Yes", "No"]', "outcomePrices": '["0.72", "0.28"]',
     "volumeNum": 1500000, "liquidityNum": 50000, "endDate": "2026-03-20", "slug": "fed-cut-march"}
p = parse_market(m)
ok("取 Yes 概率=0.72", p["prob"] == 0.72, p["prob"])
ok("prob_pct=72.0", p["prob_pct"] == 72.0)
ok("outcome=Yes", p["outcome"] == "Yes")
ok("成交量解析", p["volume_usd"] == 1500000)
ok("非 longshot", p["longshot"] is False)

# 已是 list 形式(非 JSON 字符串)也支持
m2 = {"question": "BTC above $200k?", "outcomes": ["Yes", "No"], "outcomePrices": ["0.05", "0.95"],
      "volumeNum": 2000000}
p2 = parse_market(m2)
ok("list 形式解析 + longshot 标记", p2["prob"] == 0.05 and p2["longshot"] is True)

# 多元市场:取最高概率结果
m3 = {"question": "Which party wins? (affects S&P)", "outcomes": '["A","B","C"]',
      "outcomePrices": '["0.2","0.5","0.3"]', "volumeNum": 100}
p3 = parse_market(m3)
ok("多元取最高=B 0.5", p3["outcome"] == "B" and p3["prob"] == 0.5)

# 缺价格 → None
ok("缺 outcomePrices → None", parse_market({"question": "Fed?", "outcomes": '["Yes","No"]'}) is None)
ok("无 question → None", parse_market({"outcomes": '["Yes"]', "outcomePrices": '["1"]'}) is None)

# token_id 提取(用于拉历史)
mt = {"question": "Fed cut?", "outcomes": '["Yes","No"]', "outcomePrices": '["0.3","0.7"]',
      "volumeNum": 1, "clobTokenIds": '["tokYes","tokNo"]'}
ok("Yes 取对应 token", parse_market(mt)["token_id"] == "tokYes")

print("== history_features ==")
D = 86400
# 30 天:第0天 p=0.2 → 第30天 p=0.5;7 天前(第23天)假设 p=0.4
hist = [{"t": 1000000 + i * D, "p": 0.2 + 0.01 * i} for i in range(31)]  # 线性 0.2→0.5
hf = history_features(hist, days=(7, 30))
ok("30d 变化 = 末-首 = +0.30", abs(hf["prob_chg_30d"] - 0.30) < 1e-6, hf["prob_chg_30d"])
ok("7d 变化 ≈ +0.07", abs(hf["prob_chg_7d"] - 0.07) < 1e-6, hf["prob_chg_7d"])
ok("火花线最多 12 点", len(hf["spark"]) == 12)
ok("火花线末点=最新", abs(hf["spark"][-1] - 0.50) < 1e-6)
ok("点数不足 → 空 dict", history_features([{"t": 1, "p": 0.5}]) == {})
# 窗口不满 d 天 → 用最早点(诚实)
short = [{"t": 1000000, "p": 0.4}, {"t": 1000000 + 2 * D, "p": 0.6}]
ok("窗口不满用最早点(30d=+0.2)", abs(history_features(short, days=(30,))["prob_chg_30d"] - 0.2) < 1e-6)

print(f"\npolymarket_events 单测全过:{PASS} 断言")
