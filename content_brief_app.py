import os
import requests
from bs4 import BeautifulSoup
import streamlit as st
from pydantic import BaseModel, HttpUrl, ValidationError
from openai import OpenAI


# Define a Pydantic model for user input
class UserInput(BaseModel):
    url: HttpUrl


# Function to fetch and parse the URL
def fetch_and_parse_url(url: str):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        page_content = response.content
        soup = BeautifulSoup(page_content, "html.parser")
        return soup
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching the URL: {e}")
        return None


# Function to extract content
def extract_content(soup, tag, attr=None):
    elements = soup.find_all(tag)
    if attr:
        return [
            {attr: el.attrs.get(attr, ""), "text": el.get_text(strip=True)}
            for el in elements
        ]
    else:
        return [el.get_text(strip=True) for el in elements]


# Function to analyze the page structure
def analyze_page_structure(soup):
    if soup.find("article"):
        content_section = soup.find("article")
    elif soup.find("main"):
        content_section = soup.find("main")
    else:
        content_section = soup.find("body")

    content_brief = {
        "headlines": [],
        "body_texts": extract_content(content_section, "p"),
        "ctas": extract_content(content_section, "a", "href")
        + extract_content(content_section, "button"),
        "images": extract_content(content_section, "img", "src"),
        "videos": extract_content(content_section, "video", "src"),
    }

    for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        content_brief["headlines"].extend(extract_content(content_section, tag))

    return content_brief


# Function to generate content using OpenAI's GPT-3.5
def generate_content(prompt, openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", messages=prompt, temperature=0.7, max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating content: {e}")
        return None


# Function to generate a summary and DALL-E prompt using OpenAI
def generate_summary_and_prompt(generated_content, openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    try:
        summary_prompt = [
            {"role": "system", "content": "You are a summarization assistant."},
            {
                "role": "user",
                "content": f"Summarize the following content and create a prompt for generating a relevant image: {generated_content}",
            },
        ]
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=summary_prompt,
            temperature=0.7,
            max_tokens=300,
        )
        summary_and_prompt = response.choices[0].message.content
        return summary_and_prompt
    except Exception as e:
        st.error(f"Error generating summary and DALL-E prompt: {e}")
        return None


# Function to generate an image using DALL-E
def generate_image(dalle_prompt, openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    try:
        response = client.images.generate(
            model="dall-e-2",
            prompt=dalle_prompt + " The generated image must not contain any text.",
            size="512x512",  # Set image size to 512x512
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        st.error(f"Error generating image: {e}")
        return None


# Streamlit app
TITLE = "AI Content Generation from URL"
st.set_page_config(page_title=TITLE)
st.title(TITLE)
url_input = st.text_input("Enter the URL of the web page:")

openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.sidebar.warning(
        "OpenAI API key not found in environment variables. Please provide your OpenAI API key:"
    )
    openai_api_key = st.sidebar.text_input("Enter OpenAI API Key:", type="password")
    if openai_api_key:
        st.success(
            "API key provided. Make sure to set it in your environment variable for future use."
        )
else:
    st.sidebar.success("Using OpenAI API key from environment variable.")

if url_input:
    try:
        user_input = UserInput(url=url_input)  # Validate and sanitize user input
        url = user_input.url
        soup = fetch_and_parse_url(url)
        if soup:
            st.write(
                "To generate content, please provide your OpenAI API key in the left sidebar and click 'Generate Content'."
            )
            if st.button("Generate Content"):
                content_brief = analyze_page_structure(soup)

                system_prompt = {
                    "role": "system",
                    "content": "You are a content creator. Based on the following components, generate a coherent and engaging article. Use the headlines, body texts, CTAs, images, and videos appropriately.",
                }

                user_prompt = {
                    "role": "user",
                    "content": f"""
                    Here are the components:
                    Headlines: {content_brief["headlines"]}
                    Body Texts: {content_brief["body_texts"]}
                    CTAs: {content_brief["ctas"]}
                    """,
                }

                prompts = [system_prompt, user_prompt]
                generated_content = generate_content(prompts, openai_api_key)

                if generated_content:
                    # Generate a summary and DALL-E prompt
                    summary_and_prompt = generate_summary_and_prompt(
                        generated_content, openai_api_key
                    )
                    if summary_and_prompt:
                        # Generate an image using the summary and DALL-E prompt
                        generated_image_url = generate_image(
                            summary_and_prompt, openai_api_key
                        )
                        if generated_image_url:
                            st.subheader("Generated Image")
                            st.image(generated_image_url)

                    st.subheader("Generated Content")
                    st.write(generated_content)
    except ValidationError as e:
        st.error(f"Invalid URL: {e}")
