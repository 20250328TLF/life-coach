import streamlit as st
import os
from notion_client import Client
from datetime import datetime

# Load secrets
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
REFLECTION_DB_ID = os.getenv("NOTION_REFLECTION_DB_ID")

# Connect to Notion
notion = Client(auth=NOTION_TOKEN)

st.set_page_config(page_title="AI Life Coach")
st.title("🧠 AI Life Coach")
st.subheader("Recent Reflections")

# Fetch pages from the Notion Reflections Journal
def fetch_reflections():
    def get_theme_names(relation_list):
        names = []
        for rel in relation_list:
            try:
                theme_page = notion.pages.retrieve(rel["id"])
                name_prop = theme_page["properties"].get("Name", {})
                if "title" in name_prop and name_prop["title"]:
                    names.append(name_prop["title"][0]["plain_text"])
            except Exception as e:
                st.warning(f"⚠️ Failed to fetch theme: {e}")
        return ", ".join(names)
    
    results = notion.databases.query(
        **{
            "database_id": REFLECTION_DB_ID,
            "sorts": [{"property": "Session Date", "direction": "descending"}],
            "page_size": 10
        }
    ).get("results")
    
    #st.write("✅ Raw Notion response:", results)

    reflections = []
    for page in results:
        props = page["properties"]

        def get_text(field):
            return (
                props[field]["rich_text"][0]["plain_text"]
                if props.get(field) and props[field]["rich_text"]
                else ""
            )

        def get_title(field):
            return (
                props[field]["title"][0]["plain_text"]
                if props.get(field) and props[field]["title"]
                else "Untitled"
            )

        def get_date(field):
            return (
                props[field]["date"]["start"]
                if props.get(field) and props[field]["date"]
                else None
            )

        def get_multi_select(field):
            return ", ".join([tag["name"] for tag in props[field]["multi_select"]]) if props.get(field) else ""

        def get_select(field):
            return props[field]["select"]["name"] if props.get(field) and props[field]["select"] else ""

        def get_number(field):
            return props[field]["number"] if props.get(field) and props[field]["number"] else None

        reflections.append({
            "title": get_title("Session Title"),
            "date": get_date("Session Date"),
            "summary": get_text("Summary"),
            "insights": get_text("Insights"),
            "mood": get_select("Mood"),
            "topics": get_theme_names(props["Theme"]["relation"]) if props.get("Theme") else "",
            "intensity": get_number("Intensity"),
        })
        st.write("🧩 Raw Theme relation list:", props["Theme"])

    return reflections

# Display reflections
reflections = fetch_reflections()

if reflections:
    for r in reflections:
        st.markdown(f"### 🧠 {r['title']}")
        st.markdown(f"**📅 Date:** {r['date']}")
        st.markdown(f"**🎭 Mood:** {r['mood']} &nbsp;&nbsp;&nbsp; **🎯 Topics:** {r['topics']} &nbsp;&nbsp;&nbsp; **🔥 Intensity:** {r['intensity']}")
        st.markdown(f"**✍️ Summary:** {r['summary']}")
        st.markdown(f"**💡 Insights:** {r['insights']}")
        st.markdown("---")
else:
    st.info("No reflections found. Add some entries to your Notion Reflections Journal to get started.")