import json
import requests
import pandas as pd
import dropbox
import dropbox.files
import streamlit as st
from io import BytesIO

# Page config
st.set_page_config(
    page_title = "USA Data Dashboard",
    page_icon  = "📶",
)

# Reading CSS styles
with open("styles.css") as stl:
    st.markdown(f"<style>{stl.read()}</style>", 
                unsafe_allow_html=True)
   
# Reading Datamap
@st.cache_data
def load_datamap():
    datamap = pd.read_excel("datamap_1.xlsx", 
                            sheet_name = "Data Map")
    return datamap

@st.cache_data
def load_DBfile(file, sheet):

    # Accessing Dropbox files
    _, res = file
    data = res.content

    # Reading data frames
    with BytesIO(data) as file:
        df = pd.read_stata(file, convert_categoricals = False)

    return df

datamap  = load_datamap()

# Defining tools
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True
    
def retrieve_DBtoken(key, secret, refresh_token):
    data = {
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'client_id': key,
        'client_secret': secret,
    }
    response = requests.post('https://api.dropbox.com/oauth2/token', data = data)
    response_data = json.loads(response.text)
    access_token  = response_data["access_token"]
    return access_token

if check_password():

    # Defining auth secrets (when app is already deployed)
    dbtoken  = st.secrets["dbtoken"]
    dbkey    = st.secrets["dbkey"]
    dbsecret = st.secrets["dbsecret"]

    # Retrieving access token 
    atoken   = retrieve_DBtoken(dbkey, dbsecret, dbtoken)

    # Accessing Dropbox
    dbx = dropbox.Dropbox(atoken)

    # Loading data
    data = load_DBfile(dbx, "USA_data.dta", 0)

    st.markdown(
        """
        <h1 style='text-align: center;'>USA Data Dashboard</h1>
        
        <p class='jtext'>
        The <strong style="color:#003249">EU-S Copilot</strong> is a web app designed to assist Data Analysts 
        in their data-cleaning, harmonizing, and validation tasks for data collected from public opinion polls 
        and expert-coded questionnaires.
        </p>

        <p class='jtext'>
        Galingan!
        </p>
        """,
        unsafe_allow_html = True
    )

    topic = st.selectbox(
        "Please select a topic from the list below:",
        (datamap
        .drop_duplicates(subset = "topic")
        .topic.to_list())
    )
    indicator = st.selectbox(
        "Please select a question from the list below:",
        (datamap
        .loc[datamap["topic"] == topic]
        .question_text.to_list())
    )

    st.write(data)
