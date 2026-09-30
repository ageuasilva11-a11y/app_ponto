from datetime import datetime, timedelta
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
  if "private_key" in sec:
    sec["private_key"] = sec["private_key"].replace("\\n", "\n")
  gc = gspread.service_account_from_dict(sec)
  nome_planilha = st.secrets["google_sheets"].get(
      "planilha_nome", "Base Ponto Eletronico"
  )
  return gc.open(nome_planilha)


def obter_ou_criar_worksheet(sheet, nome_aba, colunas_padrao):
  try:
    return sheet.worksheet(nome_aba)
  except gspread.exceptions.WorksheetNotFound:
    ws = sheet.add_worksheet(title=nome_aba, rows=1000, cols=len(colunas_padrao))
    ws.append_row(colunas_padrao)
    return ws


COLUNAS_PONTO = [
    "Nome",
    "Tipo",
    "Data",
    "Hora",
    "Mês/Ano",
    "Latitude",
    "Longitude",
    "Observação",
]
COLUNAS_ASSINATURA = ["Nome", "Mês/Ano", "Data_Assinatura", "Status"]


def carregar_dados():
  try:
    sheet = conectar_google_sheets()
    worksheet = obter_ou_criar_worksheet(sheet, "Sheet1", COLUNAS_PONTO)
    dados = worksheet.get_all_records()
    df = pd.DataFrame(dados)

    if df.empty or "Nome" not in df.columns:
      return pd.DataFrame(columns=COLUNAS_PONTO)

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
    return pd.DataFrame(columns=COLUNAS_PONTO)


def calcular_horario_por_longitude(lon):
  """Calcula o fuso horário com base na longitude do GPS:

  - Longitude menor que -50 (Oeste do Brasil: Amazonas, Acre, etc.): UTC-4
  - Longitude maior ou igual a -50 (Leste/Nordeste/Sudeste: Ceará, SP, etc.):
  UTC-3
  """
  agora_utc = datetime.utcnow()
  if lon is not None and lon < -50.0:
    # Fuso Amazonas (UTC-4)
    agora_local = agora_utc - timedelta(hours=4)
  else:
    # Fuso Brasília / Ceará (UTC-3)
    agora_local = agora_utc - timedelta(hours=3)
  return agora_local


def salvar_registro(nome, tipo, lat, lon, obs):
  try:
    sheet = conectar_google_sheets()
    worksheet = obter_ou_criar_worksheet(sheet, "Sheet1", COLUNAS_PONTO)

    # Determina a hora exata com base na localização GPS do funcionário
    agora_local = calcular_horario_por_longitude(lon)
    d = agora_local.strftime("%d/%m/%Y")
    h = agora_local.strftime("%H:%M:%S")
    m = agora_local.strftime("%m/%Y")

    nova_linha = [
        nome,
        tipo,
        str(d),
        str(h),
        str(m),
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
    worksheet = obter_ou_criar_worksheet(sheet, "Assinaturas", COLUNAS_ASSINATURA)
    dados = worksheet.get_all_records()
    df = pd.DataFrame(dados)
    if df.empty:
      return pd.DataFrame(columns=COLUNAS_ASSINATURA)
    return df
  except Exception:
    return pd.DataFrame(columns=COLUNAS_ASSINATURA)


def salvar_assinatura(nome, mes_ano, lon):
  try:
    sheet = conectar_google_sheets()
    worksheet = obter_ou_criar_worksheet(sheet, "Assinaturas", COLUNAS_ASSINATURA)

    registros = worksheet.get_all_records()
    for i, reg in enumerate(registros):
      if reg.get("Nome") == nome and reg.get("Mês/Ano") == mes_ano:
        worksheet.delete_rows(i + 2)

    agora_local = calcular_horario_por_longitude(lon)
    hora_atual = agora_local.strftime("%d/%m/%Y %H:%M:%S")

    nova_linha = [
        nome,
        mes_ano,
        str(hora_atual),
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

  st.markdown("---")
  st.subheader("1. Obter Localização GPS (Necessário para validar o horário)")
  loc = streamlit_geolocation()

  lat = loc.get("latitude") if loc else None
  lon = loc.get("longitude") if loc else None

  if lat and lon:
    regiao = "Amazonas (Manaus)" if lon < -50.0 else "Ceará / Outros (UTC-3)"
    st.success(
        f"✅ GPS Capturado! Localização identificada: **{regiao}** (Lat:"
        f" {lat}, Lon: {lon})"
    )

    # Mostra o relógio em tempo real adaptado à região do GPS do telemóvel
    agora_visor = calcular_horario_por_longitude(lon)
    st.info(f"🕒 Horário ajustado para a sua região: {agora_visor.strftime('%d/%m/%Y - %H:%M:%S')}")
  else:
    st.warning(
        "⚠️ Por favor, permita o acesso à localização GPS no seu telemóvel"
        " para calcular o fuso horário correto."
    )

  st.markdown("---")
  st.subheader("2. Dados do Ponto")

  with st.form(key="form_ponto_nativo"):
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

    submit_button = st.form_submit_button(
        label="✅ Salvar Registro de Ponto", type="primary"
    )

  if submit_button:
    if not nome_colaborador.strip():
      st.error("Por favor, preencha o nome do funcionário.")
    elif not lat or not lon:
      st.error(
          "⚠️ Aguarde a captura do sinal de GPS antes de salvar o ponto para"
          " garantir a hora correta."
      )
    else:
      sucesso = salvar_registro(
          nome_colaborador, tipo_ponto, lat, lon, observacao
      )
      if sucesso:
        st.success(
            f"Ponto de **{nome_colaborador}** registrado com sucesso na"
            " planilha!"
        )
        st.rerun()

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
          # Usa a última longitude conhecida ou assume o padrão de Manaus se não tiver GPS recente
          if salvar_assinatura(func_sel, mes_sel, lon=-60.0):
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
