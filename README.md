FraudLens: Autonomous Fraud Investigation Agent

FraudLens is an AI-powered fraud investigation platform designed to help payment companies investigate suspicious transactions faster, understand potential fraud patterns, and make more informed decisions. Instead of relying entirely on manual investigation, FraudLens brings transaction evidence, customer activity, account relationships, and device signals together to create a clearer picture of suspicious behaviour.

 The Problem We Are Solving

Digital payments are growing rapidly, but financial fraud continues to challenge payment providers and their investigation teams. Analysts often need to examine transaction histories, linked accounts, login activity, and device information separately. This process can be slow, repetitive, and difficult to scale. At the same time, legitimate customers may experience unnecessary restrictions when suspicious activity is incorrectly interpreted.

Our research focuses on making fraud investigation more explainable, consistent, and efficient while reducing dependence on manual analysis.

 Our Approach
 
FraudLens combines backend data analysis with an investigation workflow that gathers relevant evidence and presents findings in an understandable format. Its intended capabilities include identifying account takeover patterns, suspicious card testing activity, mule networks, unusual transaction behaviour, and relationships between accounts and devices.

Rather than treating a risk score as the complete answer, the platform aims to explain why a transaction appears suspicious, distinguish observed evidence from possible interpretations, and support human review before consequential decisions are made.

Technology Stack

The project uses FastAPI and Python for backend services, SQLAlchemy for database access, and Next.js, React, and TypeScript for the frontend. SQLite supports local development, while PostgreSQL is the planned production database. Gemini integration is intended to support evidence-grounded investigation summaries, with deterministic analysis and fallback behaviour remaining important when the language model is unavailable.

Responsible and Explainable AI

FraudLens is designed to assist investigators, not blindly replace them. Findings should be traceable to available evidence, uncertainty should be communicated clearly, and evaluation metrics should be reported only when supported by valid testing data. Protecting sensitive financial information and preventing unsupported fraud accusations are essential considerations.

Project Vision

Our goal is to build a practical, transparent, and scalable fraud investigation assistant that helps analysts spend less time collecting information and more time making sound decisions. FraudLens is being developed as a hackathon project, with local testing, integration verification, and production deployment forming part of its ongoing development.

FraudLens: Investigate smarter. Explain clearly. Decide responsibly.
