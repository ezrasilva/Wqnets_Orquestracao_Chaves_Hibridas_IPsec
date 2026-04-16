# Contributing

Este projeto tem foco academico e experimental. Contribuicoes devem priorizar clareza metodologica, rastreabilidade e reproducibilidade.

## 1. Regras gerais

- Nao introduzir mudancas que alterem protocolo experimental sem documentacao.
- Evitar alterar simultaneamente logica de coleta e logica de analise no mesmo PR sem justificativa.
- Preservar compatibilidade dos formatos CSV/JSON de saida.

## 2. Fluxo recomendado de contribuicao

1. Crie branch com nome descritivo.
2. Implemente alteracoes pequenas e coesas.
3. Atualize README e docs quando houver impacto metodologico.
4. Execute validacoes locais antes do PR.
5. Abra PR com descricao clara de impacto experimental.

## 3. Validacoes locais minimas

```bash
python3 - <<'PY'
import ast
import pathlib

for p in pathlib.Path('.').rglob('*.py'):
	if '.venv' in p.parts or '.git' in p.parts:
		continue
	ast.parse(p.read_text(encoding='utf-8'), filename=str(p))

print('Syntax OK')
PY
python3 scripts/validate_outputs.py
```

Se sua mudanca impacta experimento/analise, execute ao menos um cenario de smoke test e anexe evidencias no PR.

## 4. Convencoes de codificacao

- Python 3.10+
- Mensagens de log informativas e consistentes
- Argumentos CLI via argparse
- Nomes de arquivos de saida estaveis e autoexplicativos

## 5. O que incluir no PR

- Objetivo da mudanca
- Arquivos alterados
- Risco para comparabilidade com resultados anteriores
- Comandos executados localmente
- Evidencias (trechos de output, CSV/JSON gerado, ou figuras)
