import streamlit as st
import asyncio
from main import process_request 

st.set_page_config(
    page_title="CrowdBrew",
    page_icon="☕",
    layout="centered"
)

st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #795548;
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #5d4037;
        color: white;
    }
    
    .card-header {
        border-left: 5px solid #795548;
        padding-left: 15px;
        margin-bottom: 15px;
    }
    .card-header h3 {
        margin: 0;
        padding: 0;
        color: #333;
        font-size: 1.4rem;
    }
    .card-header p {
        margin: 0;
        color: #666;
        font-style: italic;
    }
    
    hr {
        margin-top: 1em;
        margin-bottom: 1em;
        border: 0;
        border-top: 1px solid #eee;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("☕ CrowdBrew")
st.subheader("Asystent promocyjnego menu dla kawiarni")

# --- INPUT ---
with st.form("search_form"):
    date_query = st.text_input("Na kiedy szukamy wydarzeń?", placeholder="np. 13 grudnia 2025")
    submitted = st.form_submit_button("🔍 Znajdź wydarzenia i stwórz menu")

# --- APPLICATION LOGIC ---
if submitted and date_query:
    with st.spinner('CrowdBrew przeszukuje Łódź i parzy kawę... (to potrwa ok. 20-30s)'):
        try:
            results = asyncio.run(process_request(date_query))
            
            if not results:
                st.error("Asystent nie znalazł wydarzeń lub wystąpił błąd parsowania. Spróbuj innej daty.")
            else:
                st.success(f"Sukces! Znaleziono i zapisano {len(results)} propozycji.")
                
                # --- RESULTS LOOP ---
                for item in results:

                    with st.container(border=True):
                        
                        st.markdown(f"""
                        <div class="card-header">
                            <h3>📅 {item.get('event_date')} | {item.get('event_name')}</h3>
                            <p>📍 {item.get('location')}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # Scoring and charts
                        score = item.get('impact_score', 0)
                        breakdown = item.get('score_breakdown', {})

                        # Explainable AI
                        if score > 0:
                            col1, col2 = st.columns([0.7, 0.3])
                            with col1:
                                st.write(f"**{item.get('description')}**")
                            with col2:
                                st.metric(label="Potencjał Biznesowy", value=f"{score}/100")
                            
                            # Progress bar
                            st.progress(score)
                            
                            # Expandable details
                            with st.expander("📊 Dlaczego AI wybrało to wydarzenie? (Analiza)"):
                                for key, val in breakdown.items():
                                    col_lbl, col_bar = st.columns([0.4, 0.6])
                                    with col_lbl:
                                        st.caption(key.upper())
                                    with col_bar:
                                        # Normalize 0-20 to 0-1.0
                                        norm_val = min(val / 20.0, 1.0)
                                        st.progress(norm_val)

                                st.markdown("---")
                                st.markdown("**🧠 Uzasadnienie stratega:**")
                                st.info(item.get('comments', "Brak szczegółowego uzasadnienia."))
                        else:
                            # Fallback for old entries without scoring
                            st.write(item.get('description'))

                        st.markdown("<hr><h4>🍰 Menu Specjalne:</h4>", unsafe_allow_html=True)
                        
                        # Menu (columns)
                        cols = st.columns(2)
                        menu = item.get('menu_items', [])
                        
                        if len(menu) > 0:
                            with cols[0]:
                                st.info(f"☕ **{menu[0].get('name')}**\n\n{menu[0].get('desc')}")
                        if len(menu) > 1:
                            with cols[1]:
                                st.warning(f"🍰 **{menu[1].get('name')}**\n\n{menu[1].get('desc')}")
                                
                        # 4. Post section (dynamic height)
                        post_content = item.get('facebook_post', '')
                        # Height algorithm: 50px base + 25px for every 60 characters
                        calc_height = 50 + (len(post_content) // 60) * 25
                        
                        st.text_area(
                            "Post na Facebooka:", 
                            value=post_content, 
                            height=calc_height, 
                            key=f"post_{item.get('event_name')}"
                        )

        except Exception as e:
            st.error(f"Wystąpił nieoczekiwany błąd: {e}")

# Footer
st.markdown("---")
st.caption("CrowdBrew | Powered by Gemini 2.5 Flash Lite")