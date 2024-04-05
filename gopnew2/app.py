from flask import Flask, jsonify, request
import json
import requests
import os
import openai
from langdetect import detect
from dotenv import load_dotenv
from flask_cors import CORS, cross_origin

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

project_folder = os.path.dirname(__file__)

load_dotenv(os.path.join(project_folder, '.env'))

api_base = os.getenv("API_BASE")
deployment_id = os.getenv("DEPLOYMENT_ID")
api_key = os.getenv("API_KEY")
cognitive_search_endpoint = os.getenv("COGNITIVE_SEARCH_ENDPOINT")
cognitive_search_key = os.getenv("COGNITIVE_SEARCH_KEY")
cognitive_search_index_name = os.getenv("COGNITIVE_SEARCH_INDEX_NAME")
OPENAI_URL = f"{api_base}/openai/deployments/{deployment_id}/extensions/chat/completions?api-version=2023-06-01-preview"

def translate_text(text, target_language):
    openai.api_type = "azure"
    openai.api_base = api_base
    openai.api_version = "2023-06-01-preview"
    openai.api_key = api_key

    message_text = [
        {"role":"system","content":"You are an AI assistant that translates text. You make sure that there are no spelling mistakes in your response."},
        {"role":"user","content":f"Translate the following test to, please make sure that structure and meaing of the sentense is not changed {target_language} : {text}"}]

    completion = openai.ChatCompletion.create(
    engine=deployment_id,
    messages = message_text,
    temperature=0,
    max_tokens=1400,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
    stream=False
    )
    

    return completion["choices"][0]["message"]["content"]

@app.route("/")
def index():
    return f"<center><h1>Flask App deployment on AZURE</h1></center"

@app.route("/get_response", methods=["POST"])
@cross_origin()
def get_response():
    url = OPENAI_URL

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }
    user_input = request.get_json().get("message")

    input_language = detect(user_input)

    # Translate input to English if it's in Punjabi
    if input_language == "pa":
        user_input = translate_text(user_input, "English")

    body = {
    "temperature": 0,
    "max_tokens": 1400,
    "top_p": 1.0,
    "stream": False,
    "dataSources": [
        {
            "type": "AzureCognitiveSearch",
            "parameters": {
                "endpoint": cognitive_search_endpoint,
                "key": cognitive_search_key,
                "indexName": cognitive_search_index_name
            }
        }
    ],
    "messages": [
        {
            "role": "user",
            "content": user_input
        }
    ]
}

    response = requests.post(url, headers=headers, json=body)

    json_response = response.json()

    message = json_response["choices"][0]["messages"][1]["content"]
    

    if input_language == "pa":
        message = translate_text(message, "Punjabi")


    tool_message_content = json_response["choices"][0]["messages"][0]["content"]

    # Converting the content string to a dictionary

    tool_message_content_dict = json.loads(tool_message_content)

    # Extracting the 'citations' field if present
    url2 = ""
    if "citations" in tool_message_content_dict:
        citations = tool_message_content_dict["citations"]
        

        # Extracting the URL from the first citation if present

        if citations:
            first_citation = citations[0]

            if "url" in first_citation:
                url2 = first_citation["url"]

                # print(url2)

            else:
                print("No URL found in the first citation")

        else:
            print("No citations found")
    else:
        print("No 'citations' field found in the tool message content")

    # print(message)
    url2 = url2.replace("/originaldocuments/", "/actualdocuments/") #  change citiation url to original documents url 

    return jsonify({"assistant_content": message + " " +  url2})
    

if __name__ == "__main__":
    app.run()
