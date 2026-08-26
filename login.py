import streamlit as st
from supabase_client import supabase

def login():

    # Hide sidebar on login page
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    st.title("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    st.markdown("[Forgot Password](forgot_password)")

    if st.button("Login"):

        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            st.session_state["user"] = response.user
            st.session_state["session"] = response.session

            st.success("Login successful!")
            st.rerun()

        except Exception:
            st.error("Invalid email or password")

    st.markdown("Don't have an account? [Sign up](signup)")


