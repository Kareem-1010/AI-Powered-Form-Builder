import cohere
import streamlit as st
import json
import os
import pandas as pd
import pyqrcode
from io import StringIO

cohere_api_key = "MBRTRJ4tg4hPLzXb2dtzCpPXAN0GDzinF66GsLCq"
cohere_client = cohere.Client(cohere_api_key)

saved_forms_path = "saved_forms.json"
responses_path = "form_responses.csv"

def load_saved_forms():
    if os.path.exists(saved_forms_path):
        with open(saved_forms_path, "r") as file:
            return json.load(file)
    return {}

def save_form(form_id, form_data):
    saved_forms = load_saved_forms()
    saved_forms[form_id] = form_data
    with open(saved_forms_path, "w") as file:
        json.dump(saved_forms, file, indent=4)

def save_response(form_id, responses):
    df = pd.read_csv(responses_path) if os.path.exists(responses_path) else pd.DataFrame()
    responses["form_id"] = form_id
    df = df.append(responses, ignore_index=True)
    df.to_csv(responses_path, index=False)

def generate_form_questions(form_description, goal, target_audience, tone, num_questions, question_preferences, additional_context):
    prompt = (
        f"Generate a fully editable form in JSON format with the following structure:\n"
        f"{{\n"
        f"    \"form_id\": \"feedback_form_001\",\n"
        f"    \"form_title\": \"Customer Feedback Form\",\n"
        f"    \"form_description\": \"{form_description}\",\n"
        f"    \"questions\": [\n"
        f"        {{\n"
        f"            \"type\": \"Open-ended text\",\n"
        f"            \"text\": \"What is your overall impression of our service?\"\n"
        f"        }},\n"
        f"        {{\n"
        f"            \"type\": \"Likert scale\",\n"
        f"            \"text\": \"How satisfied are you with our service? (1 = Not satisfied, 5 = Very satisfied)\",\n"
        f"            \"options\": [1, 2, 3, 4, 5]\n"
        f"        }}\n"
        f"    ]\n"
        f"}}\n"
    )
    try:
        response = cohere_client.generate(
            model="command", prompt=prompt, max_tokens=1000, temperature=0.7
        )
        response_text = response.generations[0].text
        form_data = json.loads(response_text)
        return form_data
    except Exception as e:
        st.error(f"Error while processing response: {e}")
        return None

st.title("AI-Powered Form Generator")

saved_forms = load_saved_forms()

st.sidebar.title("Saved Forms")
form_titles = list(saved_forms.keys())
form_title = st.sidebar.selectbox("Select a Form to Edit", form_titles, index=0 if form_titles else -1)

if form_title and form_title in saved_forms:
    selected_form = saved_forms[form_title]
    st.subheader(f"Editing: {selected_form['form_title']}")
    st.json(selected_form)

form_description = st.text_area("Form Description", placeholder="Describe the purpose of the form.")
goal = st.text_input("Goal/Objective", placeholder="Specify the goal of the form.")
target_audience = st.text_input("Target Audience", placeholder="Who will fill out the form?")
tone = st.selectbox("Preferred Tone", ["Formal", "Casual", "Engaging", "Neutral"])
num_questions = st.selectbox("Number of Questions", ["1-8", "9-16", "17-24", "24+"])
question_preferences = st.multiselect("Question Preferences", ["Multiple-choice", "Likert scale", "Open-ended text", "File uploads"])
additional_context = st.text_area("Additional Context (Optional)", placeholder="Include specific instructions or example questions.")

if st.button("Generate Form"):
    if form_description and goal and target_audience:
        try:
            generated_form = generate_form_questions(
                form_description, goal, target_audience, tone, num_questions, question_preferences, additional_context
            )
            if generated_form:
                form_id = f"feedback_form_{len(saved_forms) + 1}"
                form_data = {
                    "form_id": form_id,
                    "form_title": f"Customer Feedback Form {len(saved_forms) + 1}",
                    "form_description": form_description,
                    "questions": generated_form["questions"]
                }
                save_form(form_id, form_data)
                st.subheader("Generated Form JSON")
                st.code(json.dumps(form_data, indent=4), language="json")
                st.success("Form saved successfully!")
                shareable_link = f"{st.secrets['base_url']}/form/{form_id}"
                st.subheader("Shareable Form Link")
                st.write(shareable_link)
                qr_code = pyqrcode.create(shareable_link)
                st.image(qr_code.png_as_base64_str(scale=5), use_column_width=True)
            else:
                st.error("Failed to generate valid form data.")
        except Exception as e:
            st.error(f"Error generating form: {e}")
    else:
        st.warning("Please fill out all required fields.")

st.subheader("Submit Form Responses")
if form_title and form_title in saved_forms:
    form_data = saved_forms[form_title]
    responses = {}
    for question in form_data["questions"]:
        if question["type"] == "Open-ended text":
            responses[question["text"]] = st.text_input(question["text"])
        elif question["type"] == "Likert scale":
            responses[question["text"]] = st.slider(question["text"], 1, 5)
        elif question["type"] == "Multiple-choice":
            responses[question["text"]] = st.radio(question["text"], question["options"])
    if st.button("Submit Response"):
        save_response(form_title, responses)
        st.success("Response recorded successfully!")

if os.path.exists(responses_path):
    df = pd.read_csv(responses_path)
    st.subheader("Response Analytics")
    st.write(df.describe())
    st.write(df.head())
