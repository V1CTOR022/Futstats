# ⚽ Fut Stats

**Impacto ofensivo dos jogadores na temporada 2025/2026**

Dashboard feito com **Streamlit**, **Pandas**, **Matplotlib** e **Seaborn** para analisar gols, assistências e impacto por partida dos jogadores das 5 principais ligas da Europa (Premier League, La Liga, Serie A, Bundesliga e Ligue 1).

---

## 🏆 Funcionalidades

- **Métricas personalizadas**
  - **Participação**: gols + assistências
  - **Impacto Ofensivo**: `Gols × 1.2 + Assistências`
  - **Impacto por Jogo**: impacto ofensivo dividido pelo número de partidas
- **Filtros** por liga, posição e número mínimo de jogos
- **Top 10** por impacto ofensivo e por impacto por jogo, com tabela e gráfico
- **Comparação** lado a lado entre dois jogadores
- Jogadores que trocaram de clube durante a temporada têm os números somados numa linha só

---

## 🚀 Como rodar

Precisa do Python 3.9 ou superior.

```bash
git clone https://github.com/V1CTOR022/FutStats.git
cd FutStats
pip install -r requirements.txt
streamlit run app.py
```

O dashboard abre sozinho no navegador.

---

## 📂 Estrutura

```
FutStats/
├── app.py                         # aplicação Streamlit
├── players_data-2025_2026.csv     # dados dos jogadores
└── requirements.txt               # dependências
```

---

## 🤝 Contribuindo

Sugestões e pull requests são bem-vindos. Abra uma issue se encontrar algum problema ou tiver uma ideia.

---

## 📄 Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE).

---

## 📬 Contato

Desenvolvido por **Victor Yuri**

LinkedIn: https://www.linkedin.com/in/victor-yuri-65147136a/
