import streamlit as st
from supabase_client import supabase

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
    </style>
""", unsafe_allow_html=True)

st.title("Forgot Password")

email = st.text_input("Email")

if st.button("Reset Password"):
    try:
        supabase.auth.reset_password_for_email(
            email,
            {
                "redirect_to":"http://localhost:8501/reset_password"
            }
            )
        st.success("Password reset link sent to your email")
        st.switch_page("app.py")
    except Exception as e:
        st.error(f"Error resetting password: {e}")