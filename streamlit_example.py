import streamlit as st

st.title("PDF Upload")

uploaded_file = st.file_uploader(
    "Upload a PDF",
    type=["pdf"]
)

if uploaded_file:

    st.success(
        f"Uploaded: {uploaded_file.name}"
    )

    st.write(
        f"File size: {uploaded_file.size} bytes"
    )