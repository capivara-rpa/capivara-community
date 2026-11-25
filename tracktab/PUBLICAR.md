# Publicar a TrackTab na Chrome Web Store (1 clique)

Assim que a extensão estiver publicada, qualquer usuário instala com **um clique**
— sem precisar baixar o repositório nem usar o "modo desenvolvedor".

## 1. Empacotar

```bash
bash packaging/build_tracktab.sh     # gera dist/tracktab.zip
```

O `.zip` já sai com o `manifest.json` na raiz (exigência da loja).

## 2. Criar a conta de desenvolvedor

1. Acesse <https://chrome.google.com/webstore/devconsole>.
2. Faça login com a conta Google que vai publicar.
3. Pague a taxa **única** de US$ 5 (válida para sempre, por conta).

## 3. Criar o item e enviar o zip

1. **New item** → arraste `dist/tracktab.zip`.
2. Preencha a listagem:
   - **Nome**: `TrackTab`
   - **Descrição curta**: `Gravador de elementos: capture XPath e dados com um clique.`
   - **Categoria**: `Developer Tools`
   - **Idioma**: Português (Brasil)
3. **Ícones**: use 128×128 (já está em `tracktab/icons/icon128.png`).
4. **Screenshots**: ao menos 1 imagem 1280×800 (capture a extensão em uso).

## 4. Privacidade e permissões (obrigatório)

A loja exige justificativa para cada permissão. Use algo como:

| Permissão | Motivo |
|---|---|
| `activeTab` / `scripting` | Ler os elementos da aba ativa quando o usuário clica em "Capturar". |
| `storage` | Guardar as capturas localmente no navegador. |
| `content_scripts` (all_urls) | Destacar o elemento sob o cursor durante a captura. |
| **Não coleta dados** | Marcar "This item does not collect user data": nada sai do navegador. |

Política de privacidade: pode ser um texto simples explicando que tudo é local
(hospede um `privacidade.html` no próprio repositório/GitHub Pages).

## 5. Enviar para revisão e publicar

1. **Submit for review**. A revisão costuma levar de algumas horas a poucos dias.
2. Aprovado → o item ganha uma URL pública:
   `https://chrome.google.com/webstore/detail/<ID>`
3. Coloque esse link no README do template (botão "Instalar TrackTab").

## 6. Atualizações

1. Suba a `version` em `tracktab/manifest.json` (ex.: `1.0.0` → `1.0.1`).
2. `bash packaging/build_tracktab.sh`.
3. **Package → Upload new package** e envie de novo.

> Dica: o workflow da CI também gera `tracktab.zip` como artefato a cada push,
> então o arquivo pronto para upload fica disponível nas *Actions*.
