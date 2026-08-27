import streamlit as st
from supabase_client import supabase

def get_session():
    session = supabase.auth.get_session()
    if session is None:
        st.switch_page("app.py")
    return session

session = get_session()

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
    </style>
""", unsafe_allow_html=True)

st.title("Reset Password")

new_password = st.text_input("New Password", type="password")
confirm_password = st.text_input("Confirm New Password", type="password")

if st.button("Reset Password"):
    try:
        if new_password != confirm_password:
            st.error("Passwords do not match")
        else:
            supabase.auth.update_user({"password": new_password})
            st.success("Password reset successfully")
            st.switch_page("app.py")
    except Exception as e:
        st.error(f"Error resetting password: {e}")