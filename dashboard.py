import json
import requests
import numpy as np
import pandas as pd
import dropbox
import dropbox.files
import streamlit as st
from io import BytesIO
import plotly.express as px
from pandas.api.types import is_numeric_dtype

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

def normalize(group):
    return (group / group.sum())*100

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
    @st.cache_data
    def load_data():

        # Accessing Dropbox files
        _, res = dbx.files_download("/USA_data.dta")
        data = res.content

        # Reading data frames
        with BytesIO(data) as file:
            df = pd.read_stata(file, convert_categoricals = True)

        return df
    
    data = load_data()
    data["year"] = pd.to_numeric(data["year"], downcast='integer')

    # Instructions and filters/parameters
    st.markdown(
        """
        <h1 style='text-align: center;'>USA Data Dashboard</h1>
        """,
        unsafe_allow_html = True
    )
    topic = st.selectbox(
        "Please select a topic from the list below:",
        (datamap
        .drop_duplicates(subset = "topic")
        .topic.to_list())
    )
    question = st.selectbox(
        "Please select a question from the list below:",
        (datamap
        .loc[datamap["topic"] == topic]
        .question_text.to_list())
    )
    years = st.multiselect(
        "Please select the years for which you want to delimit your results:",
        (data
        .drop_duplicates(subset = "year")
        .year.to_list()),
        default = [2024]
    )
    paff = st.toggle(
        "Do you want to disaggregate results by Political Affiliation?",
        value = False
    )
    dkna = st.toggle(
        "Do you want to exclude DK/NAs from the final counts?",
        value = True
    )
    target = datamap.loc[datamap["question_text"] == question, "variable"].iloc[0]

    # Subsetting data as requested
    if paff:
        data = (
            data.copy()
            .loc[data["political_aff"] != ""]
        )
    if dkna:
        data = (
            data.copy()
            .loc[data[target] != "Don't know/No answer"]
            .loc[data[target] != "Don't Know/No Answer"]
            .loc[data[target] != "Prefer not to say"]
            .loc[data[target] != "No answer"]
            .loc[data[target] != "Don't know"]
            .loc[data[target] != 99]
            .loc[data[target] != 98]
        )
    if years:
        subset = (
            data.copy()
            .loc[data["year"].isin(years)]
        )
    else :
        subset = data.copy()

    # Table of results
    if paff:
        response = pd.crosstab(
            index     = [subset["political_aff"], subset[target]], 
            columns   = subset["year"], 
            # normalize = "all"
        )
        response[years] = response.groupby("political_aff")[years].transform(normalize)
        response = response.round(1)
        response.index = response.index.set_names(["Political Affiliation", "Answer"])
        response = response.reset_index()

    else:
        response = pd.crosstab(
            index     = subset[target], 
            columns   = subset["year"], 
            normalize = True
        ) * 100
        response = response.round(1)
        response.index = response.index.set_names(["Answer"])
        response = response.reset_index()
    
    if is_numeric_dtype(response.Answer):
        response["Answer"] = response["Answer"].astype(int).astype(str)

    reportV = datamap.loc[datamap["variable"] == target].encoding.iloc[0]
    st.markdown("----")
    st.markdown(
        f"""
        <p class='jtext'>
            You have selected to visualize the data for the following question:
        </p>
        <p class='jtext'>
            <i>{question}</i>
        </p>
        <p class='jtext'>
            The final counts for this question are shown in the table below. Please notice that
            the numbers represent the percentage of respondents that marked each specific answer
            during the online poll. You will also find a Chart, feel free to hoover to get more 
            information.
        </p>
        <p class='jtext'>
            Final data was received on June 21st, therefore, <b> some of the new questions still DO NOT HAVE 
            labels</b> in the data base. You can check their respective encodings in the expander tab below:
        </p>
        """, 
        unsafe_allow_html=True
    )
    with st.expander("Answer encodings"):
            st.markdown(
                f"""
                <p class='jtext'>
                    The encoded value labels for the selected question are defined as follow:
                </p>
                <p class='jtext'>
                    {reportV}
                </p>
                """, 
                unsafe_allow_html=True
            )
    st.dataframe(response, use_container_width = True)

    if paff:
        response_long = response.reset_index().melt(id_vars=["Political Affiliation", "Answer"], var_name="Year", value_name="Percentage")
        response_long = response_long.loc[response_long["Year"] != "index"]
        response_long["Year"] = response_long["Year"].apply(lambda x: str(x) if isinstance(x, (int, float)) else x)
        nyears = len(response_long.drop_duplicates(subset="Year").Year.to_list())
        if nyears > 1:
            fig = px.bar(
                response_long, 
                y          = "Year", 
                x          = "Percentage", 
                color      = "Answer", 
                barmode    = "stack",
                facet_col  = "Political Affiliation"
            )
            st.plotly_chart(fig, use_container_width = True)
        else:
            fig = px.bar(
                response_long, 
                y          = "Answer", 
                x          = "Percentage", 
                facet_col  = "Political Affiliation"
            )
            st.plotly_chart(fig, use_container_width = True)

    else:
        response_long = response.reset_index().melt(id_vars="Answer", var_name="Year", value_name="Percentage")
        response_long = response_long.loc[response_long["Year"] != "index"]
        response_long["Year"] = response_long["Year"].apply(lambda x: str(x) if isinstance(x, (int, float)) else x)
        nyears = len(response_long.drop_duplicates(subset="Year").Year.to_list())
        if nyears > 1:
            fig = px.bar(
                response_long, 
                y          = "Year", 
                x          = "Percentage", 
                color      = "Answer", 
                barmode    = "stack"
            )
            st.plotly_chart(fig, use_container_width = True)
        else:
            fig = px.bar(
                response_long, 
                y       = "Answer", 
                x       = "Percentage"
            )
            st.plotly_chart(fig, use_container_width = True)
