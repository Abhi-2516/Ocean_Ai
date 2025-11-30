# streamlit_ui/app.py
import streamlit as st
import requests
import subprocess
import json
from pathlib import Path
from typing import List, Optional
import os
import shlex

# Root project folder (two levels up from this file)
ROOT = Path(__file__).resolve().parents[1] if (Path(__file__).resolve().parents and len(Path(__file__).resolve().parents) > 1) else Path('.').resolve()
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

# Backend URL: prefer secrets, then environment, then default
DEFAULT_BACKEND = "http://127.0.0.1:8000"
BACKEND_URL = None
try:
    BACKEND_URL = st.secrets.get("backend_url", None)
except Exception:
    BACKEND_URL = None
if not BACKEND_URL:
    BACKEND_URL = os.environ.get("BACKEND_URL", DEFAULT_BACKEND)

st.set_page_config(page_title="Ocean.AI — Demo UI", layout="wide")

st.title("Ocean.AI — RAG Testcase & Script Demo")

# ------------------------------
# Sidebar: uploads & ingestion
# ------------------------------
with st.sidebar:
    st.header("Build / Ingest")

    uploaded = st.file_uploader("Upload one or more files to assets (txt, md, html)", accept_multiple_files=True)
    if uploaded:
        saved_files = []
        for f in uploaded:
            out = ASSETS / f.name
            with open(out, "wb") as fh:
                fh.write(f.getbuffer())
            saved_files.append(str(out))
        st.success(f"Saved {len(saved_files)} file(s) to assets/")

    if st.button("Ingest saved assets now"):
        files = [str(p) for p in ASSETS.glob("*")]
        if not files:
            st.warning("No files in assets/ to ingest. Upload files first.")
        else:
            cmd = ["python", "backend/ingest_runner.py"] + files
            st.info("Running ingest: \n" + " ".join(shlex.quote(x) for x in cmd))
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                out_text = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
                st.code(out_text)
                if res.returncode == 0:
                    st.success("Ingestion finished")
                else:
                    st.error("Ingestion finished with errors (see output above).")
            except Exception as e:
                st.error(f"Failed to run ingest: {e}")

    st.markdown("---")
    st.markdown("**Backend URL**")
    url_in = st.text_input("Backend base URL", value=BACKEND_URL)
    if url_in and url_in != BACKEND_URL:
        # Update session and local variable (won't persist across reloads)
        BACKEND_URL = url_in
        st.session_state['backend_url'] = BACKEND_URL

# ------------------------------
# Generate Testcases UI
# ------------------------------
st.header("Query & Generate Testcases")
col1, col2 = st.columns([1, 2])
with col1:
    query = st.text_input("Agent query", "discount code")
    top_k = st.number_input("Top k", min_value=1, max_value=10, value=3)
    use_llm = st.checkbox("Use LLM?", value=False)
    if st.button("Generate Testcases"):
        payload = {"query": query, "top_k": int(top_k), "use_llm": bool(use_llm)}
        try:
            r = requests.post(f"{BACKEND_URL}/generate_testcases", json=payload, timeout=30)
            r.raise_for_status()
            resp = r.json()
            st.session_state['last_generate'] = resp
            st.success("Generated testcases")
        except Exception as e:
            st.error(f"Failed to call backend: {e}")

with col2:
    if 'last_generate' in st.session_state:
        g = st.session_state['last_generate']
        st.subheader("Retrieved grounding chunks")
        if g.get('retrieved'):
            for idx, item in enumerate(g['retrieved']):
                st.markdown(f"**Chunk {idx+1}** — distance {item.get('distance')} — source: {item.get('metadata',{}).get('source')}")
                st.code(item.get('document',''))
        st.subheader("Generated Testcases")
        if g.get('testcases'):
            for i, tc in enumerate(g['testcases']):
                with st.expander(f"{i+1}. {tc.get('Test_ID','')} — {tc.get('Test_Scenario', tc.get('Test_Steps', ['...'])[0])}"):
                    st.json(tc)
            # ensure there's at least one testcase
            max_idx = max(0, len(g['testcases'])-1)
            st.session_state['selected_index'] = st.number_input("Select testcase index to generate script (0-based)", min_value=0, max_value=max_idx, value=st.session_state.get('selected_index', 0))
        else:
            st.info("No testcases in last response")

st.markdown("---")
st.header("Generate Selenium Script from Selected Testcase")

