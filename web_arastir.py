"""
import urllib.parse
INTERNET ARASTIRMA MOTORU
Takim verisi yetersizse: tum kaynaklardan bilgi toplar.
TheSportsDB + Wikipedia + OpenLigaDB + lig ortalamasi
"""
import urllib.request, json, ssl, time, re, os, threading

_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"}

# Onbellek (ayni takimi tekrar sormayalim)
CACHE_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "veri", "takim_web.json")
_kilit = threading.Lock()
_bellek = None
_son_kayit = 0.0


def _yukle_bellek():
    global _bellek
    if _bellek is not None:
        return _bellek
    try:
        with open(CACHE_DOSYA, encoding="utf-8") as f:
            _bellek = json.load(f)
    except Exception:
        _bellek = {}
    return _bellek


def _kaydet_bellek(zorla=False):
    """Onbellegi diske yaz (her cagride degil, seyrek)"""
    global _son_kayit
    if _bellek is None:
        return
    simdi = time.time()
    if not zorla and (simdi - _son_kayit) < 10:
        return          # 10 sn'de bir yaz (cok yazma = yavas)
    try:
        os.makedirs(os.path.dirname(CACHE_DOSYA), exist_ok=True)
        gecici = CACHE_DOSYA + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(_bellek, f, ensure_ascii=False)
        os.replace(gecici, CACHE_DOSYA)
        _son_kayit = simdi
    except Exception:
        pass


def _cek(url, timeout=10, ua=None):
    if ua is None:
        h = _UA
    elif ua == "":
        h = {}          # BOS User-Agent (ESPN boyle istiyor)
    else:
        h = {"User-Agent": ua}
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as r:
        return json.loads(r.read().decode("utf-8"))


# ═══════════════ 1) THESPORTSDB ═══════════════
def sportsdb_takim(ad):
    """Takimi bul + son maclarini al"""
    try:
        q = urllib.parse.quote(ad)
        d = _cek("https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t=" + q)
        ts = d.get("teams") or []
        if not ts:
            return None
        t = ts[0]
        tid = t.get("idTeam")
        sonuc = {
            "id": tid,
            "ad": t.get("strTeam"),
            "lig": t.get("strLeague"),
            "ulke": t.get("strCountry"),
            "stadyum": t.get("strStadium"),
            "kurulus": t.get("intFormedYear"),
            "logo": t.get("strTeamBadge"),
            "maclar": [],
        }
        # Son maclar
        try:
            d2 = _cek("https://www.thesportsdb.com/api/v1/json/3/eventslast.php?id=" + str(tid))
            for m in (d2.get("results") or []):
                ev, dep = m.get("strHomeTeam"), m.get("strAwayTeam")
                eg, dg = m.get("intHomeScore"), m.get("intAwayScore")
                if eg is None or dg is None:
                    continue
                try:
                    eg, dg = int(eg), int(dg)
                except Exception:
                    continue
                sonuc["maclar"].append({"ev": ev, "dep": dep, "ev_gol": eg, "dep_gol": dg,
                                        "tarih": m.get("dateEvent"), "lig": m.get("strLeague")})
        except Exception:
            pass
        # Sezon maclari (daha fazla gecmis)
        try:
            lig_id = t.get("idLeague")
            if lig_id:
                sezon = time.strftime("%Y") + "-" + str(int(time.strftime("%Y")) + 1)
                d3 = _cek("https://www.thesportsdb.com/api/v1/json/3/eventsseason.php?id=%s&s=%s" % (lig_id, sezon))
                for m in (d3.get("events") or []):
                    ev, dep = m.get("strHomeTeam"), m.get("strAwayTeam")
                    eg, dg = m.get("intHomeScore"), m.get("intAwayScore")
                    if eg is None or dg is None:
                        continue
                    try:
                        eg, dg = int(eg), int(dg)
                    except Exception:
                        continue
                    # Sadece bu takimin maclari
                    if (ev and ad.lower() in ev.lower()) or (dep and ad.lower() in dep.lower()):
                        sonuc["maclar"].append({"ev": ev, "dep": dep, "ev_gol": eg, "dep_gol": dg,
                                                "tarih": m.get("dateEvent"), "lig": m.get("strLeague")})
        except Exception:
            pass
        return sonuc
    except Exception:
        return None


# ═══════════════ 2) WIKIPEDIA ═══════════════
def wikipedia_takim(ad):
    """Wikipedia'dan takim bilgisi"""
    try:
        q = urllib.parse.quote(ad)
        # TR dene, sonra EN
        for dil in ("tr", "en"):
            try:
                url = ("https://%s.wikipedia.org/api/rest_v1/page/summary/%s" % (dil, q))
                d = _cek(url)
                ozet = d.get("extract") or ""
                if ozet:
                    return {"dil": dil, "baslik": d.get("title"), "ozet": ozet[:600]}
            except Exception:
                continue
        return None
    except Exception:
        return None


