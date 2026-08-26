import streamlit as st
from supabase_client import supabase

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
    </style>
""", unsafe_allow_html=True)

st.title("Signup")



name = st.text_input("Username")
email = st.text_input("Email")
password = st.text_input("Password", type="password")

if st.button("Sign Up"):
    try:
        response = supabase.auth.sign_up({
            "email":email,
            "password":password,
            "options":{
                "data":{
                    "name":name
                }
            }
        })
        st.success("Account successfully created")
        st.switch_page("login.py")
    except Exception as e:
        st.error(f"Error creating account: {e}")
        
st.markdown("Already have an account? [Sign In](app)")

        