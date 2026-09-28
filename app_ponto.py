from datetime import datetime
import os
import pandas as pd
import streamlit as st
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(
    page_title="Ponto Eletrônico - Externa", page_icon="📍", layout="centered"
)

ARQUIVO_BANCO = "registros_ponto.csv"


def carregar_dados():
  if os.path.exists(ARQUIVO_BANCO):
    try:
      df = pd.read_csv(ARQUIVO_BANCO)
      # Se a coluna antiga de data existe mas falta a coluna Mês/Ano, cria automaticamente
      if "Mês/Ano" not in df.columns:
        if "Data/Hora" in df.columns:
          # Tenta extrair o mês/ano da coluna antiga Data/Hora
          df["Mês/Ano"] = pd.to_datetime(
              df["Data/Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce"
          ).dt.strftime("%m/%Y")
        elif "Data" in df.columns:
          df["Mês/Ano"] = pd.to_datetime(
              df["Data"], format="%d/%m/%Y", errors="coerce"
          ).dt.strftime("%m/%Y")
        else:
          df["Mês/Ano"] = "09/2026"  # Padrão caso venha vazio
        df.to_csv(ARQUIVO_BANCO, index=False)
      return df
    except Exception:
      pass

  return pd.DataFrame(
    columns=[
        "Nome",
        "Tipo",
        "Data",
        "Hora",
        "Mês/Ano",
        "Latitude",
        "Longitude",
        "Observação",
    ]
  )


def salvar_registro(nome, tipo, lat, lon, obs):
  df = carregar_dados()
  agora = datetime.now()

  novo_registro = pd.DataFrame(
    [{
        "Nome": nome,
        "Tipo": tipo,
        "Data": agora.strftime("%d/%m/%Y"),
        "Hora": agora.strftime("%H:%M:%S"),
        "Mês/Ano": agora.strftime("%m/%Y"),
        "Latitude": str(lat),
        "Longitude": str(lon),
        "Observação": obs,
    }]
  )
  df = pd.concat([df, novo_registro], ignore_index=True)
  df.to_csv(ARQUIVO_BANCO, index=False)


st.title("📍 Registro de Ponto à Distância")
st.markdown("Registre seu ponto por funcionário com geolocalização.")

with st.form(key="form_ponto"):
  nome_colaborador = st.text_input(
      "Nome do Funcionário:", placeholder="Ex: Ageu Silva"
  )

  tipo_ponto = st.selectbox(
      "Tipo de Marcação:",
      [
          "Entrada",
          "Início Almoço",
          "Fim Almoço",
          "Saída",
          "Visita Externa / Obra",
      ],
  )

  observacao = st.text_area(
      "Observação (Opcional):", placeholder="Ex: Canteiro de obras / Obra 1288"
  )

  st.markdown("---")
  st.subheader("Localização GPS")
  loc = streamlit_geolocation()

  submit_button = st.form_submit_button(
      label="✅ Salvar Registro de Ponto", type="primary"
  )

if submit_button:
  if not nome_colaborador.strip():
    st.error("Por favor, preencha o nome do funcionário.")
  elif not loc or not loc.get("latitude") or not loc.get("longitude"):
    st.error("Por favor, aguarde a captura do GPS antes de salvar.")
  else:
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    salvar_registro(nome_colaborador, tipo_ponto, lat, lon, observacao)
    st.success(f"Ponto de **{nome_colaborador}** salvo com sucesso!")

st.markdown("---")

# --- PAINEL DO GESTOR COM FILTROS POR MÊS E FUNCIONÁRIO ---
st.subheader("📊 Painel de Registros e Relatórios")
df_registros = carregar_dados()

if not df_registros.empty and "Mês/Ano" in df_registros.columns:
  st.markdown("### Filtros de Busca")
  col_f1, col_f2 = st.columns(2)

  with col_f1:
    meses_disponiveis = ["Todos"] + sorted(
        df_registros["Mês/Ano"].dropna().unique().tolist()
    )
    mes_escolhido = st.selectbox("Filtrar por Mês/Ano:", meses_disponiveis)

  with col_f2:
    funcionarios_disponiveis = ["Todos"] + sorted(
        df_registros["Nome"].dropna().unique().tolist()
    )
    func_escolhido = st.selectbox(
        "Filtrar por Funcionário:", funcionarios_disponiveis
    )

  df_filtrado = df_registros.copy()
  if mes_escolhido != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Mês/Ano"] == mes_escolhido]
  if func_escolhido != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Nome"] == func_escolhido]

  st.dataframe(df_filtrado, use_container_width=True)

  csv = df_filtrado.to_csv(index=False).encode("utf-8")
  st.download_button(
      label="📥 Baixar Relatório Filtrado (CSV)",
      data=csv,
      file_name=(
          f"relatorio_ponto_{func_escolhido}_{mes_escolhido}.csv".replace(
              "/", "-"
          )
      ),
      mime="text/csv",
  )
else:
  st.info("Nenhum ponto registrado no arquivo ainda.")