if 'last_generate' in st.session_state and st.session_state.get('last_generate',{}).get('testcases'):
    tc_list = st.session_state['last_generate']['testcases']
    idx = st.session_state.get('selected_index', 0)
    idx = max(0, min(idx, len(tc_list)-1))
    tc = tc_list[idx]
    st.subheader(f"Selected: {tc.get('Test_ID','')} / {tc.get('Test_Scenario','')}")
    checkout_html = st.text_area("Checkout HTML (paste full contents here) — or leave blank to use assets/example.txt", height=250)

    # default html_path -> file:/// + forward slashes
    default_html_path = f"file:///{str((ASSETS/'checkout.html').resolve()).replace('\\','/')}"
    html_path = st.text_input("html_path (file:// path to use in generated script)", value=st.session_state.get('html_path', default_html_path))

    if st.button("Generate Script via backend API"):
        # prepare payload
        if checkout_html and checkout_html.strip():
            html_payload = checkout_html
        else:
            # fallback to example.txt (this project uses example.txt as a simple HTML-like fallback)
            example_file = ASSETS / 'example.txt'
            if example_file.exists():
                html_payload = example_file.read_text(encoding='utf-8')
            else:
                st.error("No checkout_html provided and assets/example.txt not found. Please upload or paste checkout HTML.")
                html_payload = None

        if html_payload is not None:
            payload = {"test_case": tc, "checkout_html": html_payload, "html_path": html_path}
            try:
                r = requests.post(f"{BACKEND_URL}/generate_script", json=payload, timeout=60)
                r.raise_for_status()
                resp = r.json()
                script = resp.get('script')
                if script:
                    st.subheader("Generated Selenium Script")
                    st.code(script, language="python")

                    # Download button
                    default_name = f"generated_test_{tc.get('Test_ID','')}.py"
                    st.download_button("Download script", script, file_name=default_name, mime="text/x-python")

                    # save to tests/ automatically
                    out = Path("tests")
                    out.mkdir(exist_ok=True)
                    fname = out / default_name
                    fname.write_text(script, encoding='utf-8')
                    st.success(f"Saved script to {fname}")

                    # Run the saved script option
                    if st.button("Run saved script now"):
                        try:
                            # run the script in the same venv
                            run_res = subprocess.run([sys.executable if hasattr(__import__('sys'), 'executable') else "python", str(fname)], capture_output=True, text=True, check=False)
                            stdout = run_res.stdout or ""
                            stderr = run_res.stderr or ""
                            st.text_area("Script stdout", stdout, height=200)
                            if stderr:
                                st.text_area("Script stderr", stderr, height=200)
                            if run_res.returncode == 0:
                                st.success("Script finished with exit code 0 (likely passed).")
                            else:
                                st.error(f"Script finished with exit code {run_res.returncode}. See stdout/stderr above.")
                        except Exception as e:
                            st.error(f"Failed to run script: {e}")
                else:
                    st.error("Backend returned no script. Provide a checkout HTML with coupon input or use local generator.")
            except Exception as e:
                st.error(f"Error generating script: {e}")
else:
    st.info("Generate testcases first to enable script generation.")

st.markdown("---")
st.header("Local script generator (no backend)")
if st.button("Generate script locally from first saved testcase"):
    try:
        import json as _json
        tc_file = Path('tests/sample_testcase.json')
        if not tc_file.exists():
            st.error('tests/sample_testcase.json not found. Run generate_testcases and save one.')
        else:
            tc = _json.loads(tc_file.read_text(encoding='utf-8'))
            from backend.agent_tools import generate_selenium_script_html
            # use checkout.html if present, else example.txt
            html_file = ASSETS / 'checkout.html'
            if not html_file.exists():
                html_file = ASSETS / 'example.txt'
            if not html_file.exists():
                st.error('No checkout.html or example.txt found in assets/. Please upload one.')
            else:
                html = html_file.read_text(encoding='utf-8')
                script = generate_selenium_script_html(tc, html, html_path if 'html_path' in locals() else default_html_path)
                if script:
                    st.code(script, language="python")
                    Path('tests').mkdir(exist_ok=True)
                    Path('tests/generated_test_local.py').write_text(script, encoding='utf-8')
                    st.success('Wrote tests/generated_test_local.py')
                else:
                    st.error('Local generator returned None. Provide checkout.html in assets or paste HTML above.')
    except Exception as e:
        st.error(f'Local generation error: {e}')

st.markdown("---")
st.write("Tips: start your backend (uvicorn backend.app:app --reload --port 8000). If you changed file paths, update the Backend URL in the sidebar.")
