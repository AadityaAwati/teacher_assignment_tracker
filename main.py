import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import json

st.set_page_config(layout="wide")

st_autorefresh(interval=30000, key="refresh")

PROJECT_ID = st.secrets["firebase"]["project_id"]
API_KEY    = st.secrets["firebase"]["api_key"]

BASE_URL = (
    f"https://firestore.googleapis.com/v1/"
    f"projects/{PROJECT_ID}/databases/(default)/documents/main"
)

subjects = [
    "English", "Kannada", "Hindi", "Math",
    "Science", "SST", "Computer", "Art"
]

if "editing" not in st.session_state:
    st.session_state.editing = None

# ---------------------------------------------------------------------------
# Firestore REST helpers
# ---------------------------------------------------------------------------

def parse_value(v: dict):
    if "stringValue"    in v: return v["stringValue"]
    if "integerValue"   in v: return str(v["integerValue"])
    if "doubleValue"    in v: return str(v["doubleValue"])
    if "booleanValue"   in v: return str(v["booleanValue"])
    if "timestampValue" in v: return v["timestampValue"]
    if "nullValue"      in v: return "None"
    if "mapValue"       in v:
        fields = v["mapValue"].get("fields", {})
        return ", ".join(f"{k}: {parse_value(fv)}" for k, fv in fields.items())
    if "arrayValue"     in v:
        items = v["arrayValue"].get("values", [])
        return ", ".join(parse_value(i) for i in items)
    return str(list(v.values())[0])

def to_firestore_value(val: str) -> dict:
    """Wrap a plain Python string into a Firestore REST value object."""
    return {"stringValue": val}

def get_doc(doc_name: str) -> dict:
    url = f"{BASE_URL}/{doc_name}?key={API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        raw_fields = resp.json().get("fields", {})
        return {k: parse_value(v) for k, v in raw_fields.items()}
    except requests.exceptions.RequestException as e:
        st.error(f"Could not load {doc_name}: {e}")
        return {}

def save_doc(doc_name: str, data: dict):
    """Overwrite an entire document with a plain {str: str} dict."""
    url = f"{BASE_URL}/{doc_name}?key={API_KEY}"
    body = {
        "fields": {k: to_firestore_value(v) for k, v in data.items()}
    }
    try:
        resp = requests.patch(url, json=body, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"Could not save {doc_name}: {e}")

def delete_key(doc_name: str, key: str):
    data = get_doc(doc_name)
    if key in data:
        del data[key]
        save_doc(doc_name, data)

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

st.markdown("""
<style>
div.stButton > button {
    height:40px !important;
    width:100%;
    border-radius:10px !important;
    margin-left:10px;
    margin-right:10px;
    margin-top: 10px;
    margin-down: 10px;
}
h1,h2 { font-family:Georgia; }
h3    { font-family:Courier New; }
div[data-testid="stWidgetLabel"] p {
    font-family:Courier New;
    font-weight:bold;
}
[data-testid="column"]:nth-of-type(1){
    background-color:#F0F2F6;
    padding:20px;
    border-radius:10px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def announcement_section(title, color, doc_name):
    st.markdown(f"""
    <div style='background:{color};padding:20px;border-radius:10px;'>
    <h3>{title}</h3>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([8, 1])
    text = c1.text_input("", key=f"{title}_new")

    for _ in range(5):
        st.text("")

    if c2.button("Add", key=f"{title}_add"):
        if text:
            data = get_doc(doc_name)
            n = len(data) + 1
            data[f"announcement{n}"] = text
            save_doc(doc_name, data)
            st.rerun()

    data = get_doc(doc_name)
    for k, v in data.items():
        a, b, c = st.columns([8, 1, 1])
        a.code(v)
        if b.button("Edit", key=f"{k}_edit"):
            st.session_state.editing = k
        if c.button("Delete", key=f"{k}_delete"):
            delete_key(doc_name, k)
            st.rerun()

def subject_section(title, color, doc_name):
    st.markdown(f"""
    <div style='background:{color};padding:20px;border-radius:10px;'>
    <h3>{title}</h3>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([4, 4, 1])
    subject = c1.selectbox("", subjects, key=f"{title}_subject")
    text    = c2.text_input("", key=f"{title}_text")

    if c3.button("Add", key=f"{title}_add"):
        if text:
            data = get_doc(doc_name)
            data[subject] = text
            save_doc(doc_name, data)
            st.rerun()

    data = get_doc(doc_name)
    if not data:
        st.code("None")

    for subject_name, value in data.items():
        a, b, c = st.columns([8, 1, 1])
        a.code(f"{subject_name} : {value}")

        if b.button("Edit", key=f"{title}_{subject_name}_edit"):
            st.session_state.editing = (title, subject_name)

        if c.button("Delete", key=f"{title}_{subject_name}_delete"):
            delete_key(doc_name, subject_name)
            st.rerun()

        if (st.session_state.editing is not None
                and st.session_state.editing[0] == title
                and st.session_state.editing[1] == subject_name):
            st.markdown("---")
            d1, d2, d3 = st.columns([4, 4, 1])
            edited_subject = d1.selectbox(
                "Subject", subjects,
                index=subjects.index(subject_name),
                key=f"{title}_{subject_name}_subject"
            )
            edited_text = d2.text_input(
                "Text", value=value,
                key=f"{title}_{subject_name}_text"
            )
            if d3.button("Save", key=f"{title}_{subject_name}_save"):
                current = get_doc(doc_name)
                if subject_name in current:
                    del current[subject_name]
                current[edited_subject] = edited_text
                save_doc(doc_name, current)
                st.session_state.editing = None
                st.rerun()

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

col1,  col2,  col3  = st.columns([10, 1, 1])
col4,  col5,  col6  = st.columns([10, 1, 1])
col7,  col8,  col9  = st.columns([10, 1, 1])
col10, col11, col12 = st.columns([10, 1, 1])
col13, col14, col15 = st.columns([10, 1, 1])

with col1:
    st.title("Student Assignment Tracker [Teacher v1.0]")

with col4:
    for _ in range(10):
        st.text("")
    announcement_section("ANNOUNCEMENTS",      "#a69b03", "announcements")

with col7:
    for _ in range(5):
        st.text("")
    subject_section("HOMEWORK ASSIGNMENTS",    "#a34903", "homework")

with col10:
    for _ in range(5):
        st.text("")
    subject_section("ACTIVITIES",              "#166bf5", "activities")

with col13:
    for _ in range(5):
        st.text("")
    subject_section("CLASS TESTS",             "#03a619", "class_tests")
