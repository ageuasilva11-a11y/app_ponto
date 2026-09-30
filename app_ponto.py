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


def salvar_registro(nome, tipo, data_str, hora_str, lat, lon, obs):
  try:
    sheet = conectar_google_sheets()
    worksheet = obter_ou_criar_worksheet(sheet, "Sheet1", COLUNAS_PONTO)

    # Extrai o mês/ano da data fornecida pelo dispositivo
    try:
      dt_obj = datetime.strptime(data_str, "%d/%m/%Y")
      mes_ano_str = dt_obj.strftime("%m/%Y")
    except Exception:
      mes_ano_str = datetime.now().strftime("%m/%Y")

    nova_linha = [
        nome,
        tipo,
        str(data_str),
        str(hora_str),
        str(mes_ano_str),
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


def salvar_assinatura(nome, mes_ano):
  try:
    sheet = conectar_google_sheets()
    worksheet = obter_ou_criar_worksheet(sheet, "Assinaturas", COLUNAS_ASSINATURA)

    registros = worksheet.get_all_records()
    for i, reg in enumerate(registros):
      if reg.get("Nome") == nome and reg.get("Mês/Ano") == mes_ano:
        worksheet.delete_rows(i + 2)

    agora = datetime.now()
    hora_atual = agora.strftime("%d/%m/%Y %H:%M:%S")

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

  # Instruções para o GPS
  st.markdown("---")
  st.subheader("1. Obter Localização GPS")
  loc = streamlit_geolocation()

  lat = loc.get("latitude") if loc else None
  lon = loc.get("longitude") if loc else None

  if lat and lon:
    st.success(f"GPS Capturado com sucesso! (Lat: {lat}, Lon: {lon})")
  else:
    st.warning(
        "⚠️ Aguardando permissão ou sinal de GPS. Por favor, permita o acesso à"
        " localização no seu dispositivo."
    )

  st.markdown("---")
  st.subheader("2. Dados do Ponto e Registo Automático")

  # Formulário interativo puro em HTML/JS executado no navegador do utilizador
  # Isso garante que a data e a hora recolhidas são EXATAMENTE as do telemóvel/computador dele, onde quer que ele esteja.
  form_html = """
    <form action="" method="get" style="font-family: sans-serif; background-color: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0;">
        <div style="margin-bottom: 15px;">
            <label style="font-weight: bold; color: #31333F; display: block; margin-bottom: 5px;">Nome do Funcionário:</label>
            <input type="text" id="input_nome" name="nome" placeholder="Ex: Ageu Silva" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box;" required>
        </div>
        
        <div style="margin-bottom: 15px;">
            <label style="font-weight: bold; color: #31333F; display: block; margin-bottom: 5px;">Tipo de Marcação:</label>
            <select id="select_tipo" name="tipo" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; background: white;">
                <option value="Entrada">Entrada</option>
                <option value="Início Almoço">Início Almoço</option>
                <option value="Fim Almoço">Fim Almoço</option>
                <option value="Saída">Saída</option>
                <option value="Visita Externa / Obra">Visita Externa / Obra</option>
            </select>
        </div>

        <div style="margin-bottom: 15px;">
            <label style="font-weight: bold; color: #31333F; display: block; margin-bottom: 5px;">Observação (Opcional):</label>
            <textarea id="input_obs" name="obs" placeholder="Ex: Canteiro de obras" style="width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; height: 80px;"></textarea>
        </div>

        <!-- Campos ocultos que capturam automaticamente a data e hora do dispositivo do utilizador -->
        <input type="hidden" id="hidden_data" name="data_dispositivo">
        <input type="hidden" id="hidden_hora" name="hora_dispositivo">

        <button type="submit" onclick="preencherHorario()" style="background-color: #ff4b4b; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-weight: bold; width: 100%;">
            ✅ Salvar Registro de Ponto
        </button>
    </form>

    <script>
    function preencherHorario() {
        const agora = new Date();
        
        // Formata a data DD/MM/YYYY baseada no fuso do dispositivo do utilizador
        const dia = String(agora.getDate()).padStart(2, '0');
        const mes = String(agora.getMonth() + 1).padStart(2, '0');
        const ano = agora.getFullYear();
        document.getElementById('hidden_data').value = dia + '/' + mes + '/' + ano;

        // Formata a hora HH:MM:SS baseada no fuso do dispositivo do utilizador
        const horas = String(agora.getHours()).padStart(2, '0');
        const minutos = String(agora.getMinutes()).padStart(2, '0');
        const segundos = String(agora.getSeconds()).padStart(2, '0');
        document.getElementById('hidden_hora').value = horas + ':' + minutos + ':' + segundos;
    }
    </script>
    """

  # Renderiza o formulário customizado
  import streamlit.components.v1 as components

  components.html(form_html, height=450)

  # Captura os parâmetros enviados pelo formulário HTML quando o utilizador clica em salvar
  params = st.query_params
  if "nome" in params and params["nome"]:
    nome_val = params["nome"]
    tipo_val = params.get("tipo", "Entrada")
    obs_val = params.get("obs", "")
    data_val = params.get("data_dispositivo", datetime.now().strftime("%d/%m/%Y"))
    hora_val = params.get("hora_dispositivo", datetime.now().strftime("%H:%M:%S"))

    if not lat or not lon:
      st.error(
          "⚠️ O GPS ainda não foi detetado acima. Aguarde o sinal verde de"
          " localização antes de submeter."
      )
    else:
      # Salva na planilha com os dados exatos recolhidos do telemóvel do funcionário
      sucesso = salvar_registro(
          nome_val, tipo_val, data_val, hora_val, lat, lon, obs_val
      )
      if sucesso:
        st.success(
            f"Ponto de **{nome_val}** registrado com sucesso às {hora_val} do"
            f" dia {data_val}!"
        )
        # Limpa os parâmetros da URL para evitar múltiplos envios ao atualizar a página
        st.query_params.clear()
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
