#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Concreto Protendido — resolvedor dos dois roteiros clássicos de prova.

  1) pre_dimensionamento_ruptura()  -> nº de cabos no ELU (Questão 2 da VC)
  2) forca_minima_protensao()       -> N mínimo por tensões em serviço (Questão 3)

Unidades: kN e cm nas rotinas do ELU; MN, m e MPa nas rotinas de tensões.
Cada função imprime o passo a passo e devolve um dicionário com os resultados,
para você conferir a conta feita à mão.

Uso:
    python3 protendido.py            # roda os dois exemplos da VC 2024
    python3 protendido.py --q2       # só o pré-dimensionamento
    python3 protendido.py --q3       # só as tensões
"""

from dataclasses import dataclass
from math import ceil
import sys

# --------------------------------------------------------------------------- #
# Catálogo de aços de protensão (relaxação baixa, RB)
# --------------------------------------------------------------------------- #

ACOS = {
    "CP-190 RB": {"fptk": 1900.0, "relaxacao": "RB"},
    "CP-210 RB": {"fptk": 2100.0, "relaxacao": "RB"},
    "CP-175 RB": {"fptk": 1750.0, "relaxacao": "RB"},
    "CP-190 RN": {"fptk": 1900.0, "relaxacao": "RN"},
}

E_P = 200_000.0  # MPa — módulo de elasticidade do aço de protensão (NBR 6118)

# Cordoalhas de 7 fios (área em cm²)
CORDOALHAS = {"9.5": 0.548, "12.7": 0.9867, "15.2": 1.400}


def fpyk(aco: str) -> float:
    """Tensão de escoamento característica. RB: 0,90 fptk; RN: 0,85 fptk."""
    d = ACOS[aco]
    return (0.90 if d["relaxacao"] == "RB" else 0.85) * d["fptk"]


def eps_pyd(aco: str, gamma_s: float = 1.15) -> float:
    """Deformação de cálculo ao escoamento, em ‰ (Questão 1c)."""
    return fpyk(aco) / gamma_s / E_P * 1000.0


def sigma_p0_max(aco: str, sistema: str = "pos") -> float:
    """
    Tensão inicial máxima no cabo, em MPa (NBR 6118, 9.6.1.2.1).
      pós-tração, RB: min(0,74 fptk ; 0,82 fpyk)
      pré-tração, RB: min(0,77 fptk ; 0,85 fpyk)
    """
    fpt = ACOS[aco]["fptk"]
    fpy = fpyk(aco)
    if sistema == "pos":
        c1, c2 = 0.74 * fpt, 0.82 * fpy
    else:
        c1, c2 = 0.77 * fpt, 0.85 * fpy
    return min(c1, c2)


# --------------------------------------------------------------------------- #
# QUESTÃO 2 — pré-dimensionamento à ruptura
# --------------------------------------------------------------------------- #

@dataclass
class DadosRuptura:
    fck: float            # MPa
    aco: str              # chave de ACOS
    cordoalha: str        # chave de CORDOALHAS
    n_cordoalhas: int     # por cabo
    Mgk: float            # kN·m
    Mqk: float            # kN·m
    bf: float             # cm  — largura da mesa
    h_laje: float         # cm  — altura da mesa
    H_viga: float         # cm  — altura da viga (sem a laje)
    cg_cabos: float       # cm  — do bordo inferior
    sistema: str = "pos"
    gamma_g: float = 1.35
    gamma_q: float = 1.50
    gamma_c: float = 1.40
    gamma_s: float = 1.15


def pre_dimensionamento_ruptura(d: DadosRuptura, verbose=True):
    p = (lambda *a: print(*a)) if verbose else (lambda *a: None)

    # 1) tensão inicial admissível no cabo
    sp0 = sigma_p0_max(d.aco, d.sistema) / 10.0            # MPa -> kN/cm²
    fpt = ACOS[d.aco]["fptk"] / 10.0
    fpy = fpyk(d.aco) / 10.0
    p("1) Tensao inicial no cabo (%s, %s-tracao)" % (d.aco, d.sistema))
    if d.sistema == "pos":
        p("   0,74 fptk = %.2f kN/cm2 | 0,82 fpyk = %.2f kN/cm2" % (0.74 * fpt, 0.82 * fpy))
    else:
        p("   0,77 fptk = %.2f kN/cm2 | 0,85 fpyk = %.2f kN/cm2" % (0.77 * fpt, 0.85 * fpy))
    p("   sigma_p0 = %.2f kN/cm2" % sp0)

    # 2) área do cabo
    A_cord = CORDOALHAS[d.cordoalha]
    A_cabo = d.n_cordoalhas * A_cord
    p("2) A_cabo = %d x %.4f = %.2f cm2" % (d.n_cordoalhas, A_cord, A_cabo))

    # 3) força inicial por cabo
    Np0 = sp0 * A_cabo
    p("3) N_p0 = %.2f x %.2f = %.1f kN por cabo" % (sp0, A_cabo, Np0))

    # 4) momento último
    Md = d.gamma_g * d.Mgk + d.gamma_q * d.Mqk
    p("4) M_d = %.2f x %.0f + %.2f x %.0f = %.0f kN.m"
      % (d.gamma_g, d.Mgk, d.gamma_q, d.Mqk, Md))

    # 5) braço de alavanca
    z = d.H_viga + d.h_laje / 2.0 - d.cg_cabos
    p("5) z = %.0f + %.0f/2 - %.0f = %.0f cm = %.3f m"
      % (d.H_viga, d.h_laje, d.cg_cabos, z, z / 100))

    # 6) resultante de compressão admissível (LN dentro da mesa)
    fcd = d.fck / d.gamma_c / 10.0                          # kN/cm²
    Rcc_adm = 0.85 * fcd * d.bf * d.h_laje
    p("6) f_cd = %.3f kN/cm2 ; R_cc,adm = 0,85 x %.3f x %.0f x %.0f = %.0f kN"
      % (fcd, fcd, d.bf, d.h_laje, Rcc_adm))

    # 7) resultantes de projeto
    Rst = Md / (z / 100.0)
    ok_mesa = Rst <= Rcc_adm
    p("7) R_cc = R_st = %.0f / %.3f = %.1f kN  -> %s"
      % (Md, z / 100, Rst, "OK, LN na mesa" if ok_mesa else "ATENCAO: LN fora da mesa!"))

    # 8) resistência de um cabo no ELU
    N1 = fpy * A_cabo / d.gamma_s
    p("8) N_1cabo = %.1f x %.2f / %.2f = %.1f kN" % (fpy, A_cabo, d.gamma_s, N1))

    # 9) número de cabos
    n_exato = Rst / N1
    n = ceil(n_exato)
    p("9) n = %.1f / %.1f = %.2f  ->  adotar %d cabos" % (Rst, N1, n_exato, n))
    p("   A_p,total = %.1f cm2 ; N_p0,total = %.0f kN" % (n * A_cabo, n * Np0))
    if not ok_mesa:
        p("   !! R_cc > R_cc,adm: refazer como secao T real, este resultado nao vale.")

    return {"sigma_p0": sp0, "A_cabo": A_cabo, "Np0_cabo": Np0, "Md": Md,
            "z_cm": z, "Rcc_adm": Rcc_adm, "Rst": Rst, "N1cabo": N1,
            "n_exato": n_exato, "n_cabos": n, "LN_na_mesa": ok_mesa}


def cg_real(camadas, verbose=True):
    """
    Confere o CG dos cabos depois de arredondar o nº de cabos.
    camadas = [(n_cabos, altura_cm), ...] medidas do bordo inferior.
    """
    tot = sum(n for n, _ in camadas)
    cg = sum(n * h for n, h in camadas) / tot
    if verbose:
        termos = " + ".join("%d x %g" % (n, h) for n, h in camadas)
        print("10) CG real = (%s) / %d = %.2f cm" % (termos, tot, cg))
    return cg


# --------------------------------------------------------------------------- #
# QUESTÃO 3 — tensões em serviço / força mínima de protensão
# --------------------------------------------------------------------------- #

@dataclass
class DadosTensoes:
    fck: float        # MPa
    L: float          # m   — vão
    g: float          # kN/m — carga permanente
    q: float          # kN/m — carga acidental
    A: float          # m²
    Ws: float         # m³  — módulo resistente da fibra superior
    Wi: float         # m³  — módulo resistente da fibra inferior
    e: float          # m   — excentricidade do cabo (positiva abaixo do CG)
    perdas: float = 0.15   # perdas diferidas (fração)
    trac_adm: float = 0.0  # tração admissível na fibra inferior, MPa (>= 0)


def forca_minima_protensao(d: DadosTensoes, verbose=True):
    """
    Convenção: COMPRESSÃO POSITIVA.
    Devolve a força inicial N (kN) necessária para que a fibra inferior,
    na combinação pp + carga móvel + protensão, não ultrapasse a tração admitida.
    """
    p = (lambda *a: print(*a)) if verbose else (lambda *a: None)

    # 1) momentos
    Mg = d.g * d.L ** 2 / 8.0
    Mq = d.q * d.L ** 2 / 8.0
    p("1) M_g = %.0f kN.m ; M_q = %.0f kN.m" % (Mg, Mq))

    # 2) e 3) tensões das cargas (MN.m / m3 = MPa)
    sg_s, sg_i = +Mg / 1000 / d.Ws, -Mg / 1000 / d.Wi
    sq_s, sq_i = +Mq / 1000 / d.Ws, -Mq / 1000 / d.Wi
    p("2) peso proprio : sigma_s = %+.2f MPa ; sigma_i = %+.2f MPa" % (sg_s, sg_i))
    p("3) carga movel  : sigma_s = %+.2f MPa ; sigma_i = %+.2f MPa" % (sq_s, sq_i))

    # 4) coeficientes da protensão (por MN de força)
    ks = 1 / d.A - d.e / d.Ws          # fibra superior
    ki = 1 / d.A + d.e / d.Wi          # fibra inferior
    p("4) protensao (por MN): sigma_s = %+.3f N ; sigma_i = %+.3f N" % (ks, ki))

    # 5) perdas
    eta = 1.0 - d.perdas
    ks_f, ki_f = ks * eta, ki * eta
    p("5) com %.0f%% de perdas: sigma_s = %+.3f N ; sigma_i = %+.3f N"
      % (d.perdas * 100, ks_f, ki_f))

    # 6) condição na fibra inferior
    deficit = -(sg_i + sq_i) - d.trac_adm      # MPa que a protensão precisa cobrir
    N = deficit / ki_f                          # MN (força inicial)
    p("6) %+.2f %+.2f %+.3f N >= %+.2f  ->  N = %.3f MN = %.0f kN"
      % (sg_i, sq_i, ki_f, -d.trac_adm, N, N * 1000))

    # verificações
    lim_comp = 0.5 * d.fck
    v1 = sg_s + ks_f * N                        # ato da protensão, fibra superior
    v2 = sg_s + sq_s + ks_f * N                 # serviço, fibra superior
    v3 = sg_i + ki_f * N                        # ato da protensão, fibra inferior
    p("\n   Verificacoes (limite de compressao 0,5 fck = %.1f MPa):" % lim_comp)
    p("   (1) topo, pp+protensao      : %+.2f MPa  %s" % (v1, "OK" if v1 >= 0 else "TRACIONA!"))
    p("   (2) topo, em servico        : %+.2f MPa  %s" % (v2, "OK" if v2 <= lim_comp else "EXCEDE!"))
    p("   (3) fundo, pp+protensao     : %+.2f MPa  %s" % (v3, "OK" if v3 <= lim_comp else "EXCEDE!"))

    return {"Mg": Mg, "Mq": Mq, "sig_g": (sg_s, sg_i), "sig_q": (sq_s, sq_i),
            "k_s": ks, "k_i": ki, "N_MN": N, "N_kN": N * 1000,
            "verif": {"topo_ato": v1, "topo_servico": v2, "fundo_ato": v3},
            "tudo_ok": v1 >= 0 and v2 <= lim_comp and v3 <= lim_comp}


def tracao_admissivel(fck, alpha=1.5):
    """
    sigma_t,adm = alpha * f_ct,inf, com f_ct,inf = 0,7 * 0,3 * fck^(2/3).
    alpha: 1,2 secao T | 1,3 duplo T | 1,5 retangular.
    """
    return alpha * 0.7 * 0.3 * fck ** (2 / 3)


# --------------------------------------------------------------------------- #
# Exemplos — VC 2024
# --------------------------------------------------------------------------- #

def exemplo_q2():
    print("=" * 68)
    print("QUESTAO 2 — pre-dimensionamento a ruptura (VC 2024)")
    print("=" * 68)
    d = DadosRuptura(fck=40, aco="CP-190 RB", cordoalha="12.7", n_cordoalhas=5,
                     Mgk=2000, Mqk=2000, bf=250, h_laje=20, H_viga=150,
                     cg_cabos=12)
    r = pre_dimensionamento_ruptura(d)
    cg = cg_real([(4, 8), (2, 20)])
    print("    CG adotado = %.0f cm -> %s"
          % (d.cg_cabos, "confere, nao precisa iterar" if abs(cg - d.cg_cabos) < 0.5
             else "diferente: refazer o passo 5 com z novo"))
    return r


def exemplo_q1c():
    print("=" * 68)
    print("QUESTAO 1c — deformacao de calculo ao escoamento")
    print("=" * 68)
    for aco in ("CP-190 RB", "CP-210 RB"):
        print("   %s: fpyk = %.0f MPa | fpyd = %.1f MPa | eps_pyd = %.2f por mil"
              % (aco, fpyk(aco), fpyk(aco) / 1.15, eps_pyd(aco)))


def exemplo_q3():
    print("=" * 68)
    print("QUESTAO 3 — forca minima de protensao (VC 2024)")
    print("=" * 68)
    d = DadosTensoes(fck=30, L=20, g=12, q=20, A=0.401, Ws=0.1325, Wi=0.0993,
                     e=0.63 - 0.11, perdas=0.15, trac_adm=0.0)
    r = forca_minima_protensao(d)
    print("\n   Se fosse permitida tracao (protensao parcial, secao retangular):")
    print("   sigma_t,adm = %.2f MPa" % tracao_admissivel(d.fck, 1.5))
    return r


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--q1" in args:
        exemplo_q1c()
    elif "--q2" in args:
        exemplo_q2()
    elif "--q3" in args:
        exemplo_q3()
    else:
        exemplo_q1c(); print()
        exemplo_q2(); print()
        exemplo_q3()
