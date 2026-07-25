"""validate_feed(OpenClaw 投递安全闸门)单测:签名/边界/拒收路径。

直接 python 运行;不触碰 feed/reports(只用临时文件)。
"""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import feed_lib as fl  # noqa: E402
from validate_feed import MAX_BYTES, check_one  # noqa: E402

PASS = 0


def ok(name, cond, extra=""):
    global PASS
    assert cond, f"FAIL: {name} {extra}"
    PASS += 1
    print(f"  ✓ {name}")


def mk_report(**over):
    r = {
        "schema_version": "1.0",
        "id": "openclaw-test-2026-06-10T06-deadbeef",
        "kind": "openclaw",
        "produced_at": "2026-06-10T06:00:00Z",
        "asof_data": "2026-06-10",
        "producer": {"name": "openclaw-agent:test"},
    }
    r.update(over)
    return r


def write_tmp(obj_or_text) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    f.write(obj_or_text if isinstance(obj_or_text, str) else json.dumps(obj_or_text, ensure_ascii=False))
    f.close()
    return f.name


SECRET = "test-secret-钥匙"

print("== 签名 ==")
r = fl.sign_report(mk_report(), SECRET)
ok("签名后字段齐全", r["signature"]["alg"] == "HMAC-SHA256" and len(r["signature"]["value"]) == 64)
ok("验签通过", fl.verify_signature(r, SECRET))
tampered = dict(r, asof_data="2026-06-09")
ok("篡改正文验签失败", not fl.verify_signature(tampered, SECRET))
ok("错密钥验签失败", not fl.verify_signature(r, "wrong"))
ok("无签名验签失败", not fl.verify_signature(mk_report(), SECRET))

print("== check_one 放行/拒收 ==")
good = write_tmp(fl.sign_report(mk_report(), SECRET))
passed, errs, rep = check_one(good, require_sig=False, secret=SECRET)
ok("合法签名投递放行", passed, str(errs))

unsigned = write_tmp(mk_report(id="openclaw-test-unsigned-cafebabe"))
passed, errs, _ = check_one(unsigned, require_sig=False, secret=SECRET)
ok("设密钥后 openclaw 无签名拒收", not passed and any("签名" in e for e in errs))

badsig = write_tmp(dict(fl.sign_report(mk_report(id="openclaw-test-badsig-cafebabe"), SECRET),
                        asof_data="2026-01-01"))
passed, errs, _ = check_one(badsig, require_sig=False, secret=SECRET)
ok("签名与正文不符拒收", not passed)

routine = write_tmp(fl.sign_report(mk_report(kind="routine", id="openclaw-test-routine-cafebabe"), SECRET))
passed, errs, _ = check_one(routine, require_sig=False, secret=SECRET)
ok("外部投递冒充 routine 拒收", not passed and any("routine" in e for e in errs))

fat = fl.sign_report(mk_report(id="openclaw-test-fatbook-cafebabe",
                               book={"positions": [{"symbol": f"S{i}", "weight": 0} for i in range(401)]}), SECRET)
passed, errs, _ = check_one(write_tmp(fat), require_sig=False, secret=SECRET)
ok("positions 超限拒收", not passed and any("positions" in e for e in errs))

broken = write_tmp("{not json")
passed, errs, _ = check_one(broken, require_sig=False, secret=None)
ok("非法 JSON 拒收", not passed and any("解析失败" in e for e in errs))

huge = write_tmp("[" + ",".join(["0"] * (MAX_BYTES // 2 + 8)) + "]")
passed, errs, _ = check_one(huge, require_sig=False, secret=None)
ok("超大文件拒收", not passed and any("过大" in e for e in errs))

print("== schema 必填 ==")
missing = mk_report()
missing.pop("asof_data")
passed, errs, _ = check_one(write_tmp(fl.sign_report(missing, SECRET)), require_sig=False, secret=SECRET)
ok("缺必填字段拒收", not passed, str(errs))

unexpected_property = write_tmp(
    fl.sign_report(
        mk_report(unexpected_top_level=True),
        SECRET,
    )
)
passed, errs, _ = check_one(unexpected_property, require_sig=False, secret=SECRET)
ok(
    "完整 JSON Schema 拒绝额外顶层字段",
    not passed and any("unexpected_top_level" in e for e in errs),
    str(errs),
)

print(f"\nvalidate_feed 全部通过:{PASS} 项")
