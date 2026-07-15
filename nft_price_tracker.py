#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Трекер флор-цен NFT-подарков (источник: Tonnel Network).
Каждые 5 часов опрашивает флор по каждому подарку и пишет nft_prices.json,
после чего (если задан GH_TOKEN) пушит файл в GitHub Pages-репозиторий,
чтобы миниаппа сразу видела свежие цены.

Запуск на хосте:
    GH_TOKEN=ghp_xxx  GH_REPO=funpayclient356-commits/mini-app  python3 nft_price_tracker.py

Без GH_TOKEN просто обновляет локальный nft_prices.json (можно раздавать своим веб-сервером).
"""
import os, json, time, subprocess, datetime, urllib.request, urllib.error

HERE      = os.path.dirname(os.path.abspath(__file__))
PRICES    = os.path.join(HERE, "nft_prices.json")
INTERVAL  = 5 * 60 * 60          # 5 часов
TONNEL_URL = "https://gifts2.tonnel.network/api/pageGifts"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO  = os.environ.get("GH_REPO", "funpayclient356-commits/mini-app")


def gift_names():
    """Берём список подарков из nft_prices.json (там уже все имена в seed)."""
    with open(PRICES, encoding="utf-8") as f:
        data = json.load(f)
    return list((data.get("prices") or {}).keys())


def tonnel_floor(name):
    """Флор в TON по имени подарка через Tonnel. Возвращает float или None."""
    body = {
        "page": 1, "limit": 1,
        "sort":  json.dumps({"price": 1}),                 # дешевле → дороже
        "filter": json.dumps({"gift_name": name, "asset": "TON", "status": "listed"}),
    }
    req = urllib.request.Request(
        TONNEL_URL, data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "user-agent": UA,
                 "origin": "https://tonnel.network", "referer": "https://tonnel.network/"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            arr = json.loads(r.read().decode())
        if isinstance(arr, list) and arr:
            return float(arr[0].get("price"))
    except Exception as e:
        print(f"  ! {name}: {e}")
    return None


def refresh():
    names = gift_names()
    print(f"[{datetime.datetime.utcnow():%Y-%m-%d %H:%M}] обновляю {len(names)} цен…")
    prices = {}
    ok = 0
    for n in names:
        floor = tonnel_floor(n)
        prices[n] = {"price_ton": floor if floor is not None else 0}
        if floor is not None:
            ok += 1
        time.sleep(0.7)   # мягкий троттлинг
    out = {
        "updated": datetime.datetime.utcnow().isoformat() + "Z",
        "source": "tonnel",
        "prices": prices,
    }
    with open(PRICES, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"  готово: {ok}/{len(names)} цен получено")
    push_to_github()


def push_to_github():
    if not GH_TOKEN:
        return
    url = f"https://{GH_TOKEN}@github.com/{GH_REPO}.git"
    try:
        subprocess.run(["git", "-C", HERE, "add", "nft_prices.json"], check=True)
        subprocess.run(["git", "-C", HERE, "commit", "-m", "update NFT floor prices"], check=False)
        subprocess.run(["git", "-C", HERE, "push", url, "HEAD"], check=False)
        print("  запушено в GitHub")
    except Exception as e:
        print(f"  push error: {e}")


if __name__ == "__main__":
    while True:
        try:
            refresh()
        except Exception as e:
            print("refresh error:", e)
        print(f"  следующее обновление через 5 ч")
        time.sleep(INTERVAL)
