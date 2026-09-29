from datetime import datetime
import os
import shutil
import pandas as pd
import streamlit as st
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(
    page_title="Ponto Eletrônico - Externa", page_icon="📍", layout="centered"
)

ARQUIVO_BANCO = "registros_ponto.csv"
ARQUIVO_ASSINATURAS = "assinaturas_ponto.csv"


def fazer_backup_diario():
  if os.path.exists(ARQUIVO_BANCO):
    hoje_str = datetime.now().strftime("%d-%m-%Y")
    pasta_backup = "backups_diarios"
    if not os.path.exists(pasta_backup):
      os.makedirs(pasta_backup)
    arquivo_backup = os.path.join(pasta_backup, f"ponto_{hoje_str}.csv")
    if not os.path.exists(arquivo_backup):
      try:
        shutil.copy(ARQUIVO_BANCO, arquivo_backup)
      except Exception:
        pass


def carregar_dados():
  fazer_backup_diario()
  if os.path.exists(ARQUIVO_BANCO):
    try:
      df = pd.read_csv(ARQUIVO_BANCO)
      if "Mês/Ano" not in df.columns:
        if "Data" in df.columns:
          df["Mês/Ano"] = pd.to_datetime(
              df["Data"], format="%d/%m/%Y", errors="coerce"
          ).dt.strftime("%m/%Y")
        else:
          df["Mês/Ano"] = datetime.now().strftime("%m/%Y")
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


def carregar_assinaturas():
  if os.path.exists(ARQUIVO_ASSINATURAS):
    try:
      return pd.read_csv(ARQUIVO_ASSINATURAS)
    except Exception:
      pass
  return pd.DataFrame(columns=["Nome", "Mês/Ano", "Data_Assinatura", "Status"])


def salvar_assinatura(nome, mes_ano):
  df_ass = carregar_assinaturas()
  # Remove assinatura anterior do mesmo mês se houver, para atualizar
  df_ass = df_ass[~((df_ass["Nome"] == nome) & (df_ass["Mês/Ano"] == mes_ano))]

  nova_ass = pd.DataFrame(
    [{
        "Nome": nome,
        "Mês/Ano": mes_ano,
        "Data_Assinatura": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Status": "Assinado Digitalmente",
    }]
  )
  df_ass = pd.concat([df_ass, nova_ass], ignore_index=True)
  df_ass.to_csv(ARQUIVO_ASSINATURAS, index=False)


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
  fazer_backup_diario()


# Abas na tela principal para separar o Bater Ponto do Espelho/Assinatura
aba1, aba2 = st.tabs(["📝 Registrar Ponto", "📁 Espelho de Ponto & Assinatura"])

with aba1:
  st.title("📍 Registro de Ponto à Distância")
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
        "Observação (Opcional):", placeholder="Ex: Canteiro de obras"
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
      salvar_registro(
          nome_colaborador,
          tipo_ponto,
          loc.get("latitude"),
          loc.get("longitude"),
          observacao,
      )
      st.success(f"Ponto de **{nome_colaborador}** salvo com sucesso!")

with aba2:
  st.title("📁 Espelho de Ponto Individual")
  df_registros = carregar_dados()
  df_ass = carregar_assinaturas()

  if not df_registros.empty:
    col_func, col_mes = st.columns(2)
    with col_func:
      funcionarios = sorted(df_registros["Nome"].dropna().unique().tolist())
      func_sel = st.selectbox("Selecione o Funcionário:", funcionarios)
    with col_mes:
      meses = sorted(df_registros["Mês/Ano"].dropna().unique().tolist())
      mes_sel = st.selectbox("Selecione o Mês:", meses)

    # Filtra os dados do funcionário no mês escolhido
    df_espelho = df_registros[
        (df_registros["Nome"] == func_sel)
        & (df_registros["Mês/Ano"] == mes_sel)
    ]

    st.markdown(f"### Espelho de Ponto: {func_sel} ({mes_sel})")

    if not df_espelho.empty:
      st.dataframe(df_espelho, use_container_width=True)

      # Verifica se já está assinado
      ja_assinado = not df_ass[
          (df_ass["Nome"] == func_sel) & (df_ass["Mês/Ano"] == mes_sel)
      ].empty

      if ja_assinado:
        dados_ass = df_ass[
            (df_ass["Nome"] == func_sel) & (df_ass["Mês/Ano"] == mes_sel)
        ].iloc[0]
        st.success(
            f"✅ **Espelho Assinado!** Validado por {func_sel} em"
            f" {dados_ass['Data_Assinatura']}."
        )
      else:
        st.warning(
            "⚠️ Este espelho de ponto ainda não foi assinado/validado para este"
            " mês."
        )
        if st.button(f"✍️ Assinar Espelho de Ponto de {mes_sel}"):
          salvar_assinatura(func_sel, mes_sel)
          st.success("Espelho assinado com sucesso! Atualizando...")
          st.rerun()

      # Botão de Download do relatório individual
      csv_ind = df_espelho.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Baixar Espelho em CSV",
          data=csv_ind,
          file_name=f"espelho_{func_sel}_{mes_sel}.csv".replace("/", "-"),
          mime="text/csv",
      )
    else:
      st.info(
          "Nenhum registro encontrado para este funcionário no mês selecionado."
      )
  else:
    st.info("Nenhum ponto registrado no sistema ainda.")
