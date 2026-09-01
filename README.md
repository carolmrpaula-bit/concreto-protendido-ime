# concreto-protendido-ime

Calculadora para as provas de **Concreto Protendido** (IME — Fortificação e
Construção). A resolução aparece passo a passo, na mesma ordem em que a conta é
feita à mão, para você conferir o que fez no papel.

**Site:** https://carolmrpaula-bit.github.io/concreto-protendido-ime/ — arquivo
único (`index.html`), roda no navegador e no celular, sem instalar nada.

**Script:** `protendido.py`, sem dependências, só a biblioteca padrão do Python 3.8+.

## O que a página resolve

| Aba | Pergunta | Prova |
|---|---|---|
| Pré-dimensionar à ruptura | quantos cabos a seção precisa | VC 2024, Q2 |
| Verificar à ruptura | a seção já armada aguenta? (itera até R_cc = R_st) | VC 2023, Q2 |
| Tensões em serviço | força mínima de protensão **ou** verificação dos limites | VC 2024 e 2023, Q3 |
| Deformação do aço | ε_pyd e tensão inicial admissível no cabo | Q1c das duas |

## Uso

```bash
python3 protendido.py          # roda os três exemplos da VC 2024
python3 protendido.py --q1     # deformação de escoamento
python3 protendido.py --q2     # pré-dimensionamento à ruptura
python3 protendido.py --q3     # força mínima de protensão
```

## Adaptando para outra prova

Só troque os dados de entrada:

```python
from protendido import DadosRuptura, pre_dimensionamento_ruptura, cg_real

d = DadosRuptura(
    fck=35,               # MPa
    aco="CP-190 RB",      # ver dicionário ACOS
    cordoalha="12.7",     # 9.5 | 12.7 | 15.2 (mm)
    n_cordoalhas=6,       # por cabo
    Mgk=1970, Mqk=1940,   # kN·m
    bf=250, h_laje=20,    # mesa, cm
    H_viga=180,           # cm
    cg_cabos=20,          # cm, medido do bordo inferior
    sistema="pos",        # "pos" ou "pre"
)
r = pre_dimensionamento_ruptura(d)
cg_real([(4, 8), (2, 20)])    # confira o CG depois de arredondar
```

```python
from protendido import DadosTensoes, forca_minima_protensao

d = DadosTensoes(fck=30, L=20, g=12, q=20,
                 A=0.401, Ws=0.1325, Wi=0.0993,
                 e=0.52,          # excentricidade, m (positiva abaixo do CG)
                 perdas=0.15,
                 trac_adm=0.0)    # MPa; use tracao_admissivel(fck, alpha) se permitir tração
forca_minima_protensao(d)
```

## O que cada rotina faz

| Função | Entrada | Saída |
|---|---|---|
| `eps_pyd(aco)` | tipo de aço | deformação de cálculo ao escoamento, ‰ |
| `sigma_p0_max(aco, sistema)` | aço, pré/pós-tração | tensão inicial admissível no cabo, MPa |
| `pre_dimensionamento_ruptura(d)` | seção, aço, momentos | nº de cabos, `M_d`, `z`, `R_st`, checagem da LN na mesa |
| `cg_real(camadas)` | `[(n_cabos, altura_cm), ...]` | CG efetivo, para conferir a iteração |
| `forca_minima_protensao(d)` | seção, cargas, excentricidade | `N` mínimo (kN) e as três verificações de tensão |
| `tracao_admissivel(fck, alpha)` | `f_ck`, forma da seção | `σ_t,adm` para protensão parcial |

## Convenções

- **Compressão positiva** nas rotinas de tensão.
- ELU: kN e cm. Tensões em serviço: MN, m e MPa.
- `σ_p0` pela NBR 6118 item 9.6.1.2.1 (RB: 0,74·f_ptk e 0,82·f_pyk na pós-tração;
  0,77·f_ptk e 0,85·f_pyk na pré-tração).
- `E_p = 200 GPa`. Algumas tabelas de fabricante usam 195 GPa para CP-190 RB —
  ajuste a constante `E_P` se o professor pedir.

## Limitações

- O pré-dimensionamento assume **linha neutra dentro da mesa**. A rotina avisa
  quando `R_cc > R_cc,adm`; nesse caso a seção precisa ser tratada como T real.
- Não calcula perdas de protensão (imediatas ou diferidas) — a perda entra como
  fração fornecida por você.
- A verificação à ruptura existe só na página, não no script Python.
- O diagrama σ×ε do aço é montado a partir de dois pontos que você informa
  (σ_p a 10 ‰ e a 15 ‰, com os valores da Tabela 14 de Cholfe como padrão para o
  CP-190 RB). Confira contra a tabela oficial antes de confiar no resultado.
- A escolha da combinação no ELS segue a Tabela 13.4 da NBR 6118: protensão
  completa verifica ELS-F na combinação rara e ELS-D na frequente; protensão
  limitada, ELS-F na frequente e ELS-D na quase permanente.

## Publicando no GitHub

```bash
cd concreto-protendido-ime
git init
git add .
git commit -m "Solver de concreto protendido - roteiros de prova"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/concreto-protendido-ime.git
git push -u origin main
```
