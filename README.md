# 🏥 MedAura AI

### AI-Powered Care, Anywhere, Anytime.

MedAura AI is an **offline-first intelligent hospital management system** designed to continue working even when the internet or server connection is unavailable.

## ✨ Features

- 🏥 Patient Registration
- 🤖 Offline AI Symptom Analysis
- 🔴 Urgent / 🟡 Moderate / 🟢 Normal Priority Detection
- 💾 Local Patient Data Storage
- 🔄 Automatic Data Synchronization
- 📡 Online / Offline Server Status
- 📅 Appointment Management
- 🔎 Patient Search and Filtering
- 📝 Activity History
- 👨‍⚕️ Doctor Dashboard
- 💬 Offline AI Assistant

## 🧠 Offline AI

The system analyzes patient symptoms locally using a rule-based AI approach and assigns a priority level:

- **URGENT** – potentially serious symptom patterns
- **MODERATE** – symptoms requiring medical assessment
- **NORMAL** – no high-priority pattern detected

> **Note:** The AI symptom analysis is a project demonstration and is not a medically validated diagnostic system.

## ⚙️ Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, Flask
- **Database:** SQLite
- **AI:** Rule-based offline symptom analysis
- **Charts:** Chart.js

## 🔄 Offline Synchronization

When the server is unavailable:

**Patient → Local Database → Pending Sync**

When the server becomes available:

**Local Database → Server → Synchronized**

This allows the hospital system to continue recording patient information during network interruptions.

## 🚀 Project Goal

To build a reliable hospital management system that provides essential healthcare management features even in environments with unstable or unavailable internet connectivity.

## 👩‍💻 Developer

**N. Thenmozhi**  
B.Tech Information Technology
