import streamlit as st

def inject_global_css():
    custom_css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Manrope', sans-serif;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def set_background(image_path):
    import base64
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
    css = f"""
    <style>
    .stApp {{
        background: url("data:image/jpg;base64,{encoded_image}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-color: rgba(0, 0, 0, 0.8); /* Add a semi-transparent overlay */
        background-blend-mode: overlay; /* Blend the image with the overlay */
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

