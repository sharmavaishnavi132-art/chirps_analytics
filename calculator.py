#streamlit run filename.py

import streamlit as st

st.title("simple calculator")
#st.subheader("enter two numbers and select an operation")
st.markdown("Enter two number and select an operation")

c1,c2 = st.columns(2)
fnum=c1.number_input("enter the first number",value=0)
fnum=c2.number_input("enter the second number",value=0)

options=["Addition","Subtraction","Multiplication","Division"]
choice = st.radio("select an operation",options)

button = st.button("calculate")

result=0
if button:
    if choice == "Addition":
        result=fnum + snum
    if choice == "Subtraction":
        result = fnum - snum
    if choice == "Multiplication":
        result = fnum * snum
    if choice == "Division":
        result= fnum / snum

st.success(f"result is {result}")
st.snow()
st.balloons()