# ═══════════════ 3) OPENLIGADB (Almanya) ═══════════════
def openliga_takim(ad):
    try:
        for lig in ("bl1", "bl2", "bl3"):
            try:
                ts = _cek("https://api.openligadb.de/getavailableteams/%s/2026" % lig)
                for t in ts or []:
                    if ad.lower() in (t.get("teamName") or "").lower() or \
                       ad.lower() in (t.get("shortName") or "").lower():
                        return {"ad": t.get("teamName"), "lig": lig, "logo": t.get("teamIconUrl")}
            except Exception:
                continue
        return None
    except Exception:
        return None


# ═══════════════ ANA FONKSIYON ═══════════════
# ESPN lig kodlari (ulke -> lig eslestirmesi)
ESPN_LIGLER = {
    "ENGLAND": ["eng.1", "eng.2", "eng.3", "eng.4", "eng.fa", "eng.league_cup"],
    "SPAIN": ["esp.1", "esp.2"],
    "GERMANY": ["ger.1", "ger.2", "ger.3"],
    "ITALY": ["ita.1", "ita.2"],
    "FRANCE": ["fra.1", "fra.2"],
    "TURKEY": ["tur.1"],
    "BRAZIL": ["bra.1", "bra.2"],
    "ARGENTINA": ["arg.1", "arg.2"],
    "NETHERLANDS": ["ned.1"],
    "PORTUGAL": ["por.1"],
    "USA": ["usa.1", "usa.nwsl"],
    "MEXICO": ["mex.1"],
    "JAPAN": ["jpn.1"],
    "CHINA": ["chn.1"],
    "AUSTRALIA": ["aus.1"],
    "SCOTLAND": ["sco.1", "sco.2"],
    "BELGIUM": ["bel.1"],
    "RUSSIA": ["rus.1"],
    "WORLD": ["fifa.world", "uefa.champions", "uefa.europa", "concacaf.champions"],
}

# bellek: lig takim listesi (tekrar tekrar cekmeyelim)
_ESPN_TAKIM = {}
_ESPN_KILIT = threading.Lock()


def _espn_lig_takimlar(lig_kod):
    """ESPN lig takimlarini al (bellekli)"""
    with _ESPN_KILIT:
        if lig_kod in _ESPN_TAKIM:
            return _ESPN_TAKIM[lig_kod]
    try:
        d = _cek("https://site.web.api.espn.com/apis/site/v2/sports/soccer/%s/teams" % lig_kod, ua="")
        ts = d["sports"][0]["leagues"][0]["teams"]
        out = {}
        for t in ts:
            tt = t.get("team", {})
            ad = tt.get("displayName") or ""
            if ad:
                out[ad.lower()] = {"id": tt.get("id"), "ad": ad, "lig": lig_kod}
        with _ESPN_KILIT:
            _ESPN_TAKIM[lig_kod] = out
        return out
    except Exception:
        with _ESPN_KILIT:
            _ESPN_TAKIM[lig_kod] = {}
        return {}


def espn_takim(ad, ulke=None):
    """ESPN'den takimi bul + son maclarini al"""
    ad_t = (ad or "").lower().strip()
    if not ad_t:
        return None

    # Hangi liglerde arayacagiz?
    ligler = []
    if ulke and ulke.upper() in ESPN_LIGLER:
        ligler += ESPN_LIGLER[ulke.upper()]
    # Genel ligler
    for k in ("eng.1", "eng.2", "eng.3", "eng.4", "esp.1", "ger.1", "ita.1", "fra.1",
              "tur.1", "ned.1", "por.1", "sco.1", "bel.1"):
        if k not in ligler:
            ligler.append(k)

    for lg in ligler:
        takimlar = _espn_lig_takimlar(lg)
        # Tam veya kismi eslesme
        bulunan = None
        if ad_t in takimlar:
            bulunan = takimlar[ad_t]
        else:
            for k, v in takimlar.items():
                if ad_t in k or k in ad_t:
                    bulunan = v
                    break
        if not bulunan:
            continue
        # Maclari al
        maclar = []
        try:
            u = ("https://site.api.espn.com/apis/site/v2/sports/soccer/%s/teams/%s/schedule"
                 % (lg, bulunan["id"]))
            d2 = _cek(u, ua="")
            for m in (d2.get("events") or []):
                c = (m.get("competitions") or [{}])[0]
                cs = c.get("competitors") or []
                if len(cs) != 2:
                    continue
                # Skorlar
                skorlar = []
                for x in cs:
                    sc = x.get("score")
                    if isinstance(sc, dict):
                        sc = sc.get("displayValue") or sc.get("value")
                    skorlar.append(sc)
                if skorlar[0] is None or skorlar[1] is None:
                    continue
                try:
                    eg, dg = int(float(skorlar[0])), int(float(skorlar[1]))
                except Exception:
                    continue
                # Ev/deplasman
                ev = cs[0].get("team", {}).get("displayName") or ""
                dep = cs[1].get("team", {}).get("displayName") or ""
                # ESPN bazen ters verir, homeAway kontrol
                if cs[0].get("homeAway") == "away":
                    ev, dep = dep, ev
                    eg, dg = dg, eg
                maclar.append({"ev": ev, "dep": dep, "ev_gol": eg, "dep_gol": dg,
                               "tarih": (m.get("date") or "")[:10], "lig": lg})
        except Exception:
            pass
        if maclar:
            return {"ad": bulunan["ad"], "lig": lg, "maclar": maclar, "kaynak": "espn"}
    return None


