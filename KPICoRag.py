import os
import json
import streamlit as st
import openai
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter


# React-inspired state management
class AppState:
    def __init__(self):
        self.selected_workflow = None
        self.generated_report = None
        self.user_input = ""
        self.show_analysis = True


# Initialize OpenAI client
def get_openai_key():
    return os.getenv("OPENAI_API_KEY", st.secrets.get("OPENAI_API_KEY"))


try:
    client = openai.OpenAI(api_key=get_openai_key())
except KeyError:
    st.error("❌ OpenAI API key missing! Add to Streamlit Secrets or env vars.")
    st.stop()

# Load workflows from KPI_workflows.txt
def load_workflows():
    try:
        with open("KPI_Workflows.txt", "r") as f:
            data = json.load(f)
        return data.get("workflows", [])
    except Exception as e:
        st.error(f"🚨 Workflow loading error: {str(e)}")
        return []


# Workflow selection component
def WorkflowSelector(props):
    workflows = props['workflows']
    selected = props['selected']
    on_select = props['on_select']

    with st.container():
        selected_wf = st.selectbox(
            "📋 Select Workflow:",
            [wf['name'] for wf in workflows],
            index=next((i for i, wf in enumerate(workflows) if wf['name'] == selected), 0),
            key="workflow_selector",
            on_change=lambda: on_select(st.session_state.workflow_selector)
        )
    return selected_wf


# Workflow analysis component
def WorkflowAnalysis(props):
    workflow = props['workflow']
    with st.expander("🔍 Workflow Analysis", expanded=True):
        cols = st.columns(3)
        cols[0].metric("Steps", len(workflow.get('steps', [])))
        cols[1].metric("Business Rules", len(workflow.get('businessRules', [])))
        cols[2].metric("Dependencies", len(workflow.get('dependencies', [])))

        st.write(f"**Actors:** {', '.join(workflow.get('actors', []))}")
        st.write(f"**Outcome:** {workflow.get('expectedOutcome', '')}")


# ReAct analysis engine
def ReActComponent(props):
    workflow = props['workflow']
    analysis = []

    if not workflow['steps']:
        analysis.append("⚠️ Missing workflow steps")
    if not workflow['businessRules']:
        analysis.append("⚠️ No business rules defined")
    if not workflow['dependencies']:
        analysis.append("⚠️ Missing system dependencies")

    with st.container():
        st.subheader("🧠 AI Quality Assessment")
        if analysis:
            for issue in analysis:
                st.error(issue)
        else:
            st.success("✅ Workflow structure validated")
        st.info("💡 Recommendation: Verify AI model integration points")


# Visualization component
def ChartVisualization(props):
    workflow = props['workflow']
    steps = workflow.get('steps', [])

    if steps:
        df = pd.DataFrame({
            'Step Number': [s['stepNumber'] for s in steps],
            'Action': [s['action'] for s in steps]
        })

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(df['Action'], df['Step Number'], color='#4CAF50')
        ax.set_xlabel("Step Sequence")
        ax.set_title("Workflow Step Visualization")
        st.pyplot(fig)


# Report generation
def ReportGenerator(props):
    state = props['state']
    workflows = props['workflows']

    with st.form("report_form"):
        st.subheader("📝 Report Customization")
        user_input = st.text_area(
            "Add specific requirements:",
            value=state.user_input,
            height=150,
            help="Add any specific reporting requirements or focus areas"
        )

        if st.form_submit_button("🔄 Generate Report"):
            state.user_input = user_input
            state.generated_report = generate_report(state, workflows)
            st.rerun()


def generate_report(state, workflows):
    try:
        workflow = next(wf for wf in workflows if wf["name"] == state.selected_workflow)
    except StopIteration:
        st.error("Selected workflow not found")
        return None

    context = f"""
    ## KPI on the Fly Workflow Analysis Context
    {CORPORATE_CONTEXT}
    ## Workflow Details
    {json.dumps(workflow, indent=2)}
    ## User Requirements
    {state.user_input}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": "Generate comprehensive workflow analysis report:"
            }, {
                "role": "user",
                "content": context
            }],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"🚨 Generation failed: {str(e)}")
        return None


# Report exporter
def ReportExporter(props):
    content = props['content']

    with st.container():
        st.subheader("📤 Export Options")
        pdf_buffer = create_pdf(content)

        col1, col2 = st.columns(2)
        col1.download_button(
            "📄 Download PDF",
            data=pdf_buffer.getvalue(),
            file_name="KPI_analysis.pdf",
            mime="application/pdf"
        )
        col2.download_button(
            "📝 Download TXT",
            data=content.encode(),
            file_name="KPI_analysis.txt"
        )


def create_pdf(content):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    flowables = [
        Paragraph("KPI on the Fly Workflow Analysis Report", styles['Title']),
        Spacer(1, 24)
    ]

    sections = content.split("\n##")
    for section in sections:
        if section.strip():
            title, *body = section.strip().split("\n")
            flowables.append(Paragraph(title, styles['Heading2']))
            for line in body:
                flowables.append(Paragraph(line, styles['BodyText']))
            flowables.append(Spacer(1, 12))

    doc.build(flowables)
    buffer.seek(0)
    return buffer


# Related items component
def RelatedItems(props):
    workflow_name = props['workflow_name']
    related = {
        "Dashboard Creation": ["AI Model v2.1", "Visualizer 3.4"],
        "AI Insights Generation": ["Data Engine 5.0", "Analytics SDK"],
        "Third-Party Integrations": ["API Gateway 2.3"]
    }

    with st.container():
        st.subheader("🔗 Related Components")
        st.write(", ".join(related.get(workflow_name, ["No related components"])))


# Main application
def main():
    st.title("📊 KPI on the Fly Workflow Analyzer")
    st.markdown("**AI-Powered Workflow Optimization System**")

    if 'app_state' not in st.session_state:
        st.session_state.app_state = AppState()

    state = st.session_state.app_state
    workflows = load_workflows()

    if not workflows:
        st.error("🚨 No workflows available")
        return

    state.selected_workflow = WorkflowSelector({
        'workflows': workflows,
        'selected': state.selected_workflow,
        'on_select': lambda wf: setattr(state, 'selected_workflow', wf)
    })

    try:
        workflow = next(wf for wf in workflows if wf["name"] == state.selected_workflow)
    except StopIteration:
        st.error("Selected workflow not found")
        return

    WorkflowAnalysis({'workflow': workflow})
    ReActComponent({'workflow': workflow})
    ChartVisualization({'workflow': workflow})
    ReportGenerator({'state': state, 'workflows': workflows})

    if state.generated_report:
        st.subheader("📜 Generated Analysis Report")
        st.markdown(f"```\n{state.generated_report}\n```")
        ReportExporter({'content': state.generated_report})

    RelatedItems({'workflow_name': state.selected_workflow})


# Corporate context
CORPORATE_CONTEXT = """
KPIonthefly.com AI Analytics Platform
- Advanced dashboard creation tools
- Integrated AI/ML insights generation
- Third-party service integrations
- Enterprise-grade security protocols
- Real-time data visualization
- Compliance with GDPR and CCPA
"""

if __name__ == "__main__":
    main()