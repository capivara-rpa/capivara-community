# Política de segurança

## Como reportar

Não abra issue pública para vulnerabilidade. Envie um e-mail para
**capivara@arthurfaria.tech** com:

- descrição do problema;
- versão ou commit afetado;
- passos para reproduzir;
- impacto esperado;
- sugestão de correção, se tiver.

Você receberá uma confirmação de recebimento. O prazo de resposta é o possível
para um projeto comunitário; obrigado pela paciência.

## Escopo

Fazem parte do escopo:

- execução de código e injeção em fluxos, pacotes `.zip`, repositórios Git e
  agentes;
- autenticação, tokens de máquina, sessões e permissões da Control Room;
- cofre de credenciais, criptografia e exposição de segredos em logs;
- path traversal, upload/download de arquivos e endpoints HTTP;
- dependências e instaladores.

## Boas práticas

- Nunca publique tokens, senhas ou dados reais em issues, PRs ou exemplos.
- Use `.env` ou o cofre da Control Room para credenciais.
- Rode a Control Room em rede confiável ou com token/TLS quando exposta.
- Mantenha as dependências atualizadas.

Obrigado por ajudar a manter a Capivara segura.
