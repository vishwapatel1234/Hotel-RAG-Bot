# StayChat AI: Premium Hotel RAG Bot 🏨✨

A fully functional, luxury-themed AI concierge built for the StayChat Grand Hotel. This project leverages **RAG (Retrieval-Augmented Generation)** to intelligently answer guest queries regarding rooms, dining, amenities, and hotel policies using a proprietary knowledge base.

It boasts a gorgeous, responsive, modern SaaS layout (inspired by Claude & ChatGPT) and features local conversation history, real-time developer telemetry, and seamless PDF transcript exports.

## 🌟 Key Features

1. **RAG-Powered Engine**: Accurately retrieves context from a local knowledge base (Pricing, Policies, Amenities) to prevent hallucinations.
2. **Multi-Turn Memory**: Retains conversational context across multiple turns (e.g., "What's the price of a Deluxe Room?" -> "Does it have a city view?").
3. **Intent Detection & Multilingual Support**: Safely detects whether a query is related to the hotel. Blocks out-of-bounds questions (coding, sports) and flags sensitive requests (payment links) for human escalation.
4. **SaaS-Style UI**: A premium, centered, glassmorphic dark-mode UI with smooth animations.
5. **Local Chat History**: Automatically saves your past conversations to `localStorage` accessible via a slide-over drawer.
6. **PDF Exports**: High-resolution, styled PDF exports of the chat transcript using `html2canvas` and `jspdf`.
7. **Developer Inspector**: A toggleable side-drawer showing real-time pipeline telemetry (Intent, Language, Confidence Score, Retrieved Chunks, and Guardrail Status).

## 🎥 Demo Video

> **[INSERT DEMO VIDEO LINK HERE]**
> *(A 3-5 minute video demonstrating the UI, multi-turn memory, RAG capabilities, and developer inspector).*

## 🚀 Setup & Installation

### Prerequisites
- Node.js (v18+ recommended)
- A Google Gemini API Key

### 1. Clone the repository
```bash
git clone https://github.com/vishwapatel1234/Hotel-RAG-Bot.git
cd Hotel-RAG-Bot/frontend
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Environment Variables
Create a `.env` file in the `frontend` directory:
```env
VITE_GEMINI_API_KEY=your_actual_gemini_api_key_here
```
*(Note: `.env` is ignored by git to protect your secrets).*

### 4. Run the Application
```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser. By default, you can use the built-in "Local Simulator" or toggle to the "Live AI Pipeline" via the settings gear in the top right corner.

## 🛠️ Tech Stack
- **Frontend**: React (Vite), TypeScript, TailwindCSS, Lucide-React
- **State & Export**: LocalStorage, jsPDF, html2canvas
- **AI/Backend Integration**: Google Gemini Pro API (Client-side integration for demo purposes)
