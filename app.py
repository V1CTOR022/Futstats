from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PASTA = Path(__file__).parent

# O CSV fica na mesma pasta do app, assim roda em qualquer máquina
ARQUIVO_DADOS = PASTA / "players_data-2025_2026.csv"
ARQUIVO_CSS = PASTA / "assets" / "style.css"

# Gol vale um pouco mais que assistência no cálculo do impacto
PESO_GOL = 1.2

POSICOES = {
    "GK": "Goleiro",
    "DF": "Defensor",
    "MF": "Meio-campista",
    "FW": "Atacante",
}

VERDE = "#22c55e"
AZUL = "#38bdf8"
TEXTO = "#e2e8f0"
TEXTO_FRACO = "#94a3b8"

st.set_page_config(page_title="Fut Stats - Impacto Ofensivo", page_icon="⚽", layout="wide")
st.markdown(f"<style>{ARQUIVO_CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# =========================
# CARREGAR DADOS
# =========================
@st.cache_data
def carregar_dados():
    df = pd.read_csv(ARQUIVO_DADOS)

    colunas = ["Player", "Born", "Pos", "Squad", "Comp", "MP", "Min", "Gls", "Ast"]
    df = df[colunas]

    # "eng Premier League" -> "Premier League"
    df["Comp"] = df["Comp"].str.split(" ", n=1).str[1]

    # Quem trocou de clube no meio da temporada aparece em mais de uma linha.
    # Junto tudo numa linha só pra contar a temporada inteira do jogador.
    # O ano de nascimento ajuda a não misturar jogadores com o mesmo nome.
    df = df.sort_values("Min", ascending=False)
    df = df.groupby(["Player", "Born"], dropna=False, as_index=False).agg(
        Pos=("Pos", "first"),
        Squad=("Squad", " / ".join),
        Comp=("Comp", lambda ligas: " / ".join(ligas.unique())),
        MP=("MP", "sum"),
        Min=("Min", "sum"),
        Gls=("Gls", "sum"),
        Ast=("Ast", "sum"),
    )
    df = df[df["MP"] > 0]

    # Os poucos homônimos que sobrarem ganham o clube no nome
    repetidos = df["Player"].duplicated(keep=False)
    df.loc[repetidos, "Player"] = df["Player"] + " (" + df["Squad"] + ")"

    # Métricas personalizadas
    df["Participacao"] = df["Gls"] + df["Ast"]
    df["Impacto_Ofensivo"] = (df["Gls"] * PESO_GOL + df["Ast"]).round(1)
    df["Impacto_por_jogo"] = (df["Impacto_Ofensivo"] / df["MP"]).round(2)

    return df.sort_values("Impacto_Ofensivo", ascending=False).reset_index(drop=True)


# =========================
# COMPONENTES VISUAIS
# =========================
def card_kpi(coluna, rotulo, valor, detalhe=""):
    coluna.markdown(
        f"""
        <div class="kpi">
            <div class="rotulo">{rotulo}</div>
            <div class="valor">{escape(str(valor))}</div>
            <div class="detalhe">{escape(detalhe)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def titulo_secao(titulo, subtitulo=""):
    st.markdown(
        f'<div class="secao">{titulo}</div><div class="secao-sub">{subtitulo}</div>',
        unsafe_allow_html=True,
    )


def estilo_grafico(grafico):
    return (
        grafico.configure(background="transparent")
        .configure_view(stroke=None)
        .configure_axis(
            grid=False,
            domain=False,
            ticks=False,
            labelColor=TEXTO,
            labelFontSize=13,
            labelFont="Inter",
            labelLimit=220,
            titleColor=TEXTO_FRACO,
        )
        .configure_legend(labelColor=TEXTO, labelFontSize=13, titleColor=TEXTO_FRACO)
    )


def grafico_ranking(dados, coluna, formato):
    base = alt.Chart(dados).encode(
        y=alt.Y("Player:N", sort="-x", title=None),
        # Folga no eixo pra caber o número no fim da maior barra
        x=alt.X(
            f"{coluna}:Q",
            title=None,
            axis=None,
            scale=alt.Scale(domain=[0, dados[coluna].max() * 1.15]),
        ),
    )

    barras = base.mark_bar(cornerRadiusEnd=6, height=22).encode(
        color=alt.Color(
            f"{coluna}:Q",
            scale=alt.Scale(range=["#166534", "#4ade80"]),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("Player:N", title="Jogador"),
            alt.Tooltip("Squad:N", title="Clube"),
            alt.Tooltip("Gls:Q", title="Gols"),
            alt.Tooltip("Ast:Q", title="Assistências"),
            alt.Tooltip("MP:Q", title="Jogos"),
            alt.Tooltip(f"{coluna}:Q", title="Valor", format=formato),
        ],
    )

    rotulos = base.mark_text(align="left", dx=8, color=TEXTO, fontWeight="bold").encode(
        text=alt.Text(f"{coluna}:Q", format=formato)
    )

    return estilo_grafico((barras + rotulos).properties(height=34 * len(dados)))


def grafico_comparacao(comp):
    metricas = {"Gls": "Gols", "Ast": "Assistências", "Impacto_Ofensivo": "Impacto Ofensivo"}

    dados = (
        comp[list(metricas)]
        .rename(columns=metricas)
        .reset_index()
        .melt(id_vars="Player", var_name="Métrica", value_name="Valor")
    )

    base = alt.Chart(dados).encode(
        x=alt.X("Métrica:N", title=None, sort=list(metricas.values()), axis=alt.Axis(labelAngle=0, labelPadding=12)),
        xOffset=alt.XOffset("Player:N", sort=list(comp.index)),
        y=alt.Y("Valor:Q", title=None, axis=None),
    )

    barras = base.mark_bar(cornerRadiusEnd=6, width=48).encode(
        color=alt.Color(
            "Player:N",
            sort=list(comp.index),
            scale=alt.Scale(range=[VERDE, AZUL]),
            legend=alt.Legend(title=None, orient="top"),
        ),
        tooltip=["Player:N", "Métrica:N", "Valor:Q"],
    )

    rotulos = base.mark_text(dy=-10, color=TEXTO, fontWeight="bold").encode(text="Valor:Q")

    return estilo_grafico((barras + rotulos).properties(height=340))


def card_jogador(coluna, nome, dados, rival, cor):
    stats = [
        ("Jogos", "MP", "{:.0f}"),
        ("Gols", "Gls", "{:.0f}"),
        ("Assist.", "Ast", "{:.0f}"),
        ("Minutos", "Min", "{:,.0f}"),
        ("Impacto", "Impacto_Ofensivo", "{:.1f}"),
        ("Por jogo", "Impacto_por_jogo", "{:.2f}"),
    ]

    blocos = ""
    for rotulo, campo, formato in stats:
        destaque = " melhor" if dados[campo] > rival[campo] else ""
        valor = formato.format(dados[campo]).replace(",", ".")
        blocos += f'<div class="stat{destaque}"><span>{rotulo}</span><b>{valor}</b></div>'

    posicao = " / ".join(POSICOES.get(p, p) for p in dados["Pos"].split(","))

    coluna.markdown(
        f"""
        <div class="jogador" style="--cor: {cor}">
            <div class="nome">{escape(nome)}</div>
            <div class="info">{escape(dados["Squad"])} · {escape(dados["Comp"])} · {posicao}</div>
            <div class="stats">{blocos}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


df = carregar_dados()


# =========================
# SIDEBAR
# =========================
st.sidebar.markdown('<div class="sidebar-logo">⚽ Fut<span>Stats</span></div>', unsafe_allow_html=True)

ligas = st.sidebar.multiselect(
    "Ligas",
    options=sorted(df["Comp"].str.split(" / ").explode().unique()),
    placeholder="Todas as ligas",
)

posicoes = st.sidebar.multiselect(
    "Posições",
    options=list(POSICOES),
    default=["MF", "FW"],
    format_func=POSICOES.get,
    placeholder="Todas as posições",
    help="Jogadores com mais de uma posição (ex: MF,FW) entram em todas elas.",
)

min_jogos = st.sidebar.slider(
    "Mínimo de jogos",
    min_value=1,
    max_value=int(df["MP"].max()),
    value=5,
    help="Evita que alguém com 1 jogo e 1 gol apareça no topo do impacto por jogo.",
)

tamanho_ranking = st.sidebar.slider("Jogadores no ranking", min_value=5, max_value=20, value=10)

df_filtrado = df[df["MP"] >= min_jogos]

if ligas:
    df_filtrado = df_filtrado[df_filtrado["Comp"].apply(lambda c: any(liga in c for liga in ligas))]

if posicoes:
    df_filtrado = df_filtrado[df_filtrado["Pos"].apply(lambda p: any(pos in p for pos in posicoes))]


# =========================
# CABEÇALHO
# =========================
st.markdown(
    f"""
    <div class="hero">
        <span class="temporada">Temporada 2025/2026</span>
        <h1>Impacto Ofensivo dos Jogadores</h1>
        <p>Gols e assistências nas 5 principais ligas da Europa ·
        Impacto Ofensivo = Gols × {PESO_GOL} + Assistências</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if df_filtrado.empty:
    st.warning("Nenhum jogador encontrado com esses filtros.")
    st.stop()

artilheiro = df_filtrado.loc[df_filtrado["Gls"].idxmax()]
garcom = df_filtrado.loc[df_filtrado["Ast"].idxmax()]

k1, k2, k3, k4 = st.columns(4)
card_kpi(k1, "Jogadores", f"{len(df_filtrado):,}".replace(",", "."), "no filtro atual")
card_kpi(k2, "Gols marcados", f"{int(df_filtrado['Gls'].sum()):,}".replace(",", "."),
         f"{int(df_filtrado['Ast'].sum()):,} assistências".replace(",", "."))
card_kpi(k3, "Artilheiro", artilheiro["Player"], f"{int(artilheiro['Gls'])} gols · {artilheiro['Squad']}")
card_kpi(k4, "Garçom", garcom["Player"], f"{int(garcom['Ast'])} assistências · {garcom['Squad']}")


aba_ranking, aba_por_jogo, aba_comparacao = st.tabs(
    ["🏆  Ranking", "⚡  Impacto por jogo", "⚔️  Comparação"]
)

colunas_tabela = {
    "Player": st.column_config.TextColumn("Jogador"),
    "Squad": st.column_config.TextColumn("Clube"),
    "Pos": st.column_config.TextColumn("Pos.", width="small"),
    "MP": st.column_config.NumberColumn("Jogos", width="small"),
    "Min": st.column_config.NumberColumn("Minutos", width="small"),
    "Gls": st.column_config.NumberColumn("Gols", width="small"),
    "Ast": st.column_config.NumberColumn("Assist.", width="small"),
}


# =========================
# RANKING PRINCIPAL
# =========================
with aba_ranking:
    top = df_filtrado.nlargest(tamanho_ranking, "Impacto_Ofensivo")

    titulo_secao(
        f"Top {tamanho_ranking} em Impacto Ofensivo",
        "Quem mais contribuiu com gols e assistências na temporada.",
    )

    col_grafico, col_tabela = st.columns([1, 1.25], gap="large")

    with col_grafico:
        st.altair_chart(grafico_ranking(top, "Impacto_Ofensivo", ".1f"), width="stretch", theme=None)

    with col_tabela:
        st.dataframe(
            top[["Player", "Squad", "Gls", "Ast", "Impacto_Ofensivo"]],
            hide_index=True,
            height=36 * (len(top) + 1),
            column_config={
                **colunas_tabela,
                "Impacto_Ofensivo": st.column_config.ProgressColumn(
                    "Impacto",
                    format="%.1f",
                    min_value=0,
                    max_value=float(top["Impacto_Ofensivo"].max()),
                ),
            },
        )


# =========================
# IMPACTO POR JOGO
# =========================
with aba_por_jogo:
    top_impacto = df_filtrado.nlargest(tamanho_ranking, "Impacto_por_jogo")

    titulo_secao(
        f"Top {tamanho_ranking} em Impacto por Jogo",
        f"Média de impacto por partida, considerando quem jogou pelo menos {min_jogos} jogos.",
    )

    col_grafico, col_tabela = st.columns([1, 1.25], gap="large")

    with col_grafico:
        st.altair_chart(grafico_ranking(top_impacto, "Impacto_por_jogo", ".2f"), width="stretch", theme=None)

    with col_tabela:
        st.dataframe(
            top_impacto[["Player", "Squad", "MP", "Min", "Impacto_por_jogo"]],
            hide_index=True,
            height=36 * (len(top_impacto) + 1),
            column_config={
                **colunas_tabela,
                "Impacto_por_jogo": st.column_config.ProgressColumn(
                    "Por jogo",
                    format="%.2f",
                    min_value=0,
                    max_value=float(top_impacto["Impacto_por_jogo"].max()),
                ),
            },
        )


# =========================
# COMPARAÇÃO
# =========================
with aba_comparacao:
    titulo_secao("Comparação de Jogadores", "Escolha dois jogadores para ver quem leva a melhor.")

    jogadores = df_filtrado["Player"].tolist()

    c1, c2 = st.columns(2, gap="large")
    j1 = c1.selectbox("Jogador 1", jogadores, index=0)
    j2 = c2.selectbox("Jogador 2", jogadores, index=min(1, len(jogadores) - 1))

    if j1 == j2:
        st.info("Escolha dois jogadores diferentes para comparar.")
    else:
        comp = df_filtrado.set_index("Player").loc[[j1, j2]]

        card_jogador(c1, j1, comp.loc[j1], comp.loc[j2], VERDE)
        card_jogador(c2, j2, comp.loc[j2], comp.loc[j1], AZUL)

        st.write("")
        st.altair_chart(grafico_comparacao(comp), width="stretch", theme=None)


st.markdown('<div class="rodape">Desenvolvido por Victor Yuri Vargas Koss</div>', unsafe_allow_html=True)
