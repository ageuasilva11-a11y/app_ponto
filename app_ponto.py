from datetime import datetime
import gspread
import pandas as pd
import streamlit as st
from streamlit_geolocation import streamlit_geolocation

st.set_page_config(
    page_title="Ponto Eletrônico - Google Sheets",
    page_icon="📍",
    layout="centered",
)


def conectar_google_sheets():
  sec = dict(st.secrets["google_sheets"])

  # Normaliza a chave privada substituindo qualquer formato de quebra de linha corrompido
  if "private_key" in sec:
    pk = sec["private_key"]
    # Se vier com \\n literal, substitui por \n real
    pk = pk.replace("\\n", "\n")
    # Garante que as linhas de início e fim estejam corretas
    sec["private_key"] = pk

  gc = gspread.service_account_from_dict(sec)
  nome_planilha = st.secrets["google_sheets"].get(
      "planilha_nome", "Base Ponto Eletronico"
  )
  sheet = gc.open(nome_planilha)
  return sheet


def carregar_dados():
  try:
    sheet = conectar_google_sheets()
    worksheet = sheet.worksheet("Sheet1")
    dados = worksheet.get_all_records()
    df = pd.DataFrame(dados)

    if df.empty or "Nome" not in df.columns:
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

    if "Mês/Ano" not in df.columns or df["Mês/Ano"].isnull().all():
      if "Data" in df.columns:
        df["Mês/Ano"] = pd.to_datetime(
            df["Data"], format="%d/%m/%Y", errors="coerce"
        ).dt.strftime("%m/%Y")
      else:
        df["Mês/Ano"] = datetime.now().strftime("%m/%Y")
    return df
  except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
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
  try:
    sheet = conectar_google_sheets()
    worksheet = sheet.worksheet("Sheet1")
    agora = datetime.now()
    nova_linha = [
        nome,
        tipo,
        agora.strftime("%d/%m/%Y"),
        agora.strftime("%H:%M:%S"),
        agora.strftime("%m/%Y"),
        str(lat),
        str(lon),
        obs,
    ]
    worksheet.append_row(nova_linha)
    return True
  except Exception as e:
    st.error(f"Erro ao salvar registro na nuvem: {e}")
    return False


def carregar_assinaturas():
  try:
    sheet = conectar_google_sheets()
    worksheet = sheet.worksheet("Assinaturas")
    dados = worksheet.get_all_records()
    df = pd.DataFrame(dados)
    if df.empty:
      return pd.DataFrame(columns=["Nome", "Mês/Ano", "Data_Assinatura", "Status"])
    return df
  except Exception:
    return pd.DataFrame(columns=["Nome", "Mês/Ano", "Data_Assinatura", "Status"])


def salvar_assinatura(nome, mes_ano):
  try:
    sheet = conectar_google_sheets()
    worksheet = sheet.worksheet("Assinaturas")

    registros = worksheet.get_all_records()
    for i, reg in enumerate(registros):
      if reg.get("Nome") == nome and reg.get("Mês/Ano") == mes_ano:
        worksheet.delete_rows(i + 2)

    nova_linha = [
        nome,
        mes_ano,
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Assinado Digitalmente",
    ]
    worksheet.append_row(nova_linha)
    return True
  except Exception as e:
    st.error(f"Erro ao salvar assinatura: {e}")
    return False


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
      st.error("Por aguardar a captura do GPS antes de salvar.")
    else:
      sucesso = salvar_registro(
          nome_colaborador,
          tipo_ponto,
          loc.get("latitude"),
          loc.get("longitude"),
          observacao,
      )
      if sucesso:
        st.success(f"Ponto de **{nome_colaborador}** salvo com sucesso na nuvem!")

with aba2:
  st.title("📁 Espelho de Ponto Individual")
  df_registros = carregar_dados()
  df_ass = carregar_assinaturas()

  if not df_registros.empty and "Nome" in df_registros.columns:
    col_func, col_mes = st.columns(2)
    with col_func:
      funcionarios = sorted(df_registros["Nome"].dropna().unique().tolist())
      func_sel = st.selectbox("Selecione o Funcionário:", funcionarios)
    with col_mes:
      meses = sorted(df_registros["Mês/Ano"].dropna().unique().tolist())
      mes_sel = st.selectbox("Selecione o Mês:", meses)

    df_espelho = df_registros[
        (df_registros["Nome"] == func_sel)
        & (df_registros["Mês/Ano"] == mes_sel)
    ]

    st.markdown(f"### Espelho de Ponto: {func_sel} ({mes_sel})")

    if not df_espelho.empty:
      st.dataframe(df_espelho, use_container_width=True)

      ja_assinado = False
      if not df_ass.empty and "Nome" in df_ass.columns:
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
          if salvar_assinatura(func_sel, mes_sel):
            st.success("Espelho assinado e salvo no Google Sheets!")
            st.rerun()

      csv_bytes = df_espelho.to_csv(index=False, encoding="utf-8-sig").encode(
          "utf-8-sig"
      )
      st.download_button(
          label="📥 Baixar Cópia em CSV",
          data=csv_bytes,
          file_name=f"espelho_{func_sel}_{mes_sel}.csv".replace("/", "-"),
          mime="text/csv",
      )
    else:
      st.info(
          "Nenhum registro encontrado para este funcionário no mês selecionado."
      )
  else:
    st.info("Nenhum ponto registrado no sistema ainda.")
