# Landing page — Capivara 🦫

Página estática (HTML + CSS + JS puro, sem build) para publicar no cPanel da
Hostinger, no mesmo esquema das outras páginas do portfólio (ex.:
`/dashboards/vendas-bi/`).

```
landing/
├── capivara/               site publicado em /capivara/
│   ├── index.html
│   └── assets/
│       ├── styles.css      tokens de design (cores, raios, sombras) no topo
│       ├── app.js          tema claro/escuro, menu mobile, abas, copiar, animações
│       └── img/
│           ├── capivara.svg   mascote
│           ├── favicon.svg
│           └── cr_light.jpg · cr_dark.jpg · agenda.jpg   prints da Lagoa
└── apresentacao/           deck 16:9 (HTML/CSS + gerador PPTX)
```

## Publicar no cPanel

1. Compacte a pasta: `cd landing && zip -r capivara.zip capivara`
2. cPanel → **Gerenciador de Arquivos** → `public_html/`
3. **Carregar** o `capivara.zip` → botão direito → **Extract**
4. Acesse `https://arthurfaria.tech/capivara/index.html`
5. No construtor do site, adicione um item de menu/botão com o link
   `/capivara/index.html` (o construtor da Hostinger reserva `/capivara/` e
   redireciona para `/`).

> Quer embutir dentro de uma página do construtor? Use um bloco **Embed/HTML**
> com `<iframe src="/capivara/index.html" style="width:100%;height:100vh;border:0"></iframe>`.
> O link direto costuma ficar melhor (SEO, rolagem e prévia no WhatsApp).

## Apresentação

O deck fica em `landing/apresentacao/`:

```bash
# PDF via Chrome headless
chrome --headless --print-to-pdf=Capivara-Apresentacao.pdf \
  --no-pdf-header-footer --virtual-time-budget=8000 \
  file://$PWD/landing/apresentacao/index.html

# PPTX editável (precisa de python-pptx)
python landing/apresentacao/gerar_pptx.py
```

## Onde trocar o quê

| O quê | Onde |
|---|---|
| Número/texto do WhatsApp | `capivara/index.html` → links `wa.me/...` (plano Empresas e CTA final) |
| Link do repositório | `capivara/index.html` → `github.com/capivara-rpa/capivara` |
| Link da comunidade | `capivara/index.html` → `github.com/capivara-rpa/capivara-community` |
| Cores / raios / sombras | `capivara/assets/styles.css` → bloco `:root` e `[data-tema="escuro"]` |
| Mascote | substitua `capivara/assets/img/capivara.svg` pela ilustração oficial (mesmo nome) |
| Prints | regenere com a Lagoa em `?sem-sse&tema=light` / `tema=dark` |

Easter egg: clique 3× na capivara do topo. 🦆
