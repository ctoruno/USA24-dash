import re
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
    layout = "wide"
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

pass1, pass2, pass3 = st.columns(3)

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
        with pass2:
            st.text_input(
                "Password", type="password", on_change=password_entered, key="password"
            )
            return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        with pass2:
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
        _, res = dbx.files_download("/data4app.csv")
        data = res.content

        # Reading data frames
        with BytesIO(data) as file:
            df = pd.read_csv(file)

        return df
    
    data = load_data()
    data["year"] = pd.to_numeric(data["year"], downcast='integer')
    data = pd.merge(
        data,
        datamap,
        how = "left",
        on  = "variable"
    )

    # # Instructions and filters/parameters
    st.markdown(
        """
        <h1 style='text-align: center;'>USA Data Dashboard</h1>
        """,
        unsafe_allow_html = True
    )
    col1, col2 = st.columns(2)
    with col1:
        topic = st.selectbox(
            "Please select a topic from the list below:",
            sorted(data
            .drop_duplicates(subset = "topic")
            .topic.to_list())
        )
        question = st.selectbox(
            "Please select a question from the list below:",
            (data
            .loc[data["topic"] == topic]
            .drop_duplicates(subset = "question_text")
            .question_text.to_list())
        )
    with col2:
        years = st.multiselect(
            "Please select the years for which you want to delimit your results:",
            (data
            .loc[data["question_text"] == question]
            .drop_duplicates(subset = "year")
            .year.to_list()),
            default = [2024]
        )
        sample = st.selectbox(
            "Which sample would you like to explore?",
            ["Total sample", "Disaggregate by political affiliation", "Disaggregate by ethnicity"]
        )

    # Subsetting data as requested
    sample_values = {
        "Total sample"                         : ["Total"],
        "Disaggregate by political affiliation": ["Democrats", "Republicans"],
        "Disaggregate by ethnicity"            : ["White", "Other"]
    }
    demographics = sample_values[sample]

    title = (
        data
        .loc[data["question_text"] == question]
        .drop_duplicates(subset = "question_text")
        .chart_title.iloc[0]
    )
    subtitle = (
        data
        .loc[data["question_text"] == question]
        .drop_duplicates(subset = "question_text")
        .chart_subtitle.iloc[0]
    )
    panel_title = (
        data
        .loc[data["question_text"] == question]
        .drop_duplicates(subset = "question_text")
        .panel_title.iloc[0]
    )
    panel_subtitle = (
        data
        .loc[data["question_text"] == question]
        .drop_duplicates(subset = "question_text")
        .panel_subtitle.iloc[0]
    )
    encodings = (
        data
        .loc[data["question_text"] == question]
        .drop_duplicates(subset = "question_text")
        .encoding.iloc[0]
    )

    response = (
        data.copy()
        .loc[
            (data["question_text"] == question) & (data["sample"].isin(demographics)) & (data["year"].isin(years)),
            ["year", "sample", "answer", "percentage"]
        ]
        .reset_index(drop = True)
        .rename(
            columns = {
                "year" : "Year",
                "percentage" : "Percentage",
                "sample" : "Demographic Group",
                "answer" : "Answer"
            }
        )
    )
    response["Year"] = response["Year"].astype(str)

    # Split the string into key-value pairs
    def get_encdict(string):
        new_string = re.sub("\s+(?=\d+)", "<>", encodings)
        pairs = new_string.split("<>")
        dictionary = {}
        for pair in pairs:
            key, value = re.split("=", pair, maxsplit=1)
            dictionary[key] = value.strip()
        return(dictionary)
    
    recoding_dict = get_encdict(encodings)
    response["Answer"] = response["Answer"].replace(recoding_dict)

    st.markdown("----")
    col11, col22, col33 = st.columns([0.475, 0.05, 0.475])
    with col11:
        st.markdown(
            f"""
            <p class='jtext'>
                You have selected to visualize the data for the following question: <b><i>{question}</i></b>
            </p>
            <p class='jtext'>
                In the graphic report, this question is visualized using the following <b>METADATA</b>:
                <ul>
                    <li><b>Chart title</b>: <i>{title}</i> </li>
                    <li><b>Chart subtitle</b>: <i>{subtitle}</i> </li>
                    <li><b>Panel Header</b>: <i>{panel_title}</i> </li>
                    <li><b>Panel Subheader</b>: <i>{panel_subtitle}</i> </li>
                </ul>
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
                    {encodings}
                </p>
                """, 
                unsafe_allow_html=True
            )
    with col33:
        st.markdown(
            f"""
            <p class='jtext'>
                The column <i>Answer</i> might be a little bit tricky given the raw state of the data that we just collected.
                Therefore, if the column has numbers, please refer to the encodings listed on the left. If the column says
                <i>See metadata</i>, that means that the answers were modified to group encodings, in that case please 
                refer to the metadata listed on the left, specially to the <i>CHART SUBTITLE</i>.
            </p>
            """, 
            unsafe_allow_html=True
        )
        st.dataframe(
            (
                response
                .set_index("Year")
                .style.format({"Percentage": "{:.1f}".format})
            ), 
            use_container_width = True
        )
        
    fig = px.bar(
        response.drop_duplicates(), 
        x          = "Demographic Group", 
        y          = "Percentage", 
        color      = "Answer", 
        facet_col  = "Year",
        barmode    = "group"
    )
    fig.update_yaxes(range=[0, 105])
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    st.plotly_chart(fig, use_container_width = True)
   
    