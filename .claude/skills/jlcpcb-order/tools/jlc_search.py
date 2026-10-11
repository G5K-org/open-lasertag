"""jlc.py KEYWORD [n] - search JLCPCB assembly parts: code, model, package, basic/extended, stock, price"""
import json, sys, urllib.request
def search(kw, n=6):
    req = urllib.request.Request("https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList",
        data=json.dumps({"keyword": kw, "currentPage": 1, "pageSize": n}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return d["data"]["componentPageInfo"]["list"] or []
if __name__ == "__main__":
    for it in search(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 6):
        p = it.get("componentPrices") or [{}]
        print(f'{it["componentCode"]:10s} {it["componentModelEn"][:30]:30s} {it.get("componentSpecificationEn","")[:16]:16s} '
              f'{"BASIC" if it["componentLibraryType"]=="base" else "ext":5s} stock {it["stockCount"]:>8} ${p[0].get("productPrice","?")} | {it.get("describe","")[:60]}')
