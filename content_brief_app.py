import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI


# Function to fetch and parse the URL
def fetch_and_parse_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        page_content = response.content
        soup = BeautifulSoup(page_content, "html.parser")
        return soup
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching the URL: {e}")
        return None


# Function to analyze the page structure
def analyze_page_structure(soup):
    content_brief = {
        "headlines": [],
        "body_texts": [],
        "ctas": [],
        "images": [],
        "videos": [],
    }

    # Check for the <main> tag and find everything inside it
    main_content = soup.find("main")
    if main_content:
        content_section = main_content
    else:
        content_section = soup

    # Extract headlines
    for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        for headline in content_section.find_all(tag):
            content_brief["headlines"].append(
                {"tag": tag, "text": headline.get_text(strip=True)}
            )

    # Extract body texts
    for paragraph in content_section.find_all("p"):
        content_brief["body_texts"].append(paragraph.get_text(strip=True))

    # Extract CTAs
    for link in content_section.find_all("a"):
        if "href" in link.attrs:
            content_brief["ctas"].append(
                {"text": link.get_text(strip=True), "href": link.attrs["href"]}
            )

    for button in content_section.find_all("button"):
        content_brief["ctas"].append({"text": button.get_text(strip=True)})

    # Extract images
    for img in content_section.find_all("img"):
        img_details = {
            "src": img.attrs.get("src", ""),
            "alt": img.attrs.get("alt", ""),
            "width": img.attrs.get("width", "auto"),
            "height": img.attrs.get("height", "auto"),
        }
        content_brief["images"].append(img_details)

    # Extract videos
    for video in content_section.find_all("video"):
        video_details = {
            "src": video.attrs.get("src", ""),
            "width": video.attrs.get("width", "auto"),
            "height": video.attrs.get("height", "auto"),
            "format": video.attrs.get("type", "video/mp4"),
        }
        content_brief["videos"].append(video_details)

    return content_brief


# Function to generate content using OpenAI's GPT-3.5
def generate_content(prompt, openai_api_key):
    """[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        {"role": "user", "content": "Where was it played?"}
    ]"""
    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", messages=prompt, temperature=0.7, max_tokens=1000
    )
    return response.choices[0].message.content


# Streamlit app
TITLE = "AI Content Generation from URL"
st.set_page_config(page_title=TITLE)
st.title(TITLE)
url = st.text_input("Enter the URL of the web page:")

# Check if OPENAI_API_KEY is set in the environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    st.sidebar.write("Using OpenAI API key from environment variable.")
else:
    st.sidebar.write("Please provide your OpenAI API key:")
    openai_api_key = st.sidebar.text_input("Enter OpenAI API Key:", type='password')
    if openai_api_key:
        st.write(
            "API key provided. Make sure to set it in your environment variable for future use."
        )

if url:
    soup = fetch_and_parse_url(url)
    if soup:
        st.write(
            "To generate content, please provide your OpenAI API key in the left sidebar and click 'Generate Content'."
        )
        if st.button("Generate Content"):
            content_brief = analyze_page_structure(soup)

            # Create a system prompt to generate a complete article
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

            st.subheader("Generated Content")
            st.write(generated_content)
