import streamlit as st
import os
import re
from notion_client import Client
from datetime import datetime, timedelta
import json

st.set_page_config(page_title="Add Reflection")
st.title("📝 Add a Reflection from Structured Text")

# Load secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
REFLECTION_DB_ID = os.getenv("NOTION_REFLECTION_DB_ID")
THEME_DB_ID = os.getenv("NOTION_THEME_DB_ID")
ACTION_ITEMS_DB_ID = os.getenv("NOTION_TASK_DB_ID")  # Add this secret in Streamlit
READINGS_DB_ID = os.getenv("NOTION_READING_DB_ID")  # Add this secret in Streamlit

# Initialize Notion client
notion = Client(auth=NOTION_TOKEN)

# Step 1: Get list of existing Journal Themes
def get_existing_themes():
    response = notion.databases.query(database_id=THEME_DB_ID)
    return [r['properties']['Name']['title'][0]['plain_text'] for r in response['results'] if r['properties']['Name']['title']]

existing_themes = get_existing_themes()

# Step 2: Paste structured reflection
with st.form("reflection_form"):
    raw_input = st.text_area("Paste your structured reflection (from ChatGPT or your prompt):", height=400)
    submitted = st.form_submit_button("Parse Reflection")

# Step 3: Parse fields from the input
if submitted and raw_input:
    try:
        reflection = json.loads(raw_input)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
        st.stop()

    title = reflection.get("Session Title", "Untitled")
    date = reflection.get("Session Date", datetime.today().strftime('%Y-%m-%d'))
    mood = reflection.get("Mood", "")
    intensity = reflection.get("Intensity", None)
    summary = reflection.get("Summary", "")
    insights = reflection.get("Insights", [])
    parsed_themes = reflection.get("Theme", [])
    action_items = reflection.get("Journal Action Items", [])
    recommended_readings = reflection.get("Journal Readings", [])

    # Ensure insights, action_items, recommended_readings are lists if they are strings
    if isinstance(insights, str):
        insights = [insights]
    if isinstance(action_items, str):
        action_items = [action_items]
    if isinstance(recommended_readings, str):
        recommended_readings = [recommended_readings]

    # Ensure parsed_themes is a list if it's a string
    if isinstance(parsed_themes, str):
        parsed_themes = [t.strip() for t in re.split(",|\n|;", parsed_themes) if t.strip()]

    known_themes = [t for t in parsed_themes if t in existing_themes]
    new_themes = [t for t in parsed_themes if t not in existing_themes]

    st.subheader("🧠 Parsed Reflection")
    st.markdown(f"**Title:** {title}")
    st.markdown(f"**Date:** {date}")
    st.markdown(f"**Mood:** {mood}")
    st.markdown(f"**Intensity:** {intensity if intensity is not None else ''}")
    st.markdown("**Summary:**")
    st.markdown(summary)
    st.markdown("**Insights:**")
    for insight in insights:
        st.markdown(insight)

    if action_items:
        st.markdown("**Journal Action Items:**")
        for ai in action_items:
            st.markdown(f"- {ai}")

    if recommended_readings:
        st.markdown("**Journal Readings:**")
        for rd in recommended_readings:
            st.markdown(f"- {rd}")

    selected_themes = st.multiselect(
        "Select Journal Themes:", options=existing_themes, default=known_themes)

    if new_themes:
        st.warning(f"The following themes were not recognized and will be created if submitted: {', '.join(new_themes)}")

    if st.button("✅ Submit to Notion"):
        # Step 4: Prepare properties for Notion page
        properties = {
            "Session Title": {"title": [{"text": {"content": title}}]},
            "Session Date": {"date": {"start": date}},
            "Mood": {"select": {"name": mood}} if mood else None,
            "Intensity": {"number": int(intensity) if intensity is not None and str(intensity).isdigit() else None} if intensity else None,
            "Summary": {"rich_text": [{"text": {"content": summary}}]} if summary else None,
            "Insights": {"rich_text": [{"text": {"content": "\n".join(insights)}}]} if insights else None,
        }

        # Remove None values from properties
        properties = {k: v for k, v in properties.items() if v is not None}

        # Step 5: Link to existing themes + optionally create new ones
        theme_ids = []
        for theme_name in selected_themes + new_themes:
            # Search for theme page
            results = notion.databases.query(
                database_id=THEME_DB_ID,
                filter={"property": "Name", "rich_text": {"equals": theme_name}}
            )
            if results['results']:
                theme_ids.append({"id": results['results'][0]['id']})
            else:
                # Create the new theme in Journal Themes DB
                new_theme = notion.pages.create(
                    parent={"database_id": THEME_DB_ID},
                    properties={"Name": {"title": [{"text": {"content": theme_name}}]}}
                )
                theme_ids.append({"id": new_theme['id']})

        if theme_ids:
            properties["Journal Themes"] = {"relation": theme_ids}

        # Create the page in Reflections Journal
        reflection_page = notion.pages.create(
            parent={"database_id": REFLECTION_DB_ID},
            properties=properties
        )
        reflection_id = reflection_page['id']

        # Step 6: Create Action Items and link to Reflection and Themes
        for action_item in action_items:
            due_date = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
            ai_properties = {
                "Name": {"title": [{"text": {"content": action_item}}]},
                "Reflection": {"relation": [{"id": reflection_id}]},
                "Due Date": {"date": {"start": due_date}},
            }
            if theme_ids:
                ai_properties["Journal Themes"] = {"relation": theme_ids}
            notion.pages.create(
                parent={"database_id": ACTION_ITEMS_DB_ID},
                properties=ai_properties
            )

        # Step 7: Create Recommended Readings and link to Reflection and Themes
        for reading in recommended_readings:
            rd_properties = {
                "Name": {"title": [{"text": {"content": reading}}]},
                "Reflection": {"relation": [{"id": reflection_id}]},
            }
            if theme_ids:
                rd_properties["Journal Themes"] = {"relation": theme_ids}
            notion.pages.create(
                parent={"database_id": READINGS_DB_ID},
                properties=rd_properties
            )

        st.success("Reflection, Action Items, and Recommended Readings successfully saved to Notion!")
