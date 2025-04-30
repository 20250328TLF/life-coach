import streamlit as st
import os
import re
from notion_client import Client
from datetime import datetime

st.set_page_config(page_title="Add Reflection")
st.title("📝 Add a Reflection from Structured Text")

# Load secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
REFLECTION_DB_ID = os.getenv("NOTION_REFLECTION_DB_ID")
THEMES_DB_ID = os.getenv("NOTION_THEME_DB_ID")  # <-- You will need to add this secret in Streamlit

# Initialize Notion client
notion = Client(auth=NOTION_TOKEN)

# Step 1: Get list of existing Journal Themes
def get_existing_themes():
    response = notion.databases.query(database_id=THEMES_DB_ID)
    return [r['properties']['Name']['title'][0]['plain_text'] for r in response['results'] if r['properties']['Name']['title']]

existing_themes = get_existing_themes()

# Step 2: Paste structured reflection
with st.form("reflection_form"):
    raw_input = st.text_area("Paste your structured reflection (from ChatGPT or your prompt):", height=300)
    submitted = st.form_submit_button("Parse Reflection")

# Step 3: Parse fields from the input
if submitted and raw_input:
    def extract_field(label, text, multiline=False):
        pattern = rf"{label}:\s*(.*?)(?:\n\n|$)" if multiline else rf"{label}:\s*(.*)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ""

    title = extract_field("Session Title", raw_input)
    date = extract_field("Session Date", raw_input) or datetime.today().strftime('%Y-%m-%d')
    mood = extract_field("Mood", raw_input)
    intensity = extract_field("Intensity", raw_input)
    summary = extract_field("Summary", raw_input, multiline=True)
    insights = extract_field("Insights", raw_input, multiline=True)
    theme_text = extract_field("Topic/Theme", raw_input)

    parsed_themes = [t.strip() for t in re.split(",|\n|;", theme_text) if t.strip()]
    known_themes = [t for t in parsed_themes if t in existing_themes]
    new_themes = [t for t in parsed_themes if t not in existing_themes]

    st.subheader("🧠 Parsed Reflection")
    st.markdown(f"**Title:** {title}")
    st.markdown(f"**Date:** {date}")
    st.markdown(f"**Mood:** {mood}")
    st.markdown(f"**Intensity:** {intensity}")
    st.markdown(f"**Summary:** {summary}")
    st.markdown(f"**Insights:**\n{insights}")

    selected_themes = st.multiselect(
        "Select Journal Themes:", options=existing_themes, default=known_themes)

    if new_themes:
        st.warning(f"The following themes were not recognized and will be created if submitted: {', '.join(new_themes)}")

    if st.button("✅ Submit to Notion"):
        # Step 4: Prepare properties for Notion page
        properties = {
            "Session Title": {"title": [{"text": {"content": title}}]},
            "Session Date": {"date": {"start": date}},
            "Mood": {"select": {"name": mood}},
            "Intensity": {"number": int(intensity) if intensity.isdigit() else None},
            "Summary": {"rich_text": [{"text": {"content": summary}}]},
            "Insights": {"rich_text": [{"text": {"content": insights}}]},
        }

        # Step 5: Link to existing themes + optionally create new ones
        theme_ids = []
        for theme_name in selected_themes + new_themes:
            # Search for theme page
            results = notion.databases.query(
                database_id=THEMES_DB_ID,
                filter={"property": "Name", "rich_text": {"equals": theme_name}}
            )
            if results['results']:
                theme_ids.append({"id": results['results'][0]['id']})
            else:
                # Create the new theme in Journal Themes DB
                new_theme = notion.pages.create(
                    parent={"database_id": THEMES_DB_ID},
                    properties={"Name": {"title": [{"text": {"content": theme_name}}]}}
                )
                theme_ids.append({"id": new_theme['id']})

        properties["Journal Themes"] = {"relation": theme_ids}

        # Create the page in Reflections Journal
        notion.pages.create(
            parent={"database_id": REFLECTION_DB_ID},
            properties=properties
        )

        st.success("Reflection successfully saved to Notion!")