def takim_arastir(ad, ulke=None, onbellek_kullan=True):
    """Tum kaynaklardan takim bilgisi topla"""
    ad_temiz = (ad or "").strip()
    if not ad_temiz:
        return None

    with _kilit:
        b = _yukle_bellek()
        if onbellek_kullan and ad_temiz in b:
            return b[ad_temiz]

    sonuc = {"ad": ad_temiz, "kaynaklar": [], "maclar": [], "bilgi": {}}

    # 0) ESPN (EN DEGERLI — alt ligler dahil!)
    try:
        es = espn_takim(ad_temiz, ulke)
    except Exception:
        es = None
    if es and es.get("maclar"):
        sonuc["kaynaklar"].append("espn")
        sonuc["bilgi"]["lig"] = es.get("lig")
        sonuc["bilgi"]["espn_ad"] = es.get("ad")
        sonuc["maclar"] += es["maclar"]

    # 1) TheSportsDB
    sd = sportsdb_takim(ad_temiz)
    if sd:
        sonuc["kaynaklar"].append("thesportsdb")
        if not sonuc["bilgi"].get("lig"):
            sonuc["bilgi"]["lig"] = sd.get("lig")
        sonuc["bilgi"]["ulke"] = sd.get("ulke")
        sonuc["bilgi"]["stadyum"] = sd.get("stadyum")
        sonuc["bilgi"]["kurulus"] = sd.get("kurulus")
        sonuc["bilgi"]["logo"] = sd.get("logo")
        sonuc["maclar"] += sd.get("maclar") or []

    # 2) Wikipedia
    wk = wikipedia_takim(ad_temiz)
    if wk:
        sonuc["kaynaklar"].append("wikipedia")
        sonuc["bilgi"]["ozet"] = wk.get("ozet")

    # 3) OpenLigaDB
    ol = openliga_takim(ad_temiz)
    if ol:
        sonuc["kaynaklar"].append("openligadb")
        if not sonuc["bilgi"].get("lig"):
            sonuc["bilgi"]["lig"] = ol.get("lig")

    # Maclari tekille
    gor = set()
    tekil = []
    for m in sonuc["maclar"]:
        k = (m.get("ev"), m.get("dep"), m.get("tarih"))
        if k in gor:
            continue
        gor.add(k)
        tekil.append(m)
    sonuc["maclar"] = tekil
    sonuc["mac_sayisi"] = len(tekil)

    # Guc hesabi icin ozet
    if tekil:
        atilan = sum(m["ev_gol"] if m["ev"].lower().startswith(ad_temiz.lower()[:4]) else m["dep_gol"] for m in tekil)
        yenilen = sum(m["dep_gol"] if m["ev"].lower().startswith(ad_temiz.lower()[:4]) else m["ev_gol"] for m in tekil)
        sonuc["bilgi"]["atilan"] = atilan
        sonuc["bilgi"]["yenilen"] = yenilen
        sonuc["bilgi"]["mac"] = len(tekil)

    with _kilit:
        b = _yukle_bellek()
        b[ad_temiz] = sonuc
        _kaydet_bellek()   # 10 sn'de bir yazar (hizli)

    return sonuc


if __name__ == "__main__":
    import urllib.parse
    for t in ["Galatasaray", "Mansfield", "MK Dons", "Bayern Munich", "Real Madrid"]:
        r = takim_arastir(t)
        if r:
            print("\n%s:" % t)
            print("   kaynaklar:", r["kaynaklar"])
            print("   mac sayisi:", r["mac_sayisi"])
            b = r["bilgi"]
            print("   lig:", b.get("lig"), "| ulke:", b.get("ulke"))
            if b.get("atilan") is not None:
                print("   atilan/yenilen:", b.get("atilan"), "/", b.get("yenilen"))
            for m in r["maclar"][:3]:
                print("     %s: %s %s-%s %s" % (m.get("tarih"), m["ev"][:18], m["ev_gol"], m["dep_gol"], m["dep"][:18]))
        else:
            print("\n%s: bulunamadi" % t)
