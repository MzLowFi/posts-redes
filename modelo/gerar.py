"""Gera os slides do modelo fixo (1080x1080 PNG) a partir de um arquivo JSON.

Uso:
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 modelo/gerar.py conteudo.json pasta_saida

Formato do JSON:
{
  "serie": "IA NA PRÁTICA",            (opcional; selo no topo)
  "slides": [
    {"tipo": "capa",  "titulo": "Texto com *destaque* em azul", "subtitulo": "..."},
    {"tipo": "item",  "numero": 1, "titulo": "...", "texto": "...", "teste": "...", "rotulo_teste": "FAÇA O TESTE"},
    {"tipo": "frase", "titulo": "Frase de impacto com *destaque*", "subtitulo": "..."},
    {"tipo": "final", "titulo": "Frase de fechamento com *destaque*", "subtitulo": "..."}
  ]
}
Trechos entre *asteriscos* ficam em azul. "{handle}" no texto vira @eu.anderson.munhoz em azul.
Um post de imagem única é um JSON com um só slide ("capa" ou "frase").
"""
import asyncio, html, json, pathlib, re, sys
from playwright.async_api import async_playwright

HANDLE = "@eu.anderson.munhoz"

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1080px;height:1080px;background:#0B1730;font-family:'Inter',sans-serif;color:#F5F7FB;overflow:hidden;position:relative}
.grid{position:absolute;inset:0;background-image:radial-gradient(rgba(93,166,255,.18) 1.5px,transparent 1.5px);background-size:36px 36px;
 mask-image:linear-gradient(135deg,transparent 45%,#000 100%);-webkit-mask-image:linear-gradient(135deg,transparent 45%,#000 100%)}
.glow{position:absolute;width:620px;height:620px;right:-220px;top:-220px;border-radius:50%;background:radial-gradient(circle,rgba(93,166,255,.35),transparent 65%)}
.wrap{position:absolute;inset:80px 84px 70px 84px;display:flex;flex-direction:column}
.top{display:flex;justify-content:space-between;align-items:center;font-size:24px;font-weight:600;letter-spacing:.14em;color:#5DA6FF;min-height:52px}
.top .pill{border:2px solid rgba(93,166,255,.5);border-radius:999px;padding:10px 22px}
.top .count{color:rgba(245,247,251,.55);letter-spacing:.05em}
.main{flex:1;display:flex;flex-direction:column;justify-content:center}
.num{font-family:'Inter Display','Inter',sans-serif;font-weight:800;font-size:150px;line-height:1;color:#5DA6FF;margin-bottom:18px}
h1{font-family:'Inter Display','Inter',sans-serif;font-weight:800;letter-spacing:-.025em;line-height:1.02}
h1 em,.sub em{font-style:normal;color:#5DA6FF}
.sub{margin-top:36px;font-size:40px;line-height:1.3;color:rgba(245,247,251,.82);max-width:860px}
.sub b{color:#5DA6FF}
.box{margin-top:44px;border:2px solid rgba(93,166,255,.55);background:rgba(93,166,255,.08);border-radius:28px;padding:34px 40px;display:flex;gap:24px;align-items:flex-start}
.box .ic{flex:none;width:58px;height:58px;border-radius:14px;background:#5DA6FF;color:#0B1730;font-weight:800;font-size:34px;display:flex;align-items:center;justify-content:center}
.box .lb{font-size:22px;font-weight:700;letter-spacing:.12em;color:#5DA6FF;margin-bottom:8px}
.box .tx{font-size:36px;line-height:1.35;font-weight:600}
.foot{display:flex;justify-content:space-between;align-items:center;font-size:26px;color:rgba(245,247,251,.7)}
.foot .bar{flex:1;height:3px;background:linear-gradient(90deg,#5DA6FF,transparent);margin:0 28px}
.arrow{font-weight:700;color:#5DA6FF}
"""


def fmt(texto):
    t = html.escape(texto)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    return t.replace("{handle}", f"<b>{HANDLE}</b>").replace("\n", "<br>")


def tamanho_titulo(texto, base):
    n = len(texto)
    if n > 70:
        return base - 16
    if n > 50:
        return base - 6
    return base


def corpo(s):
    tipo = s.get("tipo", "capa")
    tit = s.get("titulo", "")
    sub = f'<p class="sub">{fmt(s["subtitulo"])}</p>' if s.get("subtitulo") else ""
    if tipo == "item":
        texto = f'<p class="sub">{fmt(s["texto"])}</p>' if s.get("texto") else ""
        box = ""
        if s.get("teste"):
            box = (f'<div class="box"><div class="ic">✓</div><div><div class="lb">{html.escape(s.get("rotulo_teste", "FAÇA O TESTE"))}</div>'
                   f'<div class="tx">{fmt(s["teste"])}</div></div></div>')
        return (f'<div class="num">{s["numero"]}.</div><h1 style="font-size:{tamanho_titulo(tit, 84)}px">{fmt(tit)}</h1>'
                f"{texto}{box}")
    base = 100 if tipo == "capa" else 96
    return f'<h1 style="font-size:{tamanho_titulo(tit, base)}px">{fmt(tit)}</h1>{sub}'


def pagina(s, idx, total, serie):
    ultimo = idx == total
    seta = "" if total == 1 else ('<span class="arrow">salve 📌</span>' if ultimo else '<span class="arrow">arraste →</span>')
    selo = f'<span class="pill">{html.escape(serie)}</span>' if serie else "<span></span>"
    cont = f'<span class="count">{idx}/{total}</span>' if total > 1 else "<span></span>"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body><div class="glow"></div><div class="grid"></div><div class="wrap">
<div class="top">{selo}{cont}</div>
<div class="main">{corpo(s)}</div>
<div class="foot"><span>{HANDLE}</span><span class="bar"></span>{seta}</div>
</div></body></html>"""


async def main(arquivo, saida):
    dados = json.loads(pathlib.Path(arquivo).read_text(encoding="utf-8"))
    slides = dados["slides"]
    serie = dados.get("serie", "")
    out = pathlib.Path(saida)
    out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1080, "height": 1080})
        for i, s in enumerate(slides, 1):
            await pg.set_content(pagina(s, i, len(slides), serie))
            await pg.wait_for_timeout(200)
            await pg.screenshot(path=str(out / f"slide_{i}.png"))
        await b.close()
    print("ok", sorted(x.name for x in out.glob("slide_*.png")))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
