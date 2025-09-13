1. Problem Statement

Campus life involves accessing information related to schedules, facilities, dining, library services, and administrative procedures. Students and staff often face difficulties in quickly retrieving accurate information.
To address this, we propose an AI-powered chatbot that serves as a Smart Campus Assistant, capable of answering queries and assisting with various campus-related services.

2. Objectives

Build an AI chatbot for handling campus information queries.

Provide conversational AI interaction through a web application.

Integrate with a campus database to retrieve up-to-date information.

Support multiple services:

Class & exam schedules

Campus facilities (labs, halls, transport, hostels, etc.)

Dining options and menus

Library services (book search, availability, timings)

Administrative procedures (admissions, fees, forms, certificates)

3. Scope of the Project

Users: Students, faculty, staff, and visitors.

Services: Query-based responses, FAQs, and automated assistance.

Platform: Web-based (future scope: mobile app).

Integration: SQL/NoSQL campus database.

AI Features: NLP-based understanding, intent recognition, and dynamic responses.

4. System Requirements
a) Functional Requirements

User can type or speak queries.

Chatbot processes query using NLP.

Chatbot retrieves data from campus database.

User receives a text-based response.

Admins can update campus information in the database.

b) Non-Functional Requirements

Performance: Real-time query processing.

Scalability: Support large numbers of users.

Security: Restricted access to sensitive data.

Usability: Simple, interactive UI.

5. System Design
a) Architecture

Frontend (Web App) – User interface for chatbot interaction.

Backend (Flask/Django/Node.js) – Processes requests, communicates with database.

NLP Engine – Handles intent recognition (Dialogflow / Rasa / spaCy / Transformers).

Database – Stores schedules, facilities, dining, library, and admin data (SQLite/MySQL).

b) Data Flow

User enters a query (e.g., "When is the library open?").

NLP engine interprets query → detects intent (library timing).

Backend queries database.

Response sent back to frontend as chatbot message.

6. Technology Stack

Frontend: HTML, CSS, JavaScript, Bootstrap/React

Backend: Python (Flask/Django)

Database: SQLite/MySQL/PostgreSQL

NLP/AI: NLTK, spaCy, HuggingFace Transformers, or Dialogflow/Rasa

Deployment: Heroku / AWS / Azure
