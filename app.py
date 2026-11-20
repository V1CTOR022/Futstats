from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

# O CSV fica na mesma pasta do app, assim roda em qualquer máquina
ARQUIVO_DADOS = Path(__file__).parent / "players_data-2025_2026.csv"

# Gol vale um pouco mais que assistência no cálculo do impacto
PESO_GOL = 1.2

POSICOES = {
    "GK": "Goleiro",
    "DF": "Defensor",
    "MF": "Meio-campista",
    "FW": "Atacante",
}

st.set_page_config(page_title="Fut Stats - Impacto Ofensivo", page_icon="⚽", layout="wide")
sns.set_theme(style="whitegrid")


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


def grafico_barras(dados, coluna, titulo):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(x=coluna, y="Player", data=dados, ax=ax, color="#2e7d32")
    ax.set_title(titulo)
    ax.set_xlabel("")
    ax.set_ylabel("")
    st.pyplot(fig)
    plt.close(fig)


df = carregar_dados()

st.title("⚽ Impacto Ofensivo dos Jogadores - 2025/2026")
st.caption(
    "Dados das 5 principais ligas da Europa. "
    f"Impacto Ofensivo = Gols × {PESO_GOL} + Assistências."
)


# =========================
# SIDEBAR
# =========================
st.sidebar.title("Filtros de Análise")

ligas = st.sidebar.multiselect(
    "Ligas:",
    options=sorted(df["Comp"].str.split(" / ").explode().unique()),
)

posicoes = st.sidebar.multiselect(
    "Posições:",
    options=list(POSICOES),
    default=["MF", "FW"],
    format_func=POSICOES.get,
    help="Jogadores com mais de uma posição (ex: MF,FW) entram em todas elas.",
)

min_jogos = st.sidebar.slider(
    "Mínimo de jogos:",
    min_value=1,
    max_value=int(df["MP"].max()),
    value=5,
    help="Evita que alguém com 1 jogo e 1 gol apareça no topo do impacto por jogo.",
)

df_filtrado = df[df["MP"] >= min_jogos]

if ligas:
    df_filtrado = df_filtrado[df_filtrado["Comp"].apply(lambda c: any(liga in c for liga in ligas))]

if posicoes:
    df_filtrado = df_filtrado[df_filtrado["Pos"].apply(lambda p: any(pos in p for pos in posicoes))]

if df_filtrado.empty:
    st.warning("Nenhum jogador encontrado com esses filtros.")
    st.stop()

st.sidebar.caption(f"{len(df_filtrado)} jogadores no filtro atual")


# =========================
# RANKING PRINCIPAL
# =========================
col1, col2 = st.columns(2)

with col1:
    st.subheader("Ranking por Impacto Ofensivo")

    top10 = df_filtrado.nlargest(10, "Impacto_Ofensivo")
    st.dataframe(
        top10[["Player", "Squad", "Pos", "Gls", "Ast", "Impacto_Ofensivo"]],
        hide_index=True,
    )
    grafico_barras(top10, "Impacto_Ofensivo", "Top 10 - Impacto Ofensivo")


# =========================
# IMPACTO POR JOGO
# =========================
with col2:
    st.subheader("Jogadores Mais Impactantes por Jogo")

    top_impacto = df_filtrado.nlargest(10, "Impacto_por_jogo")
    st.dataframe(
        top_impacto[["Player", "Squad", "MP", "Min", "Impacto_por_jogo"]],
        hide_index=True,
    )
    grafico_barras(top_impacto, "Impacto_por_jogo", "Top 10 - Impacto por Jogo")


# =========================
# COMPARAÇÃO
# =========================
st.divider()
st.subheader("Comparação de Jogadores")

jogadores = df_filtrado["Player"].tolist()

c1, c2 = st.columns(2)
j1 = c1.selectbox("Jogador 1", jogadores, index=0)
j2 = c2.selectbox("Jogador 2", jogadores, index=min(1, len(jogadores) - 1))

if j1 == j2:
    st.info("Escolha dois jogadores diferentes para comparar.")
else:
    comp = df_filtrado[df_filtrado["Player"].isin([j1, j2])].set_index("Player").loc[[j1, j2]]

    st.dataframe(comp[["Squad", "MP", "Gls", "Ast", "Impacto_Ofensivo", "Impacto_por_jogo"]])

    fig, ax = plt.subplots(figsize=(8, 4))
    comp[["Gls", "Ast", "Impacto_Ofensivo"]].T.plot(kind="bar", ax=ax, rot=0)
    ax.set_xticklabels(["Gols", "Assistências", "Impacto Ofensivo"])
    ax.legend(title="")
    st.pyplot(fig)
    plt.close(fig)


st.divider()
st.caption("Desenvolvido por Victor Yuri Vargas Koss")
