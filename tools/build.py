#!/usr/bin/env python3
"""遠任的走讀筆記：重建每一場的導覽與首頁。

用法（在 repo 根目錄）：
    python3 tools/build.py

資料來源：
- walks.json：所有場次（k 代號、d 日期、wd 星期、t 標題、o 活動、n 站數、p 照片數、s 一句話）
- walks/<k>/index.html：每一場的筆記頁（照片在 walks/<k>/img/）
- thumbs/<k>.jpg：首頁封面縮圖
- tools/home.tpl.html：首頁樣板

每一頁會先拿掉舊的導覽，再重新加上：
- 寬螢幕左側「全部走讀」清單：標題區固定在最上方、季節標籤固定在標題下方
- 窄螢幕頂部列＋「全部走讀 ▾」下拉
- 文末「較新的一場／較早的一場／回到全部走讀筆記」
新增一場：把頁面與照片放進 walks/<k>/、縮圖放 thumbs/<k>.jpg、在 walks.json 加一筆，再跑這支程式。
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC = "#2c6e63"
HOME = "../../index.html"


def season(d):
    y, m = int(d[:4]), int(d[5:7])
    if m <= 2:
        y -= 1
    n = "春" if 3 <= m <= 5 else "夏" if 6 <= m <= 8 else "秋" if 9 <= m <= 11 else "冬"
    return f"{y}–{(y + 1) % 100:02d} {n}" if n == "冬" else f"{y} {n}"


def strip_nav(s):
    """拿掉任何舊版本的導覽（artifact 時期或前一次建置留下的）。"""
    s = re.sub(r'<style>(?:(?!</style>).)*?\.yr-(?:top|head)\{.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<aside class="yr-side".*?</aside>', '', s, flags=re.S)
    s = re.sub(r'<script>try\{document\.querySelector\("\.yr-side.*?</script>', '', s, flags=re.S)
    s = re.sub(r'<script>\{const h=document\.querySelector\("\.yr-head"\).*?</script>', '', s, flags=re.S)
    s = re.sub(r'<div class="yr-top">.*?</details>(?:<span>[^<]*</span>)?</div>', '', s, flags=re.S)
    s = re.sub(r'<nav class="yr-pn".*?</nav>', '', s, flags=re.S)
    return s


CSS = (
    '<style>.yr-top{display:flex;align-items:center;gap:10px;padding:8px max(4vw,14px);'
    'background:#17262a;color:#e9efec;font:500 14px/1.4 "Noto Sans TC",system-ui,sans-serif;position:relative;z-index:8}'
    '.yr-top a{color:#fff;text-decoration:none;display:inline-flex;align-items:center;gap:6px;min-height:36px}'
    '.yr-top a:hover{text-decoration:underline}.yr-top span{margin-left:auto;opacity:.7;white-space:nowrap}'
    '.yr-side{display:none}.yr-se{font:700 12.5px/1 "Noto Sans TC",sans-serif;color:#9fd8ca;padding:14px 12px 6px 18px;letter-spacing:.05em;'
    'position:sticky;top:var(--yr-hh,0px);z-index:2;background:#17262a;margin:0 -6px}'
    '.yr-side,.yr-dd ul{font:14.5px/1.45 "Noto Sans TC",system-ui,sans-serif}'
    '.yr-side ul,.yr-dd ul{list-style:none;margin:0;padding:0}'
    '.yr-side li a,.yr-dd li a{display:block;padding:9px 12px;border-radius:8px;color:#dfe7e4;text-decoration:none}'
    '.yr-side li a:hover,.yr-dd li a:hover{background:rgba(255,255,255,.08)}'
    '.yr-side li a[aria-current],.yr-dd li a[aria-current]{background:#2c6e63;color:#fff}'
    '.yr-side small,.yr-dd small{display:block;font-size:12.5px;opacity:.7}'
    '.yr-head{position:sticky;top:0;z-index:3;background:#17262a;padding:18px 12px 6px;margin:0 -12px;border-bottom:1px solid rgba(255,255,255,.08)}'
    '@media(min-width:1180px){.yr-side{display:block;position:fixed;left:0;top:0;bottom:0;width:260px;z-index:6;overflow-y:auto;'
    'background:#17262a;color:#e9efec;padding:0 12px 30px}'
    '.yr-side .yr-home{display:block;color:#fff;text-decoration:none;font:800 19px/1.3 "Noto Serif TC",serif;padding:4px 12px 2px}'
    '.yr-side .yr-home:hover{text-decoration:underline}.yr-side p{margin:4px 12px 8px;font-size:13px;opacity:.65}'
    'body{margin-left:260px!important}.yr-top{display:none!important}}'
    '.yr-dd{position:static}.yr-dd summary{cursor:pointer;list-style:none;display:inline-flex;align-items:center;min-height:36px;'
    'padding:0 12px;border:1px solid rgba(255,255,255,.3);border-radius:999px;white-space:nowrap}'
    '.yr-dd summary::-webkit-details-marker{display:none}'
    '.yr-dd ul{position:absolute;left:max(4vw,14px);top:calc(100% - 2px);z-index:30;width:min(320px,calc(100vw - 28px));max-height:70vh;overflow-y:auto;'
    'background:#17262a;border-radius:10px;padding:6px;box-shadow:0 12px 30px rgba(0,0,0,.35)}'
    '.yr-dd .yr-se{top:-6px}'
    '.yr-pn{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;'
    'max-width:1040px;margin:10px auto 40px;padding:0 max(4vw,14px);font:15px/1.5 "Noto Sans TC",system-ui,sans-serif}'
    '.yr-pn a{display:block;padding:14px 16px;border:1px solid rgba(127,127,127,.35);border-radius:10px;'
    'color:inherit;text-decoration:none}.yr-pn a:hover{border-color:' + ACC + '}'
    '.yr-pn small{display:block;opacity:.65;font-size:13px}.yr-pn .nx{text-align:right}'
    '.yr-pn .home{text-align:center;grid-column:1/-1}'
    '@media(max-width:600px){.yr-pn{grid-template-columns:minmax(0,1fr)}.yr-pn .nx{text-align:left}}</style>')

JS = ('<script>{const h=document.querySelector(".yr-head"),a=document.querySelector(".yr-side");'
      'const f=()=>{if(h&&a)a.style.setProperty("--yr-hh",h.offsetHeight+"px")};f();addEventListener("resize",f);'
      'try{a.querySelector("[aria-current]").scrollIntoView({block:"center"})}catch(e){}}</script>')


def href(x):
    return f"../{x['k']}/index.html"


def nav_for(i, W):
    w = W[i]
    items, last = "", None
    for x in W:
        sk = season(x["d"])
        if sk != last:
            items += f'<li class="yr-se">{sk}</li>'
            last = sk
        cur = ' aria-current="page"' if x["k"] == w["k"] else ""
        items += (f'<li><a href="{href(x)}"{cur}><small>{x["d"].replace("-", "/")}</small>'
                  f'{html.escape(x["t"])}</a></li>')
    side = (f'<aside class="yr-side" aria-label="全部走讀"><div class="yr-head">'
            f'<a class="yr-home" href="{HOME}">‹ 遠任的走讀筆記</a><p>全部走讀・{len(W)} 場</p></div>'
            f'<ul>{items}</ul></aside>{JS}')
    top = (f'<div class="yr-top"><a href="{HOME}">‹ 遠任的走讀筆記</a>'
           f'<details class="yr-dd"><summary>全部走讀 ▾</summary><ul>{items}</ul></details>'
           f'<span>{w["d"].replace("-", "/")}</span></div>')
    prev = W[i - 1] if i > 0 else None
    nxt = W[i + 1] if i + 1 < len(W) else None
    pn = '<nav class="yr-pn" aria-label="其他走讀">'
    if prev:
        pn += (f'<a href="{href(prev)}"><small>‹ 較新的一場・{prev["d"].replace("-", "/")}</small>'
               f'{html.escape(prev["t"])}</a>')
    if nxt:
        pn += (f'<a class="nx" href="{href(nxt)}"><small>較早的一場・{nxt["d"].replace("-", "/")} ›</small>'
               f'{html.escape(nxt["t"])}</a>')
    pn += f'<a class="home" href="{HOME}">回到全部走讀筆記</a></nav>'
    return side, top, pn


def build_page(i, W):
    path = os.path.join(ROOT, "walks", W[i]["k"], "index.html")
    s = strip_nav(open(path, encoding="utf-8").read())
    side, top, pn = nav_for(i, W)
    s = s.replace("</head>", CSS + "</head>", 1)
    s = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + side + top, s, count=1)
    idx = s.rfind("</footer>")
    if idx != -1:
        idx += len("</footer>")
        s = s[:idx] + pn + s[idx:]
    else:
        s = s.replace("</body>", pn + "</body>")
    open(path, "w", encoding="utf-8").write(s)


def build_home(W):
    tpl = open(os.path.join(ROOT, "tools", "home.tpl.html"), encoding="utf-8").read()
    data = [dict(x, a="GH", u="") for x in W]
    tpl = tpl.replace("/*DATA*/[]", json.dumps(data, ensure_ascii=False))
    tpl = tpl.replace('/*HERE*/"A"', '"GH"').replace("/*URL*/{}", "{}")
    tpl = (tpl.replace("{{N}}", str(len(W)))
              .replace("{{STOPS}}", str(sum(x["n"] for x in W)))
              .replace("{{PH}}", str(sum(x["p"] for x in W))))
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(tpl)


def main():
    W = json.load(open(os.path.join(ROOT, "walks.json"), encoding="utf-8"))
    W.sort(key=lambda x: (x["d"], x["k"]), reverse=True)
    missing = [x["k"] for x in W if not os.path.exists(os.path.join(ROOT, "walks", x["k"], "index.html"))]
    if missing:
        sys.exit("walks.json 裡這些場次還沒有頁面：" + ", ".join(missing))
    for i in range(len(W)):
        build_page(i, W)
    build_home(W)
    print(f"ok：{len(W)} 場")


if __name__ == "__main__":
    main()
