# Caminho da Fé — base de dados automática

- `dados/base-ramal-principal.json`: lista de hospedagens gerada a partir do PDF oficial.
- `dados/fonte.json`: edição e endereço do PDF usado na última publicação.
- `.github/workflows/atualizar-base.yml`: rotina semanal (segunda, 06:00 de Brasília) que verifica o site da AACF.
- `scripts/`: download, validação. `pipeline/`: leitura do PDF.

Se a validação falhar, a base atual é mantida e uma issue é aberta para conferência.
