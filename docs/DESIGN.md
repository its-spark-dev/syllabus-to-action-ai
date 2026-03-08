# Design Document

## 1. System Goals

The system aims to convert unstructured syllabus documents into structured, prioritized, and actionable weekly plans.

The AI component is not merely a summarizer but a reasoning engine.

---

## 2. Core Design Principles

1. Simplicity of UI
2. AI-driven reasoning
3. Explainable prioritization
4. Modular architecture
5. Scalable deployment

---

## 3. Architecture Layers

### Layer 1: Extraction

Parse unstructured syllabus text into structured data:
- Assignments
- Exams
- Deadlines
- Weight percentages

### Layer 2: Reasoning

Using IBM WatsonX with Granite models:
- Analyze workload
- Detect deadline clustering
- Evaluate grade weight importance
- Prioritize tasks

### Layer 3: Planning

Generate:
- Weekly to-do lists
- Time-aware task breakdowns
- Study focus areas

---

## 4. Module Structure

app.py – Streamlit UI  
parser/ – syllabus parsing logic  
planner/ – weekly plan generation  
ai/ – IBM WatsonX integration  
data/ – mock syllabi for testing  

---

## 5. Deployment Strategy

The application can be deployed using IBM Cloud to demonstrate real-world scalability